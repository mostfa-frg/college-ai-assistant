import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

BASE_URL = "https://learn3.sha.edu.eg/"
DATA_DIR = PROJECT_ROOT / "data"
MATERIALS_DIR = DATA_DIR / "materials"
PROCESSED_DIR = DATA_DIR / "processed"
SUMMARIES_DIR = DATA_DIR / "summaries"
SOLUTIONS_DIR = DATA_DIR / "solutions"
PORTAL_STATE_FILE = DATA_DIR / "portal-state.json"
DATABASE_PATH = DATA_DIR / "assistant.db"

# Course IDs confirmed during portal inspection.
COURSE_IDS = (
    "1325",  # Cloud computing
    "1327",  # Embedded systems
    "1323",  # Computer security
    "1328",  # Graduation project 1
    "1324",  # Digital image processing
    "1326",  # Distributed systems
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
