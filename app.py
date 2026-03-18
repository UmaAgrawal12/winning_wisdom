from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from agents.topic_agent import fetch_winning_wisdom_quote, fetch_winning_wisdom_quote_for_topic, generate_topics
from agents.script_agent import generate_daily_wisdom_script, DailyWisdomScript, revise_wisdom_script
from agents.score_agent import score_reel_script
from agents.seo_agent import generate_seo_metadata, SEOResult



class TopicProposal(BaseModel):
    topic: str
    quote: str
    source: str


class TopicQuoteRequest(BaseModel):
    topic: str


class DailyFullFlowResponse(BaseModel):
    topic: str
    quote: str
    source: str
    script: DailyWisdomScript
    seo: SEOResult


class TopicApproval(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str


class ScriptApproval(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    approved_script: str


class KeywordRequest(BaseModel):
    keyword: str


class ScriptRevision(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    current_script: str
    suggestions: str


class DailyFlowResponse(BaseModel):
    script: DailyWisdomScript
    score: dict
    seo: SEOResult


app = FastAPI(title="Winning Wisdom Frontend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/topic")
def get_topic():
    """
    Step 1: Generate a topic, then a quote for that topic.
    """
    topics_result = generate_topics(
        theme="Winning Wisdom: discipline, meaning, resilience, self-mastery",
        n=8,
        audience="general_self_improver",
    )
    topic = topics_result.topics[0] if topics_result.topics else "Discipline on the hard days"
    quote_data = fetch_winning_wisdom_quote_for_topic(topic=topic)
    return {"topic": topic, "quote": quote_data["quote"], "source": quote_data["source"]}


@app.post("/api/topic/quote")
def get_quote_for_topic(payload: TopicQuoteRequest) -> TopicProposal:
    """
    Given a topic, fetch a quote aligned to that topic.
    """
    topic = (payload.topic or "").strip()
    quote_data = fetch_winning_wisdom_quote_for_topic(topic=topic)
    return TopicProposal(topic=topic, quote=quote_data["quote"], source=quote_data["source"])


@app.post("/api/topic/approve")
def approve_topic(payload: TopicApproval):
    """
    Step 1b: Approve or override the topic/quote, then preview script.
    """
    script = generate_daily_wisdom_script(
        quote_override=payload.quote,
        source_override=payload.source,
    )
    return script


@app.get("/api/daily-flow")
def daily_flow() -> DailyFullFlowResponse:
    """
    End-to-end flow:
    topic -> quote -> script -> SEO
    """
    topics_result = generate_topics(
        theme="Winning Wisdom: discipline, meaning, resilience, self-mastery",
        n=8,
        audience="general_self_improver",
    )
    topic = topics_result.topics[0] if topics_result.topics else "Discipline on the hard days"
    quote_data = fetch_winning_wisdom_quote_for_topic(topic=topic)

    script = generate_daily_wisdom_script(
        quote_override=quote_data["quote"],
        source_override=quote_data["source"],
    )

    seo = generate_seo_metadata(
        topic=topic,
        script_text=script.spoken_script.full_script,
        audience="general_self_improver",
    )

    return DailyFullFlowResponse(
        topic=topic,
        quote=quote_data["quote"],
        source=quote_data["source"],
        script=script,
        seo=seo,
    )


@app.post("/api/script/approve")
def approve_script(payload: ScriptApproval):
    """
    Step 2: Approve the final script text, then score and generate SEO.
    """
    # Build a DailyWisdomScript using the approved script text
    base_script = generate_daily_wisdom_script(
        quote_override=payload.quote,
        source_override=payload.source,
    )
    base_script.spoken_script.full_script = payload.approved_script

    score = score_reel_script(base_script)
    seo = generate_seo_metadata(
        topic=payload.topic or payload.quote,
        script_text=payload.approved_script,
        audience="general_self_improver",
    )

    return {
        "script": base_script,
        "score": score.dict(),
        "seo": seo,
    }


@app.post("/api/script/from-keyword")
def script_from_keyword(payload: KeywordRequest) -> DailyWisdomScript:
    """
    Generate a fresh script starting from a client-provided keyword.

    The keyword is treated as the core idea or "quote seed" for the day.
    We plug it into the existing daily wisdom generator so the rest of the
    flow (scoring + SEO) can run unchanged.
    """
    # Use the keyword as the quote text so the rest of the pipeline
    # (Arthur persona, scoring, SEO) continues to work without changes.
    script = generate_daily_wisdom_script(
        quote_override=payload.keyword,
        source_override="Client keyword",
    )
    return script


@app.post("/api/script/revise")
def revise_script(payload: ScriptRevision) -> DailyWisdomScript:
    """
    Regenerate the script based on client suggestions.

    The quote and source stay the same, but the spoken script is rewritten
    in Arthur's voice, applying the requested edits.
    """
    script = revise_wisdom_script(
        quote=payload.quote,
        source=payload.source,
        current_script=payload.current_script,
        suggestions=payload.suggestions,
    )
    return script



