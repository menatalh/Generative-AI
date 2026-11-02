# Music Store Customer Support

A multi-agent customer support assistant for a digital music store, built with LangGraph on the Chinook sample database. A supervisor routes each question to a music catalog agent, an invoice agent, or both. Customers are verified by customer ID, email, or phone before anything runs, and their music preferences are remembered across sessions.

## Demo

[Watch the demo video](https://drive.google.com/file/d/1eWsfdxkX_c5T83wGGlJZCmwDhP9tIVHU/view?usp=sharing)

## Setup

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt ipykernel
```

## Run

Open `music_store_support.ipynb`, select the `.venv` kernel, and run the cells top to bottom.

The first cell downloads the Chinook SQL script from GitHub and loads it into an in-memory SQLite database. The LLM cell asks for your Groq API key (starts with `gsk_`, get one at https://console.groq.com/keys) unless `GROQ_API_KEY` is already set.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | Yes | Groq API key. Prompted with `getpass` if not set. |

## How it works

<img width="1316" height="298" alt="Screenshot 2026-11-02 at 12 18 19 PM" src="https://github.com/user-attachments/assets/9e633e9c-ae29-44fa-9b33-f8ca1c062ce6" />


- **Verification** (`verify_info`): the LLM extracts a customer ID, email, or phone number from the message with structured output, then a database lookup maps it to a `CustomerId`. Phone numbers are compared by digits only, so `+55 12 39235555` matches `+55 (12) 3923-5555`. Once verified, `customer_id` stays in the thread state and later turns skip this step.
- **Human-in-the-loop** (`human_input`): if no valid identifier is found, the graph pauses with `interrupt()`. The caller resumes it with `Command(resume="...")`, and the reply goes back through `verify_info` until it succeeds.
- **Supervisor** (`langgraph_supervisor.create_supervisor`): routes each part of a request to the right sub-agent through handoff tools, then combines the answers into one reply. Uses `output_mode="last_message"` so only each agent's final answer enters the shared history.
- **Music Catalog sub-agent** (`create_react_agent`): tools `get_albums_by_artist`, `get_tracks_by_artist`, `get_songs_by_genre`, `check_for_songs`. Its prompt function injects the customer's saved preferences from `loaded_memory`.
- **Invoice Information sub-agent** (`create_react_agent`): tools `get_invoices_by_customer_sorted_by_date`, `get_invoices_sorted_by_unit_price`, `get_employee_by_invoice_and_customer`. Its prompt function injects the verified `customer_id`, so customers can only see their own invoices. The employee is found through `Customer.SupportRepId`.
- **Long-term memory** (`load_memory`, `create_memory`): an `InMemoryStore` holds one `UserProfile` (a list of music preferences) per customer under the namespace `("memory_profile", customer_id)`. `load_memory` reads it into the state before the supervisor runs, and `create_memory` asks the LLM to merge new preferences from the conversation and saves them after.
- **Short-term memory**: a `MemorySaver` checkpointer keeps each thread's messages and `customer_id` between turns.

## Test scenarios

| Scenario | Thread | Expected result |
|---|---|---|
| Phone number given, mixed question (spec Test Case 1) | `tc1` | Most recent purchase August 7, 2025, $8.91; albums Hot Rocks, No Security, Voodoo Lounge |
| Follow-up "List some songs that match my preferences?" | `tc1` | Rolling Stones songs, from the saved preferences |
| No customer info (spec Test Case 2) | `tc2` | Interrupts and asks for customer ID, email, or phone; a wrong ID interrupts again; a correct email answers the original question |

## Project structure

```
music_store_support.ipynb   All code, tests, and explanations
requirements.txt            Python dependencies
```

## Limits

- Groq's free tier allows 200,000 tokens per day per model. A full notebook run uses a large share of that, so a `RateLimitError 429` means the daily quota is used up. Switch to another Groq model (for example `openai/gpt-oss-20b`) or wait for the quota to recover.
- `create_react_agent` is deprecated in LangGraph 1.x in favour of `langchain.agents.create_agent`. It still works and only prints a warning.
- The log line `wrote to unknown channel remaining_steps, ignoring it` comes from the supervisor subgraph and is harmless.
