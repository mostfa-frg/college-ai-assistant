# College AI Assistant

A local-first assistant for checking Moodle course updates and preparing reviewable assignment drafts. It runs only when you launch it; it is not a background service and it never submits work to Moodle.

## Use it without typing Python commands

The default launch opens a guided console workflow:

1. **Sign in to Moodle** once and save your session locally.
2. **Check Moodle assignments** to refresh course activities and submission status. The quick check does not download every course file or generate drafts automatically.
3. **Prepare an assignment draft** by selecting an assignment explicitly marked `not_submitted`.
4. **Open the Word draft** and review it yourself. The assistant never submits work to Moodle.

Unknown or submitted assignments are not eligible for generation. The menu reminds you when Moodle sign-in or an AI provider key is missing. Other options let you inspect assignments and instructions or record a local review decision.

Course-material downloads are not part of the quick assignment check. Approval is a local status only and never submits anything.

## Optional local web dashboard

Prefer a browser interface? The project also includes a lightweight FastAPI dashboard with no separate frontend build step. It complements the existing CLI; it does not replace it.

From the repository root, with your project environment activated, install the project and start the dashboard:

```powershell
python -m pip install -e .
python -m uvicorn college_assistant.web_app:app --reload
```

Then open http://127.0.0.1:8000. When you use the dashboard's Moodle refresh action, it opens a sign-in browser if the session is missing or expired. Complete Microsoft sign-in at your own pace, then return to the dashboard and click **I've finished signing in — verify Moodle**. The app verifies access before saving the session and refreshing assignments. The dashboard can show assignments and instructions, generate eligible Word drafts, download drafts, and mark drafts reviewed locally.

**Safety:** Draft generation is available only for assignments explicitly marked `not_submitted`. Reviewing a draft records a local status; nothing is submitted to Moodle. Keep the server on localhost and do not expose it to the internet or an untrusted network. See [WEB_DASHBOARD.md](WEB_DASHBOARD.md) for details.

## Shareable Windows build

A Windows packaging workflow builds a portable folder containing the executable and Playwright runtime, but **does not bundle Chromium**. This keeps the initial ZIP smaller. The first time a user chooses Moodle login or sync, the app downloads Chromium once into that Windows user's `%LOCALAPPDATA%\CollegeAIAssistant\ms-playwright\` folder. That first setup requires an internet connection and may take a few minutes; subsequent launches reuse the downloaded browser.

To build it yourself on Windows, run PowerShell from the repository folder:

```powershell
.\build_windows.ps1
```

This creates `CollegeAIAssistant-Windows.zip`. Extract the ZIP to a writable folder and launch `Start College AI Assistant.bat` or `CollegeAIAssistant.exe`. No Python installation is needed on the recipient's PC. GitHub Actions packaging is temporarily disabled. Build the Windows package locally with the PowerShell command above.

The first launch creates user-specific files under `%LOCALAPPDATA%\CollegeAIAssistant\`:
- `data\assistant.db`: local database.
- `data\materials\`, `data\processed\`, `data\summaries\`, and `data\solutions\`: local course content and drafts.
- `data\portal-state.json`: local Moodle browser session.
- `.env`: that user's AI provider settings and API keys.
- `ms-playwright\`: the Chromium browser downloaded on first login/sync.

Each friend must sign in to their own Moodle account and configure their own AI API key. Do not share `.env` or `portal-state.json`. The portable program folder contains the executable and Playwright runtime, not your coursework database or login session.

## AI provider configuration

Choose Groq or Gemini in the local `.env` file, opened from menu option 5. Restart the program after changing settings.

Groq:
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

Optional Tavily fallback research:
```dotenv
TAVILY_API_KEY=your_tavily_api_key
WEB_RESEARCH_ENABLED=true
```

Never commit API keys. Free-tier limits vary by provider and account.

## Moodle login and security

Choose menu option 4 to open the browser and save your local Moodle session. The current login flow retains the project's existing `ignore_https_errors=True` workaround because the portal has previously shown a certificate warning. **Verify that warning with the college before entering credentials.** Do not share the saved session file; it is equivalent to a credential.

## Assignment drafts and source retrieval

- Assignment status is classified conservatively. Draft generation is restricted to assignments explicitly marked `not_submitted`; unknown or submitted assignments are not eligible.
- Drafts are saved as Word documents and should be reviewed before use.
- Local course material is preferred for retrieval. If local retrieval finds no relevant evidence, optional Tavily search can provide external references. External results do not prove board-specific hardware details.
- Retrieval is a lightweight local lexical ranker (BM25-like), not vector embeddings. Readable formats include PDF, DOCX, PPTX, TXT, and Markdown. Scanned PDFs may require OCR.
- No submission is performed by this project.

## Developer setup and tests

Python 3.10+ is required for development:

```powershell
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python -m playwright install chromium
python -m pytest
```

The source checkout continues to store development data in its local `data\` folder and loads `.env` from the repository root. The packaged Windows build uses a per-user data directory so different people can use the same ZIP without sharing sessions or generated files.

## Current limitations

- Moodle page parsing and submission detection rely on visible page text and conservative phrase matching.
- Course sync reports changes to activity identity/title/URL; changes to due dates or instructions that preserve the same link may not be detected.
- Scanned PDFs need OCR.
- The portal certificate warning should be resolved with the college rather than treated as a permanent bypass.
