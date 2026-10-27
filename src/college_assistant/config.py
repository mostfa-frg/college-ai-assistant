import os
import sys
from pathlib import Path

from dotenv import load_dotenv

FROZEN = bool(getattr(sys, "frozen", False))
APP_DIR = Path(sys.executable).resolve().parent if FROZEN else Path(__file__).resolve().parents[2]

if FROZEN:
    LOCAL_APP_DATA = Path(os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    USER_APP_DIR = LOCAL_APP_DATA / "CollegeAIAssistant"
    DATA_DIR = USER_APP_DIR / "data"
    ENV_FILE = USER_APP_DIR / ".env"
    BROWSER_DIR = USER_APP_DIR / "ms-playwright"
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSER_DIR)
else:
    PROJECT_ROOT = APP_DIR
    DATA_DIR = PROJECT_ROOT / "data"
    ENV_FILE = PROJECT_ROOT / ".env"
    BROWSER_DIR = None

load_dotenv(ENV_FILE)

BASE_URL = "https://learn3.sha.edu.eg/"
MATERIALS_DIR = DATA_DIR / "materials"
PROCESSED_DIR = DATA_DIR / "processed"
SUMMARIES_DIR = DATA_DIR / "summaries"
SOLUTIONS_DIR = DATA_DIR / "solutions"
PORTAL_STATE_FILE = DATA_DIR / "portal-state.json"
DATABASE_PATH = DATA_DIR / "assistant.db"

COURSE_IDS = (
    "1325",  # Cloud computing
    "1327",  # Embedded systems
    "1323",  # Computer security
    "1328",  # Graduation project 1
    "1324",  # Digital image processing
    "1326",  # Distributed systems
)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")
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
