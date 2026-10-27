import argparse
import sys
from pathlib import Path

from college_assistant.config import SOLUTIONS_DIR
from college_assistant.assignment_solutions import regenerate_assignment_draft
from college_assistant.portal_sync import print_report, run_sync
from college_assistant.storage.database import initialize_database
from college_assistant.storage.repositories import (
    approve_solution, get_assignment, list_assignments,
)


def _list_assignments() -> None:
    assignments = list_assignments()
    if not assignments:
        print("No assignments are recorded yet. Run a portal sync first.")
        return
    for item in assignments:
        status = item["solution_status"]
        print(f'[{item["id"]}] {item["title"]} | course {item["course_id"]} | '
              f'submission: {item["submission_status"]} | solution: {status}')
        print(f'    {item["url"]}')
        if item.get("solution_path"):
            print(f'    Draft: {item["solution_path"]}')
        if item.get("approved_solution_path"):
            print(f'    Approved copy: {item["approved_solution_path"]}')


def _show_instructions(assignment_id: int) -> None:
    """Print the exact instructions currently stored for an assignment."""
    item = get_assignment(assignment_id)
    if not item:
        raise SystemExit(f"Assignment ID {assignment_id} was not found.")
    instructions = (item.get("instructions_text") or "").strip()
    print(f'Assignment: {item["title"]}')
    print(f'Submission status: {item["submission_status"]}')
    print(f'Solution status: {item["solution_status"]}')
    print(f'Captured instruction characters: {len(instructions)}')
    print("-" * 72)
    if not instructions:
        print("No instructions are stored for this assignment.")
    else:
        print(instructions)


def _show_solution(assignment_id: int) -> None:
    item = get_assignment(assignment_id)
    if not item:
        raise SystemExit(f"Assignment ID {assignment_id} was not found.")
    path_value = item.get("approved_solution_path") or item.get("solution_path")
    if not path_value or not Path(path_value).is_file():
        raise SystemExit("No saved solution file exists for this assignment yet.")
    print(f'Assignment: {item["title"]}\nFile: {path_value}\n')
    print(Path(path_value).read_text(encoding="utf-8"))


def _approve_solution(assignment_id: int) -> None:
    item = get_assignment(assignment_id)
    if not item:
        raise SystemExit(f"Assignment ID {assignment_id} was not found.")
    draft = item.get("solution_path")
    if not draft or not Path(draft).is_file():
        raise SystemExit("There is no draft file to approve.")
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    approved = SOLUTIONS_DIR / f"assignment_{assignment_id}_approved.md"
    approved.write_text(Path(draft).read_text(encoding="utf-8"), encoding="utf-8")
    if not approve_solution(assignment_id, approved):
        raise SystemExit("Approval could not be saved to the local database.")
    print(f"Approved solution saved to: {approved.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check college portal updates and manage assignment solutions.")
    parser.add_argument("--init-db", action="store_true", help="Initialize the local database.")
    parser.add_argument("--assignments", action="store_true", help="List recorded assignments and saved solutions.")
    parser.add_argument("--show-instructions", type=int, metavar="ID", help="Print the instructions stored for an assignment.")
    parser.add_argument("--show-solution", type=int, metavar="ID", help="Print the saved draft or approved solution.")
    parser.add_argument("--approve-solution", type=int, metavar="ID", help="Approve and permanently save a draft solution.")
    parser.add_argument("--regenerate-draft", type=int, metavar="ID", help="Generate a new versioned review draft without overwriting the existing file.")
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
    elif args.approve_solution is not None:
        _approve_solution(args.approve_solution)
    elif args.regenerate_draft is not None:
        try:
            result = regenerate_assignment_draft(args.regenerate_draft)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"Generated draft version {result['version']} for {result['title']}.")
        print(f"Saved locally to: {Path(result['path']).resolve()}")
        print("Nothing was submitted to Moodle. Review the draft before approving it.")
    else:
        print("Starting a manual portal sync. No background process will be started.")
        results = run_sync()
        print_report(results)


if __name__ == "__main__":
    main()
