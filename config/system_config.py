import os
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in .env")

# SerpAPI for Google search results (optional - for trending topics)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# Model names can be adjusted later if needed
OPENAI_MODEL_TOPIC = "gpt-4.1-mini"
OPENAI_MODEL_SCRIPT = "gpt-4.1-mini"
OPENAI_MODEL_SEO = "gpt-4.1-mini"