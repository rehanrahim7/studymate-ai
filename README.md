# StudyMate AI

A study companion that turns the academic PDFs you already have into material you can
actually learn from. Upload a document and StudyMate extracts its text, indexes every
page, and grounds its answers in the source material.

The project runs entirely on your machine: PDFs are parsed with PyMuPDF, stored in SQLite,
and served to a local LLM through Ollama. Nothing leaves your laptop.

---

## Status

Phase 1 — the foundation and the dashboard. What works **today**:

| Area | State |
| --- | --- |
| Responsive dashboard, sidebar navigation, light/dark themes | Done |
| PDF upload with real text extraction (PyMuPDF) and page/chunk indexing | Done |
| Document library — list, inspect and delete uploads | Done |
| FastAPI service with a health check and CORS for local development | Done |
| LLM service interface (modular, Ollama-backed) | Interface done, not yet wired to features |
| Chat with citations, summaries, flashcards, quizzes | Not built yet — the UI shows honest "in development" states |

StudyMate deliberately does **not** show invented summaries, flashcards or quiz answers
before the retrieval pipeline is connected. The routes exist and explain themselves, but
they never fabricate results.

---

## Tech stack

**Frontend** — React 19, Vite, TypeScript, Tailwind CSS, shadcn/ui (Radix primitives),
React Router.

**Backend** — Python 3.12, FastAPI, SQLAlchemy 2, Pydantic Settings, PyMuPDF.

