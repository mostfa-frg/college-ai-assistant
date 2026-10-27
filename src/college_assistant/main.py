
from college_assistant.storage.database import initialize_database


def main() -> None:
    initialize_database()
    print("College AI Assistant initialized successfully.")


if __name__ == "__main__":
    main()
