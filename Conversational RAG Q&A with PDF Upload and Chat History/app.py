import os
import tempfile
from operator import itemgetter
import uuid

import chromadb
import groq
import streamlit as st
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import ConfigurableField, RunnableLambda, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from api_key import APIKey
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

vectorstore = Chroma(collection_name="student-rag", client=get_chroma_client(), embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))
retriever = HybridRetriever(vectorstore=vectorstore, k=4).configurable_fields(mode=ConfigurableField(id="search_mode"))

llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0, api_key=api_key)

contextualize_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Given a chat history and the latest user question, which might reference context in the "
     "chat history, rewrite it as a standalone question that can be understood without the chat "
     "history. Do NOT answer the question. If it is already standalone, return it unchanged. "
     "Reply with the question only."),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

retrieval_chain = contextualize_prompt | llm | StrOutputParser() | retriever # {"docs": [...], "question": ..., "chat_history": [...]

answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions about the user's uploaded PDFs. Use only the retrieved context below. "
     "If the context does not contain the answer, say you don't know instead of using outside "
     "knowledge.\n\n"
     "<context>\n{context}\n</context>"),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

def join_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

answer_chain = {
    "context": itemgetter("docs") | RunnableLambda(join_docs),
    "question": itemgetter("question"),
    "chat_history": itemgetter("chat_history"),
} | answer_prompt | llm | StrOutputParser()

rag_chain = {
    "docs": retrieval_chain,
    "question": itemgetter("question"),
    "chat_history": itemgetter("chat_history"),
} | RunnablePassthrough.assign(answer=answer_chain)

if "store" not in st.session_state:
    st.session_state.store = {}

if "sources" not in st.session_state:
    st.session_state.sources = {}

def get_session_history(session_id):
    if session_id not in st.session_state.store:
        st.session_state.store[session_id] = InMemoryChatMessageHistory()
    return st.session_state.store[session_id]

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="chat_history",
    output_messages_key="answer",
)

def render_sources(docs):
    with st.expander(f"Sources ({len(docs)})", icon=":material/description:", type="compact"):
        for doc in docs:
            name = os.path.basename(doc.metadata.get("source", "PDF"))
            page = doc.metadata.get("page")
            st.caption(f"{name}, page {page + 1}" if page is not None else name)
            st.text(doc.page_content)

session_sources = st.session_state.sources.setdefault(session_id, [])
assistant_turn = 0
for message in get_session_history(session_id).messages:
    if message.type == "human":
        with st.chat_message("user"):
            st.markdown(message.content)
    else:
        with st.chat_message("assistant"):
            st.markdown(message.content)
            render_sources(session_sources[assistant_turn])
        assistant_turn += 1

with st.bottom.container(horizontal=True, vertical_alignment="bottom"):
    search_mode = st.selectbox(
        "Search mode", SEARCH_MODES, format_func=str.capitalize,
        label_visibility="collapsed", width=130,
    )
    question = st.chat_input("Ask a question about your PDFs", submit_mode="disable")
if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                result = conversational_rag_chain.invoke(
                    {"question": question},
                    config={"configurable": {"session_id": session_id, "search_mode": search_mode}},
                )
            answer, docs = result["answer"], result["docs"]
            st.markdown(answer)
        except groq.AuthenticationError:
            groq_key.forget()
            st.error("The Groq API key was rejected. Check it in the sidebar.")
        else:
            session_sources.append(docs)
            if show_sources:
                render_sources(docs)
