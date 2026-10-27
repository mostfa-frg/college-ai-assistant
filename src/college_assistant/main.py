from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from college_assistant.config import DATA_DIR, ENV_FILE, PORTAL_STATE_FILE, SOLUTIONS_DIR
from college_assistant.assignment_solutions import regenerate_assignment_draft
from college_assistant.portal_login import save_portal_login
from college_assistant.portal_sync import print_report, run_sync
from college_assistant.storage.database import initialize_database
from college_assistant.storage.repositories import approve_solution, get_assignment, list_assignments

ENV_TEMPLATE = """# Choose groq or gemini
LLM_PROVIDER=groq
GROQ_API_KEY=
GROQ_MODEL=openai/gpt-oss-120b
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
TAVILY_API_KEY=
WEB_RESEARCH_ENABLED=true
"""


def _list_assignments() -> None:
    assignments = list_assignments()
    if not assignments:
        print("No assignments are recorded yet. Choose 'Sync Moodle' first.")
        return
    for item in assignments:
        print(f'[{item["id"]}] {item["title"]} | course {item["course_id"]} | '
              f'submission: {item["submission_status"]} | solution: {item["solution_status"]}')
        print(f'    {item["url"]}')
        if item.get("solution_path"):
            print(f'    Draft: {item["solution_path"]}')
        if item.get("approved_solution_path"):
            print(f'    Approved copy: {item["approved_solution_path"]}')


def _get_assignment(assignment_id: int) -> dict:
    item = get_assignment(assignment_id)
    if not item:
        raise SystemExit(f"Assignment ID {assignment_id} was not found.")
    return item


def _show_instructions(assignment_id: int) -> None:
    item = _get_assignment(assignment_id)
    print(f'Assignment: {item["title"]}')
    print(f'Submission status: {item["submission_status"]}')
    print(f'Solution status: {item["solution_status"]}')
    print("-" * 72)
    print((item.get("instructions_text") or "").strip() or "No instructions are stored.")


def _solution_path(assignment_id: int) -> Path:
    item = _get_assignment(assignment_id)
    for key in ("approved_solution_path", "solution_path"):
        value = item.get(key)
        if value and Path(value).is_file():
            return Path(value)
    raise SystemExit("No saved Word draft exists for this assignment.")


def _show_solution(assignment_id: int) -> None:
    print(f"Word solution file: {_solution_path(assignment_id).resolve()}")


def _open_solution(assignment_id: int) -> None:
    path = _solution_path(assignment_id)
    print(f"Opening Word draft: {path.resolve()}")
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _approve_solution(assignment_id: int) -> None:
    item = _get_assignment(assignment_id)
    draft = item.get("solution_path")
    if not draft or not Path(draft).is_file():
        raise SystemExit("There is no draft file to approve.")
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    approved = SOLUTIONS_DIR / f"assignment_{assignment_id}_approved.docx"
    shutil.copy2(draft, approved)
    if not approve_solution(assignment_id, approved):
        raise SystemExit("Approval could not be saved to the local database.")
    print(f"Approved copy saved to: {approved.resolve()}")
    print("This only records your local review. Nothing was submitted to Moodle.")


def _configure_ai() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ENV_FILE.exists():
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    print(f"Local settings file: {ENV_FILE.resolve()}")
    print("Add your own provider API key. Never share this file or upload it to GitHub.")
    if sys.platform == "win32":
        os.startfile(str(ENV_FILE))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(ENV_FILE)])
    else:
        subprocess.Popen(["xdg-open", str(ENV_FILE)])
    input("Save your changes, close the editor, then press Enter...")
    print("Settings are read at startup. Restart the assistant to apply changes.")


def _generate_draft() -> None:
    assignments = [x for x in list_assignments() if x.get("submission_status") == "not_submitted"]
    if not assignments:
        print("No assignments explicitly marked not_submitted are available.")
        print("Sync Moodle first. Unknown/submitted assignments are never generated.")
        return
    print("Assignments eligible for draft generation:")
    for item in assignments:
        print(f'[{item["id"]}] {item["title"]} | course {item["course_id"]}')
    raw = input("Enter assignment ID (or Enter to cancel): ").strip()
    if not raw:
        return
    try:
        assignment_id = int(raw)
    except ValueError:
        print("Please enter a numeric assignment ID.")
        return
    if not any(x["id"] == assignment_id for x in assignments):
        print("That assignment is not in the eligible list.")
        return
    result = regenerate_assignment_draft(assignment_id)
    print(f'Generated draft version {result["version"]}: {result["title"]}')
    print(f'Word document: {Path(result["word_path"]).resolve()}')
    print("Nothing was submitted to Moodle. Review the draft before using it.")



