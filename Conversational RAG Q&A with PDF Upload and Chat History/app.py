import os
import tempfile
import uuid

import chromadb
import groq
import streamlit as st
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from api_key import APIKey
from chat_engine import RagChatEngine
from rag_chain import build_rag_chain
from retriever import SEARCH_MODES, HybridRetriever

st.set_page_config(page_title="Conversational RAG with PDFs", page_icon="📄")
st.title("Conversational RAG Q&A with PDFs")

@st.cache_resource 
def get_chroma_client():
    return chromadb.EphemeralClient()

def index_pdfs():
    files = st.session_state.pdfs
    if not files:
        return
    docs = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        for f in files:
            path = os.path.join(tmp_dir, f.name)
            with open(path, "wb") as out:
                out.write(f.getvalue())
            docs.extend(PyPDFLoader(path).load())

    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)
    Chroma.from_documents(chunks, HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),collection_name="student-rag",client=get_chroma_client())

groq_key = APIKey("Groq", "gsk_")

with st.sidebar:
    api_key = groq_key.render()

    if "default_session_id" not in st.session_state:
        st.session_state.default_session_id = uuid.uuid4().hex[:8]
    session_id = st.text_input("Session ID", value=st.session_state.default_session_id)

    uploaded_files = st.file_uploader(
        "Upload PDFs", type="pdf", accept_multiple_files=True,
        key="pdfs", on_change=index_pdfs,
    )

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

vectorstore = Chroma(collection_name="student-rag", client=get_chroma_client(), embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
retriever = HybridRetriever(vectorstore=vectorstore, mode=search_mode, k=4)

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, api_key=api_key)

rag_chain = build_rag_chain(llm, retriever)

if "store" not in st.session_state:
    st.session_state.store = {}

if "sources" not in st.session_state:
    st.session_state.sources = {}

engine = RagChatEngine(rag_chain, st.session_state.store, st.session_state.sources)

def render_sources(docs):
    with st.expander(f"Sources ({len(docs)})", icon=":material/description:", type="compact"):
        for doc in docs:
            name = os.path.basename(doc.metadata.get("source", "PDF"))
            page = doc.metadata.get("page")
            st.caption(f"{name}, page {page + 1}" if page is not None else name)
            st.text(doc.page_content)

session_sources = engine.get_sources(session_id)
assistant_turn = 0
for role, content in engine.get_history(session_id):
    if role == "human":
        with st.chat_message("user"):
            st.markdown(content)
    else:
        with st.chat_message("assistant"):
            st.markdown(content)
            render_sources(session_sources[assistant_turn])
        assistant_turn += 1

if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                answer = engine.answer(session_id, question)
            st.markdown(answer)
        except groq.AuthenticationError:
            groq_key.forget()
            st.error("The Groq API key was rejected. Check it in the sidebar.")
        else:
            if show_sources:
                render_sources(engine.get_sources(session_id)[-1])
