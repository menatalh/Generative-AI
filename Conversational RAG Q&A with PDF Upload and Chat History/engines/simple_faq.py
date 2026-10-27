from engines.base import ChatEngine

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
