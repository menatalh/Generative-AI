from langchain_core.documents import Document

from engines.base import ChatEngine

class Chatbot:
    """Facade the UI talks to, so the engine can be swapped without touching the UI"""
    def __init__(self, engine: ChatEngine):
        self.engine = engine

    def ask(self, session_id: str, question: str) -> str:
        return self.engine.answer(session_id, question)

    def history(self, session_id: str) -> list[tuple[str, str]]:
        return self.engine.get_history(session_id)

    def sources(self, session_id: str) -> list[list[Document]]:
        return self.engine.get_sources(session_id)
