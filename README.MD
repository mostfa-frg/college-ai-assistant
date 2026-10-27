# College AI Assistant

A local-first assistant for checking college portal updates when you choose to run it.

## Current behavior

- Runs on demand; it does not run as a 24/7 service.
- Checks the six configured Moodle courses and stores the last successful scan in SQLite.
- The first scan establishes a baseline; later scans report detected activity-link changes.
- Assignment links are recorded in SQLite.
- Assignment drafts and approved copies are stored locally, with their paths and approval status recorded in SQLite.
- Nothing is submitted to the college portal. Summaries are generated only when explicitly requested.

## Assignment solution review and retrieval

Once a draft exists, list assignments and their states:

```powershell
python -m college_assistant.main --assignments
```

Use the numeric assignment ID shown in the list to review or approve a draft:

```powershell
python -m college_assistant.main --show-solution 3
python -m college_assistant.main --approve-solution 3
```

Approval creates a separate copy under `data/solutions/assignment_<ID>_approved.md` and records the approved state and path in SQLite. You can return to the approved solution at any time using `--show-solution ID` or open the saved Markdown file directly. The draft is retained separately. Do not approve until you have reviewed the solution.

**Important:** the current portal sync discovers assignment links, but deep extraction of instructions, reliable submission-state detection, and automatic draft generation still need to be completed. The approval/retrieval commands are the persistent storage layer; they do not claim a draft exists before one is generated.

## Setup (Windows / PowerShell)

Activate your virtual environment, then install dependencies:

```powershell
python -m pip install -r requirements.txt
python -m pip install -e .
python -m playwright install chromium
```

Create a local `.env` from `.env.example` only if you plan to use AI features. Never commit the real `.env`.

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
