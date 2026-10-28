# StudyMate AI — 5–7 Minute Demo

## Demo Goal

Show one complete local study workflow:

**show an indexed PDF → ask a live grounded question → inspect the cited page → use the study tools → score a quiz**

The target is 6 minutes, with 7 minutes as the hard limit including questions.

## Before the Demo (20–30 Minutes Before)

Do this setup while the screen is not being shared.

### 1. Start the local stack

Run each command block from the repository root.

```bash
# Terminal 1
ollama list
ollama serve          # skip if the macOS app is already running it

# Terminal 2
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 3
cd frontend
npm run dev
```

Confirm:

```bash
curl -fsS http://127.0.0.1:8000/api/v1/health
curl -fsS http://127.0.0.1:11434/api/tags
curl -fsS -o /dev/null -w '%{http_code}\n' http://localhost:5173
```

The health response must report the LLM as `ready`. Open
`http://localhost:5173` and confirm the Dashboard shows **Local engine: Online**.

### 2. Warm up the model

Call Ollama directly so the model is loaded before the demo. This avoids the
cold-start delay:

```bash
curl -sS http://127.0.0.1:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1:8b","prompt":"Reply with OK.","stream":false}'
```

The first Sentence Transformers request may also download `all-MiniLM-L6-v2`. Do this
well before the demo, not during it.

### 3. Prepare the real demo document

Use a PDF with selectable text, no personal information, and clear headings. Upload it
through the UI before the demo and wait until its status is **ready**. Keep a local copy
outside the repository in case you need to test the upload flow again.

Do not commit the demo PDF or put it in the submission archive unless it is intended to
be distributed. The live run shows the upload control and the already-indexed document;
avoid spending demo time on a new upload unless it consistently finishes in under 20
seconds.

### 4. Prepare the live question and fallback outputs

CPU-only generation is slow. Generate everything except the main live question **before**
the demo:

- **Prepared follow-up conversation:** one question plus a contextual follow-up, with
  source cards. Leave this conversation loaded in a dedicated Chat tab and in History.
- **Summaries:** one completed summary.
- **Flashcards:** one completed 10-card deck.
- **Quizzes:** one generated 5-question quiz, **not submitted** so scoring can be shown live.
- **Screenshots:** the prepared answer with an expanded source, the follow-up, summary,
  flashcards, and quiz.

Open a second Chat tab in a **new conversation** for the live question. Keep the prepared
Chat tab loaded as a fallback. Completed decks and quizzes are persisted, so they can be
reopened from **Study History** if a tab is refreshed; avoid refreshing while a generation
is still running.

### 5. Rehearse and prepare fallbacks

- Take screenshots of each completed tab and keep them in a folder outside the repo.
- Use 110–125% browser zoom so text is visible on a projector.
- Close notifications, personal browser tabs, and anything containing private data.
- Plug in power and disable sleep.
- Have a second browser window ready with only the fallback screenshots.
- Have a timer visible.
- Rehearse the live question and know the **2:30 cutoff** described below.

## Say This at the Start (20 seconds)

> “StudyMate AI is a local RAG application. It answers only from the PDFs I upload and
> shows the exact pages it used. This PDF is already indexed. To stay within six minutes
> on CPU-only hardware, I’ll ask the first question live; the follow-up conversation and
> study-tool outputs were generated earlier with this same document and local setup. I’ll
> label those clearly. Quiz scoring is live.”

This disclosure is required. Do not present pre-generated text as a live generation.

## Timed Run of Show

Target **6:00**, hard stop **7:00** including questions. If the live answer is slow, use
the 2:30 cutoff and skip optional detail later.

### 0:00–0:30 — Opening

- Show the Dashboard.
- Point out **Documents**, **Pages indexed**, **Retrieval chunks**, and
  **Local engine: Online**.
- State the problem: general chatbots hallucinate; students need answers tied to their
  own course material.

### 0:30–1:00 — Library and upload

- Open **Documents**.
- Show the uploaded PDF, page count, and ready status.
- Point to **Upload a PDF** and say: extraction, indexing, and storage are local.
- Say the PDF was indexed before the timer to protect the demo time budget. If you plan
  a live upload, it must be rehearsed and finish in under 20 seconds.

### 1:00–2:45 — Live grounded question and citations

- Open the dedicated **live Chat** tab and start a new conversation (click **New** in
  History if an older conversation is open).
- Select only the demo PDF.
- Ask one focused question that has a short, specific answer. Avoid “summarize the whole
  document,” which encourages a long response.
- Start the visible timer. While waiting, explain that the question is embedded, searched
  against the document's FAISS index, and sent with only the retrieved passages.
- When the answer arrives, open one source card and read the page number and retrieved
  passage.
- Say: “The answer is generated only from retrieved chunks. If retrieval finds nothing
  above the relevance threshold, the system refuses without calling the LLM.”

