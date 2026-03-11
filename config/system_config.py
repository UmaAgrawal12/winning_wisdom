import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in .env")

# Model names can be adjusted later if needed
OPENAI_MODEL_TOPIC = "gpt-4.1-mini"
OPENAI_MODEL_SCRIPT = "gpt-4.1-mini"
OPENAI_MODEL_SEO = "gpt-4.1-mini"