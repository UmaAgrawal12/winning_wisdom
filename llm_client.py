from langchain_openai import ChatOpenAI
from winning_wisdom_ai.config.system_config import (
    OPENAI_API_KEY,
    OPENAI_MODEL_TOPIC,
    OPENAI_MODEL_SCRIPT,
    OPENAI_MODEL_SEO,
)


def topic_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL_TOPIC,
        temperature=0.8,
    )


def script_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL_SCRIPT,
        temperature=0.7,
    )


def seo_llm() -> ChatOpenAI:
    return ChatOpenAI(
        api_key=OPENAI_API_KEY,
        model=OPENAI_MODEL_SEO,
        temperature=0.6,
    )


