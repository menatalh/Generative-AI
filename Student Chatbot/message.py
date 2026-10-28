from abc import ABC
from datetime import datetime

class Msg(ABC):
    def __init__(self, content):
        self.content = content
        self.align = "left"
        self.date = datetime.now()


class UsrMsg(Msg):
    def __init__(self, content):
        super().__init__(content)
        self.align = "right"


class BotMsg(Msg):
    def __init__(self, content):
        super().__init__(content)
        self.align = "left"