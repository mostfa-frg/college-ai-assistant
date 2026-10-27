# College AI Assistant

A local-first assistant for checking Moodle course updates and preparing reviewable assignment drafts. It runs only when you launch it; it is not a background service and it never submits work to Moodle.

## Use it without typing Python commands

The default launch now opens an interactive console menu. The menu can:

1. Sync the six configured Moodle courses and download available course materials.
2. List assignments and the local status of drafts.
3. Generate or regenerate a Word draft only for assignments explicitly marked `not_submitted`.
4. Open a saved draft in the default document app.
5. Approve a draft locally for your own review tracking.
6. Open the Moodle login flow and save a local session.
7. Open the local AI provider settings.
8. Show saved assignment instructions.

Approval is only a local status; it does not submit anything. Existing command-line options remain available for troubleshooting and automation, but they are not required for normal use.

## Shareable Windows build

A Windows packaging workflow builds a portable folder containing the executable and Playwright runtime, but **does not bundle Chromium**. This keeps the initial ZIP smaller. The first time a user chooses Moodle login or sync, the app downloads Chromium once into that Windows user's `%LOCALAPPDATA%\CollegeAIAssistant\ms-playwright\` folder. That first setup requires an internet connection and may take a few minutes; subsequent launches reuse the downloaded browser.

To build it yourself on Windows, run PowerShell from the repository folder:

```powershell
.\build_windows.ps1
```

This creates `CollegeAIAssistant-Windows.zip`. Extract the ZIP to a writable folder and launch `Start College AI Assistant.bat` or `CollegeAIAssistant.exe`. No Python installation is needed on the recipient's PC. The GitHub Actions workflow also creates a downloadable artifact named `CollegeAIAssistant-Windows` on pushes to `main`, version tags, or manual workflow runs; artifacts are temporary (30 days).

The first launch creates user-specific files under `%LOCALAPPDATA%\CollegeAIAssistant\`:
- `data\assistant.db`: local database.
- `data\materials\`, `data\processed\`, `data\summaries\`, and `data\solutions\`: local course content and drafts.
- `data\portal-state.json`: local Moodle browser session.
- `.env`: that user's AI provider settings and API keys.
- `ms-playwright\`: the Chromium browser downloaded on first login/sync.

Each friend must sign in to their own Moodle account and configure their own AI API key. Do not share `.env` or `portal-state.json`. The portable program folder contains the executable and Playwright runtime, not your coursework database or login session.

## AI provider configuration

Choose Groq or Gemini in the local `.env` file, opened from menu option 7. Restart the program after changing settings.

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

Choose menu option 6 to open the browser and save your local Moodle session. The current login flow retains the project's existing `ignore_https_errors=True` workaround because the portal has previously shown a certificate warning. **Verify that warning with the college before entering credentials.** Do not share the saved session file; it is equivalent to a credential.

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