def _check_assignments() -> None:
    """Refresh assignment status without generating drafts."""
    if not PORTAL_STATE_FILE.is_file():
        print("First, sign in to Moodle using option 4. Your session stays on this computer.")
        return
    print("\nChecking Moodle assignments...")
    results = run_sync()
    print_report(results)
    assignments = list_assignments()
    eligible = [item for item in assignments if item.get("submission_status") == "not_submitted"]
    print(f"\nReady for review: {len(eligible)} assignment(s) explicitly marked not submitted.")
    if eligible:
        print("Choose option 2 to select an assignment. No draft was generated automatically.")
    elif any(item.get("submission_status") == "unknown" for item in assignments):
        print("Some statuses are unknown. Verify those assignments in Moodle before drafting.")


def _interactive_menu() -> None:
    actions = {
        "1": ("Check Moodle assignments", _check_assignments),
        "2": ("Prepare an assignment draft", _generate_draft),
        "3": ("Open a saved Word draft", lambda: _open_solution(int(input("Assignment ID: ").strip()))),
        "4": ("Sign in to Moodle / refresh session", save_portal_login),
        "5": ("Set up AI provider / API key", _configure_ai),
        "6": ("View assignments and draft status", _list_assignments),
        "7": ("Show assignment instructions", lambda: _show_instructions(int(input("Assignment ID: ").strip()))),
        "8": ("Mark a draft reviewed (local only)", lambda: _approve_solution(int(input("Assignment ID: ").strip()))),
    }
    while True:
        print("\n" + "=" * 56 + "\n             COLLEGE AI ASSISTANT\n" + "=" * 56)
        if not PORTAL_STATE_FILE.is_file():
            print("SETUP NEEDED: sign in to Moodle first (option 4).")
        elif not (os.getenv("GROQ_API_KEY") or os.getenv("GEMINI_API_KEY")):
            print("SETUP NEEDED: configure an AI provider before generating drafts (option 5).")
        print("\nRecommended workflow: 1. Check assignments -> 2. Choose a draft -> 3. Review the Word file")
        for key, (label, _) in actions.items():
            print(f"  {key}. {label}")
        print("  0. Exit")
        choice = input("\nChoose an option: ").strip()
        if choice == "0":
            print("Goodbye. Your local data has been kept.")
            return
        action = actions.get(choice)
        if not action:
            print("Please choose one of the listed options.")
            continue
        try:
            action[1]()
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except (ValueError, OSError, RuntimeError, SystemExit) as exc:
            print(f"\nCould not complete that action: {exc}")
        except Exception as exc:
            print(f"\nUnexpected error: {exc}")
            print("Share the error text for troubleshooting, but never share API keys or portal-state.json.")
        input("\nPress Enter to return to the menu...")

def main() -> None:
    parser = argparse.ArgumentParser(description="College AI Assistant. With no options, opens the interactive menu.")
    parser.add_argument("--init-db", action="store_true", help="Initialize the local database.")
    parser.add_argument("--assignments", action="store_true", help="List recorded assignments and saved solutions.")
    parser.add_argument("--show-instructions", type=int, metavar="ID", help="Print stored assignment instructions.")
    parser.add_argument("--show-solution", type=int, metavar="ID", help="Print the saved draft or approved solution.")
    parser.add_argument("--open-solution", type=int, metavar="ID", help="Open a saved draft in the default document app.")
    parser.add_argument("--approve-solution", type=int, metavar="ID", help="Approve a draft locally; does not submit it.")
    parser.add_argument("--regenerate-draft", type=int, metavar="ID", help="Generate a draft for an explicitly unsubmitted assignment.")
    parser.add_argument("--login", action="store_true", help="Open the Moodle login flow.")
    args = parser.parse_args()
    initialize_database()
    if args.init_db:
        print("Local database initialized successfully.")
    elif args.assignments:
        _list_assignments()
    elif args.show_instructions is not None:
        _show_instructions(args.show_instructions)
    elif args.show_solution is not None:
        _show_solution(args.show_solution)
    elif args.open_solution is not None:
        _open_solution(args.open_solution)
    elif args.approve_solution is not None:
        _approve_solution(args.approve_solution)
    elif args.regenerate_draft is not None:
        result = regenerate_assignment_draft(args.regenerate_draft)
        print(f'Generated draft version {result["version"]} for {result["title"]}.')
        print(f'Word document: {Path(result["word_path"]).resolve()}')
        print("Nothing was submitted to Moodle. Review the draft before approving it.")
    elif args.login:
        save_portal_login()
    else:
        _interactive_menu()


if __name__ == "__main__":
    main()
