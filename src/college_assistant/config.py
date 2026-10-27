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

# Provider can be "groq" or "gemini". Existing Groq .env files keep working.
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

# Optional Tavily web search used only when local course retrieval finds no evidence.
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
WEB_RESEARCH_ENABLED = os.getenv("WEB_RESEARCH_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}

if LLM_PROVIDER == "gemini":
    LLM_API_KEY = GEMINI_API_KEY
    LLM_MODEL = GEMINI_MODEL
    LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
elif LLM_PROVIDER == "groq":
    LLM_API_KEY = GROQ_API_KEY
    LLM_MODEL = GROQ_MODEL
    LLM_BASE_URL = "https://api.groq.com/openai/v1"
else:
    raise ValueError("LLM_PROVIDER must be 'groq' or 'gemini'.")
