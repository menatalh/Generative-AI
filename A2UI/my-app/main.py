"""A LangChain chain that answers with A2UI. Usage: uv run main.py "a weather card" """

import json
import subprocess
import sys

from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

from a2ui.core.basic_catalog import BasicCatalog
from a2ui.inference_formats.direct_json import DirectJsonFormat
from a2ui.schema import VERSION_0_9, CatalogConfig

# The components the client can render, and a system prompt that teaches them.
catalog = CatalogConfig.from_catalog("basic", BasicCatalog(VERSION_0_9)).to_catalog(
    protocol_version=VERSION_0_9
)
a2ui = DirectJsonFormat([catalog])
system_prompt = a2ui.generate_system_prompt(
    role_description="Answer with one short sentence, then an A2UI UI.",
    include_schema=True,
)

prompt = ChatPromptTemplate.from_messages(
    [SystemMessage(system_prompt), ("human", "{question}")]
)


def claude(prompt_value) -> str:
    """Calls Claude through your Claude Code login (`claude -p`)."""
    system, human = prompt_value.to_messages()
    cmd = ["claude", "-p", "--model", "opus", "--tools", "", "--system-prompt", system.content]
    return subprocess.run(cmd, input=human.content, capture_output=True, text=True, check=True).stdout


def to_a2ui(reply: str) -> list[dict]:
    """Extracts the A2UI messages from the reply."""
    return [m for part in a2ui.parser.parse_response(reply) for m in part.a2ui_json or []]


chain = prompt | RunnableLambda(claude) | RunnableLambda(to_a2ui)

if __name__ == "__main__":
    messages = chain.invoke({"question": " ".join(sys.argv[1:])})
    # Saved where the React app (web/) reads it.
    with open("web/public/output.jsonl", "w") as f:
        f.writelines(json.dumps(m) + "\n" for m in messages)
    print(f"Saved {len(messages)} messages to web/public/output.jsonl")
