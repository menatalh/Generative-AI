# Conversational RAG Q&A with PDF Upload and Chat History

A Streamlit app where you upload PDFs and chat about them. Answers are grounded in the retrieved chunks, and follow-up questions are rewritten into standalone questions using the session's chat history before retrieval.



https://github.com/user-attachments/assets/81510c62-9bbf-46ce-9fc2-3f16303f4fed



## Setup

Requires Python 3.12.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

The first run downloads the `all-MiniLM-L6-v2` embedding model from Hugging Face.

## Run

```bash
streamlit run app.py
```

Then, in the sidebar:

1. Paste your Groq API key (starts with `gsk_`, get one at https://console.groq.com/keys).
2. Keep or change the **Session ID**. Each session ID has its own chat history.
3. Upload one or more PDFs (up to 20 MB each).
4. Ask questions in the chat box. Pick **Hybrid**, **Keyword**, or **Semantic** search next to it, and turn on **Show retrieved sources** to see the chunks each answer used.

### Environment variables

None are required. The Groq API key is entered in the UI and kept only in `st.session_state` for the browser session; it is never written to disk.

## How it works

```
PDFs ──> rag/ingest.py ──> chunks ──> Chroma (in memory)
                                          │
question + chat history                   │
   │                                      ▼
   └─> rewrite as standalone question ─> HybridRetriever ─> answer prompt ─> LLM ─> answer
```

- **Ingestion** (`rag/ingest.py`): PyPDFLoader → strip control characters → RecursiveCharacterTextSplitter → HuggingFace embeddings → Chroma. Uploading or removing a file rebuilds the collection from the current files, so chunks never duplicate. Files that are too large, unreadable, or have no extractable text (e.g. scanned) are skipped with a warning.
- **Retrieval** (`rag/retriever.py`): semantic (vector) search, keyword (BM25) search, or both merged with Reciprocal Rank Fusion.
- **Chain** (`rag/pipeline.py`): an LCEL chain that contextualizes the question with chat history, retrieves, and answers only from the retrieved context.
- **History** (`engines/rag_engine.py`): `RunnableWithMessageHistory` with one `InMemoryChatMessageHistory` per session ID, stored in `st.session_state`.

The vector store is in memory (`chromadb.EphemeralClient`), so the index is rebuilt from the uploads each time the app restarts. The notebooks persist to `.chroma/student-rag` for experimentation; that folder is git-ignored.

## Project structure

```
app.py                  Streamlit UI + wiring
chatbot.py              Chatbot façade the UI talks to
config.py               Config: model, chunking, k, file size limit
api_key.py              API key input kept in session state
engines/
  base.py               ChatEngine interface
  simple_faq.py         Legacy FAQ engine from Project 1
  rag_engine.py         RAG engine with per-session history
rag/
  ingest.py             PDF → chunks → embeddings → Chroma
  pipeline.py           Prompts and LCEL chain
  retriever.py          Hybrid / keyword / semantic retriever
01–03_*.ipynb           Notebooks used while building each step
PDFs/                   Sample papers to try the app with
```

## Swapping the engine

The UI depends only on `Chatbot`, which takes any `ChatEngine`:

```python
chatbot = Chatbot(RagChatEngine(rag_chain, store, sources))   # RAG
chatbot = Chatbot(SimpleFAQEngine({"hi": "Hello!"}))          # Project 1 FAQ bot
```

## Configuration

Edit the defaults in `config.py`:

| Setting | Default | Meaning |
|---|---|---|
| `llm_model` | `openai/gpt-oss-120b` | Groq model |
| `temperature` | `0.0` | LLM temperature |
| `embedding_model` | `all-MiniLM-L6-v2` | HuggingFace embedding model |
| `chunk_size` / `chunk_overlap` | `1000` / `200` | Text splitter settings |
| `k` | `4` | Chunks passed to the LLM |
| `fetch_k` | `10` | Candidates per search before merging (hybrid mode) |
| `max_file_mb` | `20` | Larger PDFs are skipped |