**Retrieval** — Sentence Transformers + FAISS (optional extra, see
[Retrieval extras](#retrieval-extras)).

**LLM** — Ollama, behind a swappable `LLMService` interface.

**Storage** — SQLite.

---

## Prerequisites (macOS)

Install the command line tools first if you have not already:

```bash
xcode-select --install
```

Then install the dependencies with [Homebrew](https://brew.sh):

```bash
# Homebrew (skip if already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.12 — required, because the PyTorch wheels used by
# sentence-transformers do not yet support Python 3.13/3.14
brew install python@3.12

# Node.js 20 or newer
brew install node
```

Check that everything is available:

```bash
python3.12 --version   # Python 3.12.x
node --version         # v20 or newer
npm --version
```

### Optional: Ollama

Ollama is only needed for the AI features (chat, summaries, flashcards, quizzes). The
dashboard and the upload pipeline work without it.

```bash
brew install ollama
ollama serve                 # leave running in its own terminal
ollama pull llama3.1:8b      # the chat model
ollama pull nomic-embed-text # the embedding model
```

---

## Getting started

### 1. Backend

```bash
cd backend

# Create the virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install the app in editable mode (with the dev tooling)
pip install -e ".[dev]"

# Optional: copy and edit the settings
cp .env.example .env

# Start the API with auto-reload
uvicorn app.main:app --reload --port 8000
```

The API is now available at:

- <http://127.0.0.1:8000> — service metadata
- <http://127.0.0.1:8000/api/v1/health> — health check
- <http://127.0.0.1:8000/docs> — interactive OpenAPI documentation

### 2. Frontend

In a second terminal:

```bash
cd frontend

npm install
cp .env.example .env     # optional — the defaults already work

npm run dev
```

Open <http://localhost:5173>.

The two servers run completely independently: the frontend is a static SPA in development
and the API is a standalone service. You can restart either one at any time.

---

## Project structure

```
studymate-ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── deps.py              # shared FastAPI dependencies
│   │   │   └── v1/
│   │   │       ├── documents.py      # upload / list / delete
│   │   │       ├── health.py         # health check
│   │   │       └── router.py         # v1 router aggregation
│   │   ├── core/config.py           # pydantic-settings configuration
│   │   ├── db/                      # engine, session, declarative base
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic response models
│   │   ├── services/
│   │   │   ├── llm/                 # LLMService interface + Ollama adapter
│   │   │   ├── pdf/extractor.py     # PyMuPDF text extraction
│   │   │   └── rag/chunking.py      # page-aware text chunking
│   │   └── main.py                  # FastAPI app, CORS, lifespan
│   ├── storage/                     # SQLite database + uploaded PDFs (git-ignored)
│   ├── tests/                       # pytest suite
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── dashboard/           # stat tiles, empty states
│   │   │   ├── documents/           # upload zone, document list, provider
│   │   │   ├── features/            # study-tool feature cards
│   │   │   ├── health/              # shared health provider
│   │   │   ├── layout/              # app shell, sidebar, top bar
│   │   │   ├── theme/               # theme provider + toggles
│   │   │   └── ui/                  # shadcn/ui primitives
│   │   ├── hooks/                   # useTheme, useHealth, useDocuments
│   │   ├── lib/                     # api client, formatting helpers, cn()
│   │   ├── pages/                   # route components
│   │   └── types/                   # shared TypeScript types
│   ├── index.html
│   ├── tailwind.config.ts
│   └── vite.config.ts
├── .gitignore
└── README.md
```

**Conventions**

- API calls live in `src/lib/api.ts`; UI components never fetch directly. Shared state is
  exposed through providers in `src/components/**` and read through hooks in `src/hooks/**`.
- Backend settings come from the environment through `pydantic-settings`. Secrets are never
  committed — only `.env.example` files are tracked.
- Every backend module and API function is fully type-annotated.

---

## Configuration

Both sides read environment variables from a `.env` file. Copy the provided examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

### Backend (`backend/.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | Runtime environment name |
| `DEBUG` | `true` | Debug flag |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Bind address |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed origins |
| `DATABASE_URL` | `sqlite:///backend/storage/studymate.db` | SQLAlchemy connection URL |
| `MAX_UPLOAD_SIZE_MB` | `25` | Upload size limit |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama server |
| `OLLAMA_CHAT_MODEL` | `llama3.1:8b` | Chat model tag |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding model tag |
| `CHUNK_SIZE` / `CHUNK_OVERLAP` | `1000` / `150` | Retrieval chunking window |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-Transformers model |
| `RETRIEVAL_TOP_K` | `5` | Chunks returned per query |

### Frontend (`frontend/.env`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Base URL of the API |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8000` | Target for the Vite dev proxy |

> Only variables prefixed with `VITE_` reach the browser, and their values are public.
> Never put a secret in a `VITE_*` variable.

---

## API reference

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/health` | Service, database and LLM status |
| `GET` | `/api/v1/documents` | List every uploaded document |
| `POST` | `/api/v1/documents` | Upload a PDF (multipart, field `file`) |
| `GET` | `/api/v1/documents/{id}` | Fetch a single document |
| `DELETE` | `/api/v1/documents/{id}` | Delete a document and its stored file |

Example upload:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents \
  -F "file=@lecture-notes.pdf"
```

---

## Checks

Run these before committing.

**Backend**

```bash
cd backend
source .venv/bin/activate
pytest                 # test suite
ruff check .           # lint
mypy app               # strict type checking
```

**Frontend**

```bash
cd frontend
npm run typecheck      # tsc -b --noEmit
npm run lint           # eslint
npm run build          # typecheck + production build
```

---

## Retrieval extras

`sentence-transformers` and `faiss` pull in PyTorch, which is a large download. They are
therefore kept in an optional extra and only needed once the RAG pipeline is built:

```bash
cd backend
source .venv/bin/activate
pip install -e ".[rag]"
```

---

## Roadmap

1. **Embedding store** — encode `document_chunks` with Sentence Transformers, persist the
   vectors, and index them with FAISS.
2. **Retriever** — embed a question, fetch the top-k chunks, and assemble a context block
   with page numbers attached.
3. **Grounded answers** — send the context to Ollama through `LLMService` and return an
   answer plus the page references it was drawn from.
4. **Study tools** — summaries, flashcards and quizzes generated from the retrieved
   context, each with citations back to the source pages.
5. **Evaluation set** — a small set of question/answer pairs per document to check that
   answers stay grounded and hallucinations stay low.

---

## Troubleshooting

**`python3.12: command not found`**
The Homebrew formulae are not on your `PATH`. Add `export PATH="/opt/homebrew/bin:$PATH"`
to your shell profile, or use the absolute path
`/opt/homebrew/bin/python3.12 -m venv .venv`.

**`ModuleNotFoundError: No module named 'app'`**
Run `uvicorn` from inside the `backend/` directory, or install the package with
`pip install -e ".[dev]"`.

**The dashboard says "API offline"**
The backend is not running, or `VITE_API_BASE_URL` points somewhere else. Check
<http://127.0.0.1:8000/api/v1/health> and the browser console for a CORS error.

**"Model not running" in the sidebar**
Ollama is not running. Start it with `ollama serve` and pull a model with
`ollama pull llama3.1:8b`. The rest of StudyMate works without it.

**Upload returns "No selectable text found"**
The PDF is a scanned image with no embedded text layer. OCR is not implemented yet.

**Port 5173 or 8000 is already in use**
Change the port with `npm run dev -- --port 5174`, or run the API on another port with
`uvicorn app.main:app --port 8001` and update `VITE_API_BASE_URL`.
