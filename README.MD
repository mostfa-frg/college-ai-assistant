# College AI Assistant

A local-first assistant for checking college portal updates when you choose to run it.

## Current behavior

- Runs on demand; it does not run as a 24/7 service.
- Checks the six configured Moodle courses and stores the last successful scan in SQLite.
- On the first scan for a course, records a baseline instead of reporting every existing activity as new.
- On later scans, reports newly discovered, renamed/changed, and missing activity links.
- Stores assignment activity links for the next assignment-tracking step.
- Does not summarize every new file, call the LLM during sync, or submit anything to the portal.

**Current limitation:** assignment discovery is implemented, but reliable submission-state detection and automatic solution-draft generation are not implemented yet. Do not treat an assignment as submitted based only on the local presence of a file.

## Setup (Windows / PowerShell)

Activate your existing virtual environment, then install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m playwright install chromium
```

Create a local `.env` from `.env.example` only if you plan to use AI features. Never commit the real `.env`.

## Portal login

Run the existing login script to authenticate and save a local session:

```powershell
python login.py
```

The session is saved to `data/portal-state.json`. It is a credential-equivalent secret:
- Never share it or commit it.
- If it was previously committed or exposed, revoke the session by signing out / invalidating sessions in the portal if possible, then log in again.
- The portal currently has a certificate warning in the existing workflow. `ignore_https_errors=True` is a temporary workaround, not a certificate fix; verify the certificate with the college before entering credentials.

## Run a sync

```powershell
python -m college_assistant.main
```

The first run establishes the baseline for each course. Later runs report detected changes. If you only want to initialize the local database:

```powershell
python -m college_assistant.main --init-db
```

The database is local at `data/assistant.db`. Keep local portal state, the database, downloaded materials, extracted text, and generated summaries out of version control.

## Detection caveat

Current change detection compares activity identity, title, and URL. Moodle may change a due date or assignment instructions without changing the activity link/title; deeper activity-page inspection is needed to detect those content changes. Removed links are reported only after a course page was successfully scanned.
