# Submission Checklist

Use this list before sharing the project, recording the demo, or submitting the archive.

## 1. Deliverables

- [ ] Source code for the FastAPI backend and React frontend
- [ ] `README.md` with prerequisites, setup, configuration, run, test, and limitations
- [ ] `ARCHITECTURE.md`
- [ ] `TESTING.md`
- [ ] `DEMO_SCRIPT.md`
- [ ] This submission checklist
- [ ] Any report or cover sheet required by the course (not included in this repository)
- [ ] Demo screenshots or recording, if required
- [ ] Demo PDF, only if the course expects the input file and it is safe to distribute

Do not put screenshots, private PDFs, or the report inside the source archive unless the
submission instructions explicitly require them.

## 2. Required Software

| Requirement | Verified version | Notes |
| --- | --- | --- |
| macOS | Current test machine | Other platforms are not verified |
| Python | 3.12.15 | Project supports 3.11–3.13 |
| Node.js | 22.23.1 | Vite 8 requires `^20.19.0` or `>=22.12.0` |
| npm | 10.9.8 | Uses `package-lock.json` |
| Ollama | 0.40.8 | Must be running |
| Chat model | `llama3.1:8b` | About 4.9 GB; not bundled |
| Embedding model | `all-MiniLM-L6-v2` | About 90 MB; downloads once from Hugging Face |
| Disk space | About 8 GB total; 10 GB free recommended | Model, Python environment, and Node modules |

The demo machine must have the Ollama model available **before** the demonstration.
Internet is not needed during the demo once the embedding model has been downloaded.

## 3. Fresh Setup Verification

From the repository root:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[rag,dev]"
cp .env.example .env   # optional

cd ../frontend
npm ci
cp .env.example .env   # optional
```

Confirm before submission:

- [ ] `pip install -e ".[rag,dev]"` succeeds from a clean virtual environment
- [ ] `npm ci` succeeds from a clean `node_modules`
- [ ] `ollama list` includes `llama3.1:8b`
- [ ] Backend starts on `http://127.0.0.1:8000`
- [ ] Frontend starts on `http://localhost:5173`
- [ ] `http://127.0.0.1:8000/api/v1/health` reports the LLM as `ready`
- [ ] Dashboard shows the local engine as online
- [ ] A PDF can be uploaded and reaches **ready** status
- [ ] One chat answer returns with at least one source card

## 4. Automated Verification

```bash
cd backend
source .venv/bin/activate
python -m pytest -v
python -m mypy app
python -m ruff check app tests

cd ../frontend
npm run typecheck
npm run lint
npm run build
```

Expected results:

- [ ] Backend: **114 passed**
- [ ] mypy: no errors
- [ ] Ruff: no findings
- [ ] Frontend type check: no errors
- [ ] Frontend lint: no errors
- [ ] Frontend production build: succeeds
- [ ] No frontend automated unit/component test suite exists; this is documented in `TESTING.md`

## 5. Feature Checklist

### Documents

- [ ] Upload a selectable-text PDF up to 25 MB
- [ ] View page, chunk, and character counts
- [ ] Delete a document
- [ ] Reject unsupported file types
- [ ] Reject an image-only PDF with a clear error

### Grounded chat

- [ ] Ask a question across one or more selected documents
- [ ] Receive an answer grounded in retrieved passages
- [ ] Expand a source card and confirm the page number and retrieved text
- [ ] Ask an unrelated question and receive the exact refusal message
- [ ] Ask a follow-up that depends on recent conversation history
- [ ] Create, switch, rename, restore, and delete conversations
- [ ] Confirm deletion requires inline confirmation

### Study tools and history

- [ ] Generate a structured summary
- [ ] Generate exactly 10 flashcards, flip them, navigate, and restart
- [ ] Confirm the deck is saved and reopens from Study History after refresh
- [ ] Generate exactly 5 quiz questions
- [ ] Confirm answer keys/explanations are not visible before submission
- [ ] Submit a complete quiz and see the backend-calculated score, correct/incorrect choices, and explanations
- [ ] Confirm the quiz is saved, reopens completed, and rejects resubmission
- [ ] Delete a saved deck/quiz with inline confirmation
- [ ] Confirm deleting a source document preserves saved sets with a deleted-source warning
- [ ] Confirm duplicate or simple numerically equivalent quiz options are rejected by the backend tests

### Interface and failure handling

- [ ] Light/dark theme switch works
- [ ] Layout is usable at desktop width
- [ ] Layout has no horizontal overflow at 390px width
- [ ] Backend unavailable shows a friendly error banner
- [ ] Retry works after the backend returns
- [ ] No raw exception details are shown in study-tool failures

