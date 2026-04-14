import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
# Use override=True so project .env wins over stale shell/system OPENAI_API_KEY / GEMINI_API_KEY.
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# Provider selection: OpenAI first if explicitly requested or if key is present.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LLM_PROVIDER = (os.getenv("LLM_PROVIDER") or ("openai" if OPENAI_API_KEY else "gemini")).strip().lower()

if LLM_PROVIDER == "openai":
    if not OPENAI_API_KEY:
        raise ValueError("LLM_PROVIDER=openai requires OPENAI_API_KEY in .env")
    GEMINI_API_KEY = OPENAI_API_KEY
    GEMINI_OPENAI_BASE_URL = OPENAI_BASE_URL
    _default_model = OPENAI_MODEL or os.getenv("GEMINI_MODEL", "gpt-4o-mini")
else:
    # Google AI Studio often labels the key GOOGLE_API_KEY; GEMINI_API_KEY is the primary name here.
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not GEMINI_API_KEY:
        raise ValueError("Set GEMINI_API_KEY (or GOOGLE_API_KEY) in .env")
    GEMINI_OPENAI_BASE_URL = os.getenv(
        "GEMINI_OPENAI_BASE_URL",
        "https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    _default_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

GEMINI_MODEL_TOPIC = os.getenv("GEMINI_MODEL_TOPIC", _default_model)
GEMINI_MODEL_SCRIPT = os.getenv("GEMINI_MODEL_SCRIPT", _default_model)
GEMINI_MODEL_SEO = os.getenv("GEMINI_MODEL_SEO", _default_model)
