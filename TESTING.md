# Testing Documentation

## Automated Tests

### Backend Tests (pytest)
Run from `backend/` directory with virtual environment activated:

```bash
cd backend
source .venv/bin/activate
python -m pytest -v
```

**Current Results (2026-10-26):** 114 passed (exit 0). This suite uses fake LLM responses and does not require Ollama. Remaining warnings are third-party SWIG/FAISS deprecations.

Test coverage includes:
- Health endpoint
- Document upload and validation
- Document processing
- Chat/Q&A functionality
- Conversation CRUD, message persistence/cascade deletion, and recent-history context
- Retrieval and citations
- Study generation: JSON extraction, exact-count enforcement, source-token grounding, quiz explanations that are short/unsupported/unrelated to the correct answer, repair retry, option/answer validation, duplicate and simple numeric equivalence rejection, answer preservation across option shuffling, too-little-content `400`, missing/unindexed documents, error mapping
- Two-document isolation: separate synthetic ocean/mountain PDFs, prompt scoping, saved source IDs/chunk ownership, no cross-document markers, per-document quiz scoring
- Saved study history: persistence across database close/reopen, submitted answers/scores, conversation preservation, list/detail/delete, source isolation, source change/deletion reporting without reassignment to a later document, pagination-safe ID checks, non-ready documents
- Quiz scoring: answer-key secrecy before submission, server-side scoring, `409` resubmission, `422` wrong answer counts/options, completed-quiz detail
- Deleting a source document preserves saved decks/quizzes while clearing source IDs
- CORS
- Retrieval quality (document isolation, refusal)

`FakeLLM` supports queued responses and errors so failure paths are deterministic without Ollama. Retrieval, database, and API behavior still use the real application components.

### Type Checking
```bash
# Backend
cd backend && source .venv/bin/activate && python -m mypy app

# Frontend
cd frontend && npm run typecheck
```

### Frontend Tests
The frontend does not have an automated unit or component test runner. Its automated
verification is `npm run typecheck`, `npm run lint`, and `npm run build`.

### Linting
```bash
# Backend
cd backend && source .venv/bin/activate && python -m ruff check app tests

# Frontend
cd frontend && npm run lint
```

### Production Build
```bash
cd frontend && npm run build
```

## Verified Environment

- macOS on Apple Silicon
- Python `3.12.15`, Node `v22.23.1`, npm `10.9.8`
- Ollama `0.40.8` with `llama3.1:8b` (`4.9 GB`)
- Backend at `http://127.0.0.1:8000`, frontend at `http://localhost:5173`
- No local `.env` files; documented defaults were used

## Final Validation Commands

Run before packaging or demonstrating:

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

