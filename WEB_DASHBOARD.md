# Local Web Dashboard

The web dashboard is an optional interface. The existing command-line menu remains available.

## Start it on Windows

Activate the project's Conda environment, then from the repository root run:

```powershell
python -m pip install -e .
python -m uvicorn college_assistant.web_app:app --reload
```

Open http://127.0.0.1:8000 in your browser. Stop the server with Ctrl+C.

Before checking Moodle, sign in with the existing CLI workflow (option 4) so the local Moodle session file is created. The dashboard does not collect credentials in the browser.

## Included actions

- View assignments and their stored due dates, Moodle submission status, and draft status.
- Read stored assignment instructions.
- Refresh assignment information from Moodle.
- Generate a Word draft only when Moodle explicitly reports `not_submitted`.
- Download a saved Word draft and mark a draft reviewed locally.

Draft generation may call the configured LLM provider and incur API usage. Drafts are not submitted to Moodle; the dashboard has no submission action.

## Local-only security

This is designed for local use. Run it bound to localhost, and do not expose it directly to the internet or an untrusted network. API responses contain assignment metadata and stored instructions, so keep access to the local service limited to your own computer.
