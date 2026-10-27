from abc import ABC, abstractmethod

from langchain_core.documents import Document

class ChatEngine(ABC):
    @abstractmethod
    def answer(self, session_id: str, question: str) -> str:
        pass
    @abstractmethod
    def get_history(self, session_id: str) -> list[tuple[str, str]]:
        pass
    def get_sources(self, session_id: str) -> list[list[Document]]:
        return []