Check the running services separately:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:11434/api/tags
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:5173
```

The health response should report the API and database as healthy and the LLM as
available. A `200` from the frontend confirms Vite is serving the app.

## Live End-to-End Verification

Verified on 2026-10-26 in two passes with the local stack (`llama3.1:8b`).

### Quality-gate live check (temporary database)

This pass used two synthetic PDFs with disjoint facts and a temporary backend/database on port `8011`, so the existing local user database and private uploads were not touched.

- Live Ollama generation succeeded on the first attempt for all four sets: ocean flashcards `44.0s`, ocean quiz `80.3s`, mountain flashcards `29.7s`, mountain quiz `77.3s`.
- Every saved set had the expected source document ID, label, and SHA-256 hash; source chunk IDs belonged only to that document. No marker from the other synthetic document appeared in either saved set.
- The two quizzes were submitted with answers read from their own saved server-side keys and both scored `3/3`. The disclosed explanations referenced their own correct answers and source facts.
- Restarting the temporary backend against the same database retained both decks, both completed quizzes, their selected answers, and their scores. Repeat submissions returned `409`.
- Prompt-scoping assertions are deterministic tests; the live run verifies saved source ownership and absence of cross-document content, not the model's hidden prompt.

### Earlier live UI check (Corporate Finance PDF)

- Real Ollama generation produced exactly 10 flashcards in about 206s and exactly 5 saved quiz questions in about 239s.
- `GET /study/flashcards` and `GET /study/quizzes` returned saved records with source label, source hash, availability, ready status, and unchanged state. Deck/quiz detail endpoints reopened the saved IDs.
- Before submission, quiz `correct_answer`, `explanation`, `selected_answer`, and `is_correct` values were null. Submitting one answer per question returned HTTP 200 with a server-computed score. A repeat submission returned HTTP 409.
- The browser reopened `/flashcards?deck=1` and `/quizzes?quiz=1` from `/history`; flashcards flipped/navigated, the completed quiz showed the score, selected/correct highlighting, and explanations, and the inline delete confirmation opened and canceled without deleting. No browser console errors occurred after a clean reload.
- Frontend `npm run typecheck`, `npm run lint`, and `npm run build` all passed after the page rewrites.
- Earlier verification (2026-10-25): PDF upload/index/delete, summary, chat with five context-dependent follow-ups, exact refusal, persisted 12-message conversation, citation cards, theme switching, mobile layout, and backend-restart recovery all worked. Live chat replies took approximately 90-145s; the summary took about 230s.

Not re-run live in this pass: saved-set deletion, source-changed/deleted warnings, invalid file types, image-only PDF rejection, oversized upload, and a backend restart during an in-flight generation. The backend test suite covers saved-set deletion, source change/deletion, and scoring protections.

## Known Test Gaps

- No frontend automated suite.
- No load/performance tests; timings are single-machine observations.
- QA quality and quiz explanations are not scored by an automated evaluation set; deterministic checks only verify source support and that explanations mention the correct answer.
- General algebraic or unit equivalence between quiz options is not detected.
- Saved-set source warnings and deletion were covered by backend tests but not re-exercised in the browser during the final live pass.

## Manual End-to-End Testing Checklist

### 1. PDF Upload
- [ ] Upload a valid PDF with selectable text
- [ ] Verify processing status changes to ready
- [ ] Check document appears in library with metadata
- [ ] Try uploading invalid file type (should fail)
- [ ] Try uploading PDF with no text (should fail gracefully)

### 2. Grounded Questions and Follow-ups
- [ ] Ask initial question about uploaded PDF
- [ ] Ask pronoun-based follow-up (e.g., "What are its features?")
- [ ] Ask to explain specific point from previous answer
- [ ] Ask question requiring different section of same PDF
- [ ] Ask question not in PDF (should refuse with exact message)
- [ ] Verify sources show relevant passages with page numbers
- [ ] Verify no [Source N] markers in answer text

### 3. Persistent Chat History
- [ ] Create new conversation
- [ ] Exchange multiple messages
- [ ] Switch to different conversation
- [ ] Return to original conversation (messages preserved)
- [ ] Refresh browser (history loads)
- [ ] Restart backend server and reopen conversation
- [ ] Rename conversation
- [ ] Delete conversation (with confirmation)

### 4. Conversation Isolation
- [ ] Create conversation A with PDF 1
- [ ] Create conversation B with PDF 2
- [ ] Verify messages don't leak between conversations
- [ ] Verify document context respected per conversation

### 5. Summaries
- [ ] Generate summary for uploaded document
- [ ] Verify summary contains key points from document
- [ ] Check error handling if document not ready

### 6. Flashcards
- [ ] Generate exactly 10 flashcards from document
- [ ] Flip cards to see answers
- [ ] Navigate between cards
- [ ] Restart flashcard session
- [ ] Refresh and reopen the saved deck from Study History

### 7. Quizzes
- [ ] Generate exactly 5 quiz questions from document
- [ ] Select answers for all questions
- [ ] Confirm no answer key/explanation is visible before submission
- [ ] Submit quiz and verify the backend-calculated score
- [ ] Check correct/incorrect highlighting and explanations
- [ ] Confirm a second submission is rejected
- [ ] Refresh and reopen the completed quiz from Study History

### 8. Study History
- [ ] Verify saved decks/quizzes show title, source, count, date, and score
- [ ] Reopen each saved set by its query-param URL
- [ ] Delete a saved set with inline confirmation
- [ ] Delete a source document and confirm retained sets show a deleted-source warning
- [ ] Change a source document and confirm retained sets show a stale-source warning

### 9. Source-Grounded Study Content
- [ ] Generate from a document with too little text and confirm a friendly `400`
- [ ] Generate from a non-ready document and confirm a clear error
- [ ] Confirm generated counts are exact
- [ ] Confirm questions/cards reference the selected document and do not leak content from another document

### 10. Error Handling
- [ ] Ollama unavailable (stop Ollama, try to chat)
- [ ] Empty question submission
- [ ] No documents selected
- [ ] Network failure simulation
- [ ] Large file upload
