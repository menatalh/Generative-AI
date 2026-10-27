from abc import ABC, abstractmethod

from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.documents import Document
from langchain_core.runnables import Runnable
from langchain_core.runnables.history import RunnableWithMessageHistory

class ChatEngine(ABC):
    @abstractmethod
    def answer(self, session_id: str, question: str) -> str:
        pass
    @abstractmethod
    def get_history(self, session_id: str) -> list[tuple[str, str]]:
        pass

class RagChatEngine(ChatEngine):
    def __init__(self, rag_chain: Runnable, store: dict[str, InMemoryChatMessageHistory], sources: dict[str, list[list[Document]]]):
        self.store = store
        self.sources = sources
        self.chain = RunnableWithMessageHistory(
            rag_chain,
            self._session_history,
            input_messages_key="question",
            history_messages_key="chat_history",
            output_messages_key="answer",
        )

    def _session_history(self, session_id: str) -> InMemoryChatMessageHistory:
        if session_id not in self.store:
            self.store[session_id] = InMemoryChatMessageHistory()
        return self.store[session_id]

    def answer(self, session_id: str, question: str) -> str:
        result = self.chain.invoke(
            {"question": question},
            config={"configurable": {"session_id": session_id}},
        )
        self.sources.setdefault(session_id, []).append(result["docs"])
        return result["answer"]

    def get_history(self, session_id: str) -> list[tuple[str, str]]:
        history = self.store.get(session_id)
        if history is None:
            return []
        return [(m.type, m.content) for m in history.messages]

    def get_sources(self, session_id: str) -> list[list[Document]]:
        return self.sources.get(session_id, [])

class SimpleFAQEngine(ChatEngine):
    def __init__(self, faq_map: dict[str, str]):
        self.faq_map = faq_map
        self.histories: dict[str, list[tuple[str, str]]] = {}

    def answer(self, session_id: str, question: str) -> str:
        ans = self.faq_map.get(question.lower(), "Sorry, I don't know.")
        history = self.histories.setdefault(session_id, [])
        history.append(("human", question))
        history.append(("ai", ans))
        return ans

    def get_history(self, session_id: str) -> list[tuple[str, str]]:
        return self.histories.get(session_id, [])
