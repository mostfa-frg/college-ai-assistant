
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

DATA_DIR = PROJECT_ROOT / "data"
MATERIALS_DIR = DATA_DIR / "materials"
PROCESSED_DIR = DATA_DIR / "processed"
SUMMARIES_DIR = DATA_DIR / "summaries"

DATABASE_PATH = DATA_DIR / "assistant.db"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL")
