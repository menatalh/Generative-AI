import mysql.connector

from db import Database
from message import BotMsg

OPTIONS = {
    "list student > 3.3": { "operator": ">", "value": 3.3 },
    "list student < 2": { "operator": "<", "value": 2 },
    "list student = 4": { "operator": "=", "value": 4 },
}


class Chatbot:
    def __init__(self, database: Database):
        self.database = database

    def respond(self, prompt):
        prompt = prompt.lower()
        if prompt not in OPTIONS:
            return BotMsg("I'm not that intelligent yet")

        option = OPTIONS[prompt]
        operator = option["operator"]
        value = option["value"]
        try:
            rows = self.database.query_students(operator, value)
        except mysql.connector.Error:
            return BotMsg("Sorry, I can't reach the student database right now")
        if not rows:
            return BotMsg(f"No students found with grade {operator} {value}")

        lines = [f"Students with grade {operator} {value}:"]
        lines += [f"{name}: {grade}" for name, grade in rows]
        return BotMsg("  \n".join(lines))