## 6. Screenshots to Capture

Capture at 1440×900 or larger, with no personal data visible.

- [ ] Dashboard with a ready document and **Local engine: Online**
- [ ] Documents page showing the uploaded PDF and counts
- [ ] Live chat answer with answer text and at least one visible source card
- [ ] Expanded source card showing page number and retrieved passage
- [ ] Prepared contextual follow-up and History entry
- [ ] Optional: grounded refusal for an unrelated question
- [ ] Completed summary
- [ ] Flashcard question, and the same card after flipping
- [ ] Quiz after submission, showing the score and one explanation
- [ ] Study History showing saved decks/quizzes and a completed score
- [ ] Optional: a saved set with a deleted or changed source warning
- [ ] Optional: mobile layout at 390px

Store screenshots outside the repository, or in a clearly named submission-only folder
after checking that they contain no private information.

## 7. Demo Preparation

- [ ] Read `DEMO_SCRIPT.md`
- [ ] Use a PDF that is safe to display
- [ ] Upload and index the demo PDF before the presentation
- [ ] Generate a prepared contextual follow-up, summary, flashcards, and quiz beforehand
- [ ] Keep prepared study results in separate tabs for fast access; completed sets can be reopened from Study History
- [ ] Leave the quiz unsubmitted so scoring can be demonstrated live
- [ ] Do not delete the prepared deck/quiz or its source document before the demo
- [ ] Start the live question in a new conversation and know the 2:30 cutoff
- [ ] Warm up Ollama before presenting
- [ ] Verify the backend, frontend, and Ollama health checks
- [ ] Take fallback screenshots, including the prepared chat answer and source
- [ ] Close notifications and unrelated browser tabs
- [ ] Disable sleep and connect power
- [ ] Rehearse once and stay within 7 minutes
- [ ] Disclose that the follow-up and study outputs were pre-generated with the same local setup
- [ ] Never present prepared output as live generation

## 8. Archive Rules

If submitting a ZIP or folder, include only the project source and documentation.

**Include**
- `backend/app/`
- `backend/tests/`
- `backend/pyproject.toml`
- `backend/ruff.toml`
- `backend/.env.example`
- `frontend/src/`
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/.env.example`
- `frontend/vite.config.ts`
- `frontend/components.json`, `frontend/eslint.config.js`, `frontend/index.html`
- `frontend/postcss.config.js`, `frontend/tailwind.config.ts`
- `frontend/tsconfig.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.node.json`
- `frontend/public/` assets required by the app
- `README.md`
- `ARCHITECTURE.md`
- `TESTING.md`
- `DEMO_SCRIPT.md`
- `SUBMISSION_CHECKLIST.md`
- `.gitignore`

**Exclude**
- `.env` files and any credentials
- `.venv/`
- `node_modules/`
- `frontend/dist/`
- `backend/storage/` (uploads, SQLite database, FAISS indexes)
- `backend/studymate_api.egg-info/`
- `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`
- `.playwright-mcp/` (may contain browser screenshots)
- `.DS_Store`
- `.git/` unless the submission explicitly requires repository history
- Private PDFs, personal screenshots, and generated model caches

Verify staged or archived files:

```bash
git status --short
git status --ignored --short
git ls-files
```

Do not stage ignored local state. The repository currently has no tracked `.env`; keep it
that way.

## 9. Known Limitations to State Clearly

- CPU-only generation is slow: roughly 90–145s for chat and 177–282s for study tools on
  the verified machine.
- Requests are synchronous; there is no streaming or background queue.
- No OCR; image-only PDFs are rejected.
- No authentication or multi-user isolation.
- The frontend has no automated test suite.
- Quiz validation catches duplicate text and simple numeric equivalents, not general
  algebraic or unit equivalence.
- Source-token and answer-specific explanation checks do not guarantee semantic correctness;
  saved sets warn when their source changes but are not regenerated automatically.
- The first embedding run needs internet to download the model; subsequent runs are local.
- Grounding reduces hallucination but does not guarantee correctness.

## 10. Final Gate

- [ ] All required software is installed
- [ ] All automated checks pass
- [ ] A clean upload → chat → source → study-tool → saved-history workflow succeeds
- [ ] Demo outputs and fallback screenshots are prepared
- [ ] No `.env`, secret, private PDF, database, or cache is included
- [ ] Demo completes in 5–7 minutes
- [ ] Known limitations are disclosed
