from operator import itemgetter

from langchain_core.documents import Document
from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever
from langchain_core.runnables import Runnable, RunnableLambda, RunnablePassthrough

CONTEXTUALIZE_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "Given a chat history and the latest user question, which might reference context in the "
     "chat history, rewrite it as a standalone question that can be understood without the chat "
     "history. Do NOT answer the question. If it is already standalone, return it unchanged. "
     "Reply with the question only."),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

ANSWER_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "You answer questions about the user's uploaded PDFs. Use only the retrieved context below. "
     "If the context does not contain the answer, say you don't know instead of using outside "
     "knowledge.\n\n"
     "<context>\n{context}\n</context>"),
    MessagesPlaceholder("chat_history"),
    ("human", "{question}"),
])

def join_docs(docs: list[Document]) -> str:
    return "\n\n".join(doc.page_content for doc in docs)

def build_rag_chain(llm: BaseChatModel, retriever: BaseRetriever) -> Runnable:
    retrieval_chain = CONTEXTUALIZE_PROMPT | llm | StrOutputParser() | retriever

    answer_chain = {
        "context": itemgetter("docs") | RunnableLambda(join_docs),
        "question": itemgetter("question"),
        "chat_history": itemgetter("chat_history"), 
    } | ANSWER_PROMPT | llm | StrOutputParser()

    return {
        "docs": retrieval_chain,
        "question": itemgetter("question"),
        "chat_history": itemgetter("chat_history"),
    } | retrieval_chain | answer_chain