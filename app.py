from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.topic_agent import fetch_winning_wisdom_quote
from agents.script_agent import generate_daily_wisdom_script, DailyWisdomScript
from agents.score_agent import score_reel_script
from agents.seo_agent import generate_seo_metadata, SEOResult


class TopicApproval(BaseModel):
    quote: str
    source: str


class ScriptApproval(BaseModel):
    quote: str
    source: str
    approved_script: str


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
    Step 1: Propose a topic/quote for today's content.
    """
    quote_data = fetch_winning_wisdom_quote()
    return {"quote": quote_data["quote"], "source": quote_data["source"]}


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
        topic=payload.quote,
        script_text=payload.approved_script,
        audience="general_self_improver",
    )

    return {
        "script": base_script,
        "score": score.model_dump(),
        "seo": seo,
    }