**Hard live-chat cutoff: 2:30.** If the answer has not arrived, switch to the prepared
Chat tab, say that the live generation is taking too long, and continue with the
pre-generated answer. Do not wait on stage.

### 2:45–3:15 — Contextual follow-up and history restore

- If the live question completed, open **History** in that Chat tab and select the
  prepared follow-up conversation. If the live path failed, use the prepared Chat tab.
- Show the contextual follow-up answer.
- Say: “This follow-up was generated earlier with the same document and setup. It
  demonstrates that the six most recent messages are used for context, and the
  conversation is persisted and can be restored.”
- Do not start a second live chat question.

### 3:15–3:50 — Summary

- Open the prepared **Summaries** tab.
- Show the structured headings, key concepts, and definitions.
- Say: “Sampled chunks from the selected document ground this output, and the response
  is checked for non-empty text before it reaches the UI. The flashcard and quiz
  endpoints go further and validate structured JSON.”

### 3:50–4:20 — Flashcards

- Open the prepared **Flashcards** tab.
- Flip two cards.
- Click **Next** once, then **Restart**.
- Say: “The model returns structured JSON, not free-form text, so the UI can turn it
  into interactive revision material. The deck is saved automatically and can be reopened
  from Study History.”

### 4:20–5:25 — Live quiz scoring

- Open the prepared **Quizzes** tab.
- Select one answer per question.
- Click **Submit Quiz**.
- Show the score, correct/incorrect highlighting, and explanation. If every chosen
  answer happens to be correct, there will be no red option to show.
- Say: “The answer key is not sent to the browser before submission. The backend scores
  the quiz, saves the result, and rejects a second submission. Generation also validates
  exact counts, source grounding, duplicate options, and simple numeric equivalents such
  as `0.5`, `1/2`, and `50%`, with one repair retry before a clear error.”

### 5:25–6:05 — How it works and what was tested

Keep this to three sentences:

> “A PDF is parsed page by page and chunked. Chunks are embedded locally with
> Sentence Transformers, stored in SQLite, and searched through per-document FAISS
> indexes. FastAPI retrieves the top passages, builds a grounded prompt, sends it to
> Ollama, and returns the answer with source metadata. Generated study sets are saved
> with source provenance. The backend has 114 automated tests; the frontend is checked
> with TypeScript, ESLint, and a production build.”

Then name one limitation honestly:

> “Generation is CPU-bound, so it is slow; requests are synchronous and there is no
> streaming or background job queue yet. The app is designed for one local user.”

### 6:05–6:45 — Close and questions

- Summarize: local-first, grounded citations, usable study tools, tested.
- Stop talking and invite questions.
- If the live answer used the cutoff or anything ran long, skip optional detail and end
  at the hard stop.

## If Something Fails

### The live answer is slow

At **2:30**, stop waiting. Switch to the prepared Chat tab or a screenshot and say the
live generation exceeded the demo budget. Continue with the prepared answer and citation.
This is why the cutoff exists; it is not a failure to hide.

### Ollama or generation is unavailable

Do not restart everything on stage. Keep using the prepared tabs; their results are
already rendered. Say the local engine is unavailable, show the health banner, and
continue with source inspection and quiz scoring. Mention that the same workflow was
verified earlier and show the backend health output if useful.

### The backend stalls or the page is refreshed

Completed study sets are persisted. Reopen the saved deck or quiz from **Study History**
instead of regenerating. If the tab was refreshed during an in-flight generation, use the
prepared screenshots and continue the narration. Do not wait for a regeneration.

### The frontend will not load

Show the screenshots and the API docs at `http://127.0.0.1:8000/docs`. Explain the
endpoints and architecture; do not spend demo time debugging.

### There is extra time

Show the prepared refusal conversation and explain the deterministic relevance
threshold. Do not run a second live chat question or a full live study-tool generation.

## Do Not Do These During the Demo

- Do not claim a pre-generated result was just generated live.
- Do not start a second live chat question; the follow-up is prepared for a reason.
- Do not wait past the 2:30 live-chat cutoff.
- Do not refresh while a study generation is still running.
- Do not restart the backend during an in-flight generation.
- Do not delete the prepared deck or quiz from Study History during the demo.
- Do not run a full live summary, flashcard, or quiz generation.
- Do not open the `backend/storage/` folder on screen; it may contain private uploads.

## Evidence to Mention

- Backend: **114 tests passed**; mypy and Ruff clean.
- Frontend: type check, lint, and production build pass; no automated frontend test suite.
- Live verification: grounded chat, follow-ups, refusal, citation cards, conversation
  restore, saved flashcard/quiz history, hidden quiz keys, and backend scoring.
- Measured CPU timings: chat ~90–145s; summary ~230s; flashcards ~177–206s; quiz
  ~239–282s. The live demo uses one chat question because of these timings.
