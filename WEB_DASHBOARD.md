# Local Web Dashboard

The web dashboard is an optional interface. The existing command-line menu remains available.

## Start it on Windows

Activate the project's Conda environment, then from the repository root run:

```powershell
python -m pip install -e .
python -m uvicorn college_assistant.web_app:app --reload
```

Open http://127.0.0.1:8000 in your browser. Stop the server with Ctrl+C.

Click **Check Moodle** in the dashboard. If no saved session exists or Moodle has expired it, the app opens a visible browser window for Microsoft sign-in, keeps it open through any identity-provider redirects, waits until it returns to an authenticated page on the college portal, saves the session locally, and retries the sync automatically. Allow up to five minutes for Microsoft sign-in or MFA. You do not need to run `login.py` or switch to the CLI for session recovery. Keep the dashboard terminal open while this process runs.

## Included actions

- View assignments and their stored due dates, Moodle submission status, and draft status.
- Read stored assignment instructions.
- Refresh assignment information from Moodle, automatically opening sign-in and retrying if the session is missing or expired.
- Generate a Word draft only when Moodle explicitly reports `not_submitted`.
- Download a saved Word draft and mark a draft reviewed locally.

Draft generation may call the configured LLM provider and incur API usage. Drafts are not submitted to Moodle; the dashboard has no submission action.

## Local-only security

This is designed for local use. Run it bound to localhost, and do not expose it directly to the internet or an untrusted network. API responses contain assignment metadata and stored instructions, so keep access to the local service limited to your own computer.
