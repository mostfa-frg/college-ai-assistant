# College AI Assistant

A local-first assistant for checking college portal updates when you choose to run it.

## Current behavior

- Runs on demand; it does not run as a 24/7 service.
- Checks the six configured Moodle courses and stores the last successful scan in SQLite.
- The first scan establishes a baseline; later scans report detected activity-link changes.
- Assignment links are recorded in SQLite.
- Assignment drafts and approved copies are stored locally, with their paths and approval status recorded in SQLite.
- Nothing is submitted to the college portal. Summaries are generated only when explicitly requested.

## Assignment solutions and course-material RAG

When you run a portal sync, the assistant scans the configured courses and downloads readable Moodle resource/folder files into course-specific folders under `data/materials/`. It then uses course-scoped retrieval to find relevant passages for each assignment-generation chunk. Generated Word drafts include source references when available; if local material does not support a course-specific detail, the model is instructed to flag the gap rather than invent a specification.



If local retrieval finds no matching course passages, the assignment agent can optionally use Tavily web search as a fallback. Web results are labelled with their titles and URLs; course materials remain the preferred source. Configure `TAVILY_API_KEY` in your local `.env` and keep `WEB_RESEARCH_ENABLED=true`. If the key is absent or the search service fails, generation continues without web results. External results are supporting references, not proof that a hardware specification matches the exact board used in class.

The current retrieval implementation is a lightweight local lexical ranker (BM25-like), not vector embeddings. This avoids embedding API costs and keeps materials local. It can be upgraded to hybrid/vector retrieval later without changing the assignment-generation entry point. Readable resources currently include PDF, DOCX, PPTX, TXT, and Markdown files. Scanned-image PDFs still need OCR before they can provide useful text. Assignment extraction preserves question line breaks, and generated citations are checked against the retrieved filenames so placeholder citations are not presented as real sources.

List assignments and their states:

```powershell
python -m college_assistant.main --assignments
```

Use the numeric assignment ID shown in the list to review or approve a draft:

```powershell
python -m college_assistant.main --show-solution 3
python -m college_assistant.main --approve-solution 3
```

The approved copy is saved under `data/solutions/assignment_<ID>_approved.docx`. Review the draft in Word before approving it. Approval only records your local review state; it does not submit anything to Moodle.

**Important:** assignment-page extraction and submission detection use Moodle page text and conservative phrase matching. If the status cannot be recognized, it remains `unknown` and no draft is generated. The portal certificate warning remains a separate security concern; verify it with the college rather than treating certificate bypass as a permanent solution.

## Setup (Windows / PowerShell)

Activate your virtual environment, then install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m playwright install chromium
```

Create a local `.env` from `.env.example` only if you plan to use AI features. Never commit the real `.env`.


## AI provider configuration

Assignment generation supports Groq and Google's Gemini API through the OpenAI-compatible client. Choose one provider in your local, untracked `.env` file:

Groq (default):
```dotenv
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=openai/gpt-oss-120b
```

Gemini:
```dotenv
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.1-flash-lite
```

Create a Gemini API key in Google AI Studio. The code switches provider/model from configuration; no API key belongs in Git. Free-tier quotas vary by model, project, and account, so check the provider's current limits. Gemini's OpenAI-compatible API is documented at https://ai.google.dev/gemini-api/docs/openai.

## Portal login

Run:

```powershell
python login.py
```

The session is saved to `data/portal-state.json`. It is a credential-equivalent secret: never share it or commit it. If it was previously committed or exposed, invalidate the session if possible, then log in again. The portal currently has a certificate warning in the existing workflow; `ignore_https_errors=True` is only a temporary workaround. Verify the certificate with the college before entering credentials.

## Run a sync

```powershell
python -m college_assistant.main
```

Initialize the database without logging in:

```powershell
python -m college_assistant.main --init-db
```

Local portal state, database, downloaded materials, extracted text, summaries, and solutions belong outside version control.

## Detection caveat

Current change detection compares activity identity, title, and URL. Moodle may change due dates or instructions without changing the link/title; deeper activity-page inspection is needed. Removed links are reported only after a course page was successfully scanned.
