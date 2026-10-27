import argparse

from college_assistant.portal_sync import print_report, run_sync
from college_assistant.storage.database import initialize_database


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check college portal updates when you run the assistant."
    )
    parser.add_argument(
        "--init-db",
        action="store_true",
        help="Initialize the local database without logging into the portal.",
    )
    args = parser.parse_args()

    initialize_database()
    if args.init_db:
        print("Local database initialized successfully.")
        return

    print("Starting a manual portal sync. No background process will be started.")
    results = run_sync()
    print_report(results)


if __name__ == "__main__":
    main()
