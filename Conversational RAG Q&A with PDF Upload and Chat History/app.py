import os
import uuid

import chromadb
import groq
import streamlit as st
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from api_key import APIKey
from chatbot import Chatbot
from config import Config
from engines.rag_engine import RagChatEngine
from rag.ingest import index_documents, load_pdfs, split_documents
from rag.pipeline import build_rag_chain
from rag.retriever import SEARCH_MODES, HybridRetriever

cfg = Config()

st.set_page_config(page_title="Conversational RAG with PDFs", page_icon="📄")
st.title("Conversational RAG Q&A with PDFs")

@st.cache_resource
def get_chroma_client():
    return chromadb.EphemeralClient()

@st.cache_resource
def get_embeddings(model_name: str):
    return HuggingFaceEmbeddings(model_name=model_name)

def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name=f"{cfg.collection_name}",
        client=get_chroma_client(),
        embedding_function=get_embeddings(cfg.embedding_model),
    )

def index_pdfs():
    docs, errors = load_pdfs(st.session_state.pdfs or [], cfg.max_file_mb)
    chunks = split_documents(docs, cfg.chunk_size, cfg.chunk_overlap)
    index_documents(get_vectorstore(), chunks)
    st.session_state.ingest_errors = errors

groq_key = APIKey("Groq", "gsk_")

with st.sidebar:
    api_key = groq_key.render()

    if "default_session_id" not in st.session_state:
        st.session_state.default_session_id = uuid.uuid4().hex[:8]
    session_id = st.text_input("Session ID", value=st.session_state.default_session_id)

    uploaded_files = st.file_uploader(
        "Upload PDFs", type="pdf", accept_multiple_files=True,
        key="pdfs", on_change=index_pdfs,
        help=f"Up to {cfg.max_file_mb} MB per file",
    )
    for error in st.session_state.get("ingest_errors", []):
        st.warning(error)

    show_sources = st.toggle("Show retrieved sources", value=False)

if not api_key:
    st.stop()

if not uploaded_files:
    st.info("Upload one or more PDFs to ask questions about.")
    st.stop()

with st.bottom.container(horizontal=True, vertical_alignment="bottom"):
    search_mode = st.selectbox(
        "Search mode", SEARCH_MODES, format_func=str.capitalize,
        label_visibility="collapsed", width=130,
    )
    question = st.chat_input("Ask a question about your PDFs", submit_mode="disable")

retriever = HybridRetriever(vectorstore=get_vectorstore(), mode=search_mode, k=cfg.k, fetch_k=cfg.fetch_k)

llm = ChatGroq(model=cfg.llm_model, temperature=cfg.temperature, api_key=api_key)

rag_chain = build_rag_chain(llm, retriever)

if "store" not in st.session_state:
    st.session_state.store = {}

if "sources" not in st.session_state:
    st.session_state.sources = {}

chatbot = Chatbot(RagChatEngine(rag_chain, st.session_state.store, st.session_state.sources))

def render_sources(docs):
    with st.expander(f"Sources ({len(docs)})", icon=":material/description:", type="compact"):
        for doc in docs:
            name = os.path.basename(doc.metadata.get("source", "PDF"))
            page = doc.metadata.get("page")
            st.caption(f"{name}, page {page + 1}" if page is not None else name)
            st.text(doc.page_content)

session_sources = chatbot.sources(session_id)
assistant_turn = 0
for role, content in chatbot.history(session_id):
    if role == "human":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)
            if show_sources:
                render_sources(session_sources[assistant_turn])
        assistant_turn += 1

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                answer = chatbot.ask(session_id, question)
            st.markdown(answer)
        except groq.AuthenticationError:
            groq_key.forget()
            st.error("The Groq API key was rejected. Check it in the sidebar.")
        else:
            if show_sources:
                render_sources(chatbot.sources(session_id)[-1])
