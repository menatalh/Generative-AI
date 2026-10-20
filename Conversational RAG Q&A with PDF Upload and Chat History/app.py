# Inputs: API Key (secure), Session ID, PDF uploader, chat input.
import os
import tempfile
from operator import itemgetter
import uuid
from dotenv import load_dotenv

import anthropic
import streamlit as st
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

st.set_page_config(page_title="Conversational RAG with PDFs", page_icon="📄")
st.title("Conversational RAG Q&A with PDFs")

with st.sidebar:
    api_key = st.text_input("Anthropic API key", type="password", placeholder="sk-ant-...")

    if "default_session_id" not in st.session_state:
        st.session_state.default_session_id = uuid.uuid4().hex[:8]
    session_id = st.text_input("Session ID", value=st.session_state.default_session_id)

    uploaded_files = st.file_uploader("Upload PDFs", type="pdf", accept_multiple_files=True)

if not api_key:
    st.info("Enter your Anthropic API key in the sidebar to start")
    st.stop()

if not uploaded_files:
    st.info("Upload one or more PDFs to ask questions about")
    st.stop()

def get_retriever(files): 
    docs = []
    with tempfile.TemporaryDirectory() as tmp_dir:
        for name, data in files:
            path = os.path.join(tmp_dir, name)
            with open(path, "wb") as f:
                f.write(data)
            docs.extend(PyPDFLoader(path).load())

    chunks = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)
    vectorstore = Chroma.from_documents(
        chunks,
        HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"),
        collection_name=".chroma/student-rag"
    )
    return vectorstore.as_retriever(search_kwargs={"k": 4})


retriever = build_retriever(tuple((f.name, f.getvalue()) for f in uploaded_files))

llm = ChatAnthropic(model="claude-opus-5-5", max_tokens=4096, effort="low")

# contextualize question: rewrite follow-ups into unambiguous questions using chat history
contextualize_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "Given a chat history and the latest user question, which might reference context in the "
     "chat history, rewrite it as a standalone question that can be understood without the chat "
     "history. Do NOT answer the question. If it is already standalone, return it unchanged. "
     "Reply with the question only."),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

def join_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

retrieval_chain = contextualize_prompt | llm | StrOutputParser() | retriever | join_docs

answer_prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions about the user's uploaded PDFs. Use only the retrieved context below. "
     "If the context does not contain the answer, say you don't know instead of using outside "
     "knowledge.\n\n"
     "<context>\n{context}\n</context>"),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

rag_chain = {
    "context": retrieval_chain,
    "question": itemgetter("question"),
    "chat_history": itemgetter("chat_history"),
} | answer_prompt | llm | StrOutputParser()

if "store" not in st.session_state:
    st.session_state.store = {}

def get_session_history(session_id):
    if session_id not in st.session_state.store:
        st.session_state.store[session_id] = InMemoryChatMessageHistory()
    return st.session_state.store[session_id]

conversational_rag_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="chat_history",
)

for message in get_session_history(session_id).messages:
    with st.chat_message("user" if message.type == "human" else "assistant"):
        st.markdown(message.content)

question = st.chat_input("Ask a question about your PDFs")
if question:
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        st.write_stream(conversational_rag_chain.stream(
            {"question": question},
            config={"configurable": {"session_id": session_id}},
        ))
