from langchain_openai import ChatOpenAI
from config.system_config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_TOPIC,
    GEMINI_MODEL_SCRIPT,
    GEMINI_MODEL_SEO,
    GEMINI_OPENAI_BASE_URL,
)


def topic_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_OPENAI_BASE_URL,
        model=GEMINI_MODEL_TOPIC,
        temperature=0.8,
    )


def script_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_OPENAI_BASE_URL,
        model=GEMINI_MODEL_SCRIPT,
        temperature=0.7,
    )


def seo_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=GEMINI_API_KEY,
        base_url=GEMINI_OPENAI_BASE_URL,
        model=GEMINI_MODEL_SEO,
        temperature=0.6,
    )

