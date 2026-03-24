from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Any
from pathlib import Path
import json
import random
import concurrent.futures
from datetime import datetime

# Supabase (optional; falls back to local JSON file if not configured)
from winning_wisdom_ai.supabase_db import (
    is_supabase_configured,
    list_pipeline_runs as sb_list_pipeline_runs,
    list_approved_pipeline_runs as sb_list_approved_pipeline_runs,
    patch_pipeline_run_approvals as sb_patch_pipeline_run_approvals,
    insert_pipeline_run,
)

# Prefer package imports (works when running from project root)
from winning_wisdom_ai.agents.topic_agent import (
    fetch_winning_wisdom_quote,
    fetch_winning_wisdom_quote_for_topic,
    generate_topics,
    generate_topics_serpapi,
)
from winning_wisdom_ai.agents.script_agent import (
    generate_daily_wisdom_script,
    DailyWisdomScript,
    revise_wisdom_script,
)
from winning_wisdom_ai.agents.score_agent import score_reel_script
from winning_wisdom_ai.agents.seo_agent import generate_seo_metadata, SEOResult
from winning_wisdom_ai.media_pipeline.voice_generation import generate_voice_for_script



class TopicProposal(BaseModel):
    topic: str
    quote: str
    source: str
    persona: str = "arthur"


class TopicQuoteRequest(BaseModel):
    topic: str
    persona: str = "arthur"


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
    persona: str = "arthur"


class ScriptApproval(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    approved_script: str
    persona: str = "arthur"


class KeywordRequest(BaseModel):
    keyword: str
    persona: str = "arthur"


class ScriptRevision(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    current_script: str
    suggestions: str
    persona: str = "arthur"


class DailyFlowResponse(BaseModel):
    script: DailyWisdomScript
    score: dict
    seo: SEOResult


class ScriptVoiceRequest(BaseModel):
    script_text: str
    persona: str = "arthur"
    script_id: Optional[str] = None


def _seo_for_storage(seo: SEOResult) -> dict:
    """
    Normalize SEO payload so captions are explicitly available in Supabase.
    We keep `description` and also add `caption` for convenience.
    """
    raw = seo.model_dump()
    for platform in ("youtube", "instagram", "tiktok", "facebook"):
        block = raw.get(platform)
        if isinstance(block, dict):
            block["caption"] = block.get("description", "")
    return raw


# Stored pipeline runs live at project root /data
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_RUNS_FILE = PROJECT_ROOT / "data" / "pipeline_runs.json"

FALLBACK_TOPICS = [
    "Discipline on the hard days",
    "Stop waiting for confidence",
    "What you can control today",
    "When motivation disappears",
    "The cost of staying comfortable",
    "Doing the right thing quietly",
    "How to face criticism calmly",
    "The difference between pain and suffering",
]


def _generate_topics_with_timeout(timeout_s: float = 8.0) -> list[str]:
    """
    Try LLM-based topic generation, but never block the UI.
    Falls back to a curated topic list on timeout/error.
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(
                generate_topics,
                theme="Winning Wisdom: discipline, meaning, resilience, self-mastery",
                n=8,
                audience="general_self_improver",
            )
            result = fut.result(timeout=timeout_s)
        topics = getattr(result, "topics", None)
        if isinstance(topics, list) and topics:
            cleaned = [t.strip() for t in topics if isinstance(t, str) and t.strip()]
            if cleaned:
                return cleaned
    except Exception:
        pass

    fallback = FALLBACK_TOPICS.copy()
    random.shuffle(fallback)
    return fallback[:8]



def _load_pipeline_runs() -> list[dict[str, Any]]:
    if not PIPELINE_RUNS_FILE.exists():
        return []
    try:
        with PIPELINE_RUNS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def _save_pipeline_runs(runs: list[dict[str, Any]]) -> None:
    PIPELINE_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PIPELINE_RUNS_FILE.open("w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)


class RunApprovalPatch(BaseModel):
    topic_approved: Optional[bool] = None
    script_approved: Optional[bool] = None
    final_approved: Optional[bool] = None


app = FastAPI(title="Winning Wisdom Frontend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_DIR = PROJECT_ROOT / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")


@app.get("/api/topic")
def get_topic(persona: str = "arthur"):
    """
    Step 1: Generate a topic, then a quote for that topic.
    """
    try:
        topics_result = generate_topics_serpapi(
            theme="Winning Wisdom: discipline, meaning, resilience, self-mastery",
            n=8,
            location="United States",
            persona=persona,
        )
        topic = random.choice(topics_result.topics) if topics_result.topics else "Discipline on the hard days"
        quote_data = fetch_winning_wisdom_quote_for_topic(
            topic=topic,
            use_serpapi=True,
            require_serpapi=True,
            persona=persona,
        )
        return {"topic": topic, "quote": quote_data["quote"], "source": quote_data["source"], "persona": persona}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SerpAPI topic/quote generation failed: {e}")


@app.post("/api/topic/quote")
def get_quote_for_topic(payload: TopicQuoteRequest) -> TopicProposal:
    """
    Given a topic, fetch a quote aligned to that topic.
    """
    topic = (payload.topic or "").strip()
    try:
        quote_data = fetch_winning_wisdom_quote_for_topic(
            topic=topic,
            use_serpapi=True,
            require_serpapi=True,
            persona=payload.persona,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SerpAPI quote generation failed: {e}")
    return TopicProposal(topic=topic, quote=quote_data["quote"], source=quote_data["source"], persona=payload.persona)


@app.post("/api/topic/approve")
def approve_topic(payload: TopicApproval):
    """
    Step 1b: Approve or override the topic/quote, then preview script.
    """
    script = generate_daily_wisdom_script(
        quote_override=payload.quote,
        source_override=payload.source,
        persona=payload.persona,
    )
    return script


@app.get("/api/daily-flow")
def daily_flow(persona: str = "arthur") -> DailyFullFlowResponse:
    """
    End-to-end flow:
    topic -> quote -> script -> SEO
    """
    try:
        topics_result = generate_topics_serpapi(
            theme="Winning Wisdom: discipline, meaning, resilience, self-mastery",
            n=8,
            location="United States",
            persona=persona,
        )
        topic = random.choice(topics_result.topics) if topics_result.topics else "Discipline on the hard days"
        quote_data = fetch_winning_wisdom_quote_for_topic(
            topic=topic,
            use_serpapi=True,
            require_serpapi=True,
            persona=persona,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"SerpAPI topic/quote generation failed: {e}")

    script = generate_daily_wisdom_script(
        quote_override=quote_data["quote"],
        source_override=quote_data["source"],
        persona=persona,
    )

    seo = generate_seo_metadata(
        topic=topic,
        script_text=script.spoken_script.full_script,
        audience="general_self_improver",
        persona=persona,
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
        persona=payload.persona,
    )
    base_script.spoken_script.full_script = payload.approved_script

    score = score_reel_script(base_script)
    seo = generate_seo_metadata(
        topic=payload.topic or payload.quote,
        script_text=payload.approved_script,
        audience="general_self_improver",
        persona=payload.persona,
    )

    # If Supabase is configured, persist the approved/scored run so the
    # media generation pipeline can consume it from the DB queue.
    if is_supabase_configured():
        try:
            chosen_topic = (payload.topic or payload.quote or "").strip()
            quality_passed = bool(getattr(score, "overall_score", 0) >= 7)
            priority_fix = getattr(score, "priority_fix", None)
            quality_report = (
                f"Overall {getattr(score, 'overall_score', '')}/10 - {getattr(score, 'verdict', '')}"
            )
            if priority_fix:
                quality_report += f" | Priority fix: {priority_fix}"

            insert_pipeline_run(
                {
                    "chosen_topic": chosen_topic,
                    "script": payload.approved_script,
                    "quality_report": quality_report,
                    "quality_passed": quality_passed,
                    "topic_approved": True,
                    "script_approved": True,
                    "final_approved": True,
                    "seo_result": _seo_for_storage(seo),
                }
            )
        except Exception:
            # Don't block the UI flow if Supabase write fails; backend will still return script/score/SEO.
            pass

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
        persona=payload.persona,
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
        persona=payload.persona,
    )
    return script


@app.post("/api/script/voice")
def generate_script_voice(payload: ScriptVoiceRequest):
    """
    Generate ElevenLabs audio from the current script text.
    """
    text = (payload.script_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="script_text is required.")

    script_id = payload.script_id or f"{payload.persona}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    try:
        audio_path = generate_voice_for_script(
            script_text=text,
            script_id=script_id,
            persona=payload.persona,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Voice generation failed: {e}")

    normalized = audio_path.replace("\\", "/")
    if normalized.startswith("media/"):
        audio_url = f"/{normalized}"
    else:
        audio_url = f"/media/audio/{Path(normalized).name}"
    return {
        "ok": True,
        "persona": payload.persona,
        "audio_path": audio_path,
        "audio_url": audio_url,
    }


@app.get("/api/pipeline-runs")
def list_pipeline_runs(limit: int = 50):
    """
    List the most recent stored pipeline runs (text-only pipeline).
    """
    if is_supabase_configured():
        items = sb_list_pipeline_runs(limit=limit)
        return {"source": "supabase", "count": len(items), "items": items}

    runs = _load_pipeline_runs()
    runs = list(reversed(runs))  # newest first
    return {"source": "local_json", "file": str(PIPELINE_RUNS_FILE), "count": len(runs), "items": runs[:limit]}


@app.get("/api/pipeline-runs/approved")
def list_approved_pipeline_runs(limit: int = 50):
    """
    Return runs that are ready for production (final_approved == true).
    """
    if is_supabase_configured():
        items = sb_list_approved_pipeline_runs(limit=limit)
        return {"source": "supabase", "count": len(items), "items": items}

    runs = _load_pipeline_runs()
    approved = [r for r in runs if bool(r.get("final_approved"))]
    approved = list(reversed(approved))
    return {"source": "local_json", "file": str(PIPELINE_RUNS_FILE), "count": len(approved), "items": approved[:limit]}


@app.patch("/api/pipeline-runs/{run_id}/approve")
def approve_pipeline_run(run_id: str, patch: RunApprovalPatch):
    """
    Patch approval booleans on a stored pipeline run by ID.
    """
    if is_supabase_configured():
        item = sb_patch_pipeline_run_approvals(
            run_id,
            topic_approved=patch.topic_approved,
            script_approved=patch.script_approved,
            final_approved=patch.final_approved,
        )
        return {"ok": True, "source": "supabase", "item": item}

    runs = _load_pipeline_runs()
    for r in runs:
        if str(r.get("id")) == run_id:
            if patch.topic_approved is not None:
                r["topic_approved"] = bool(patch.topic_approved)
            if patch.script_approved is not None:
                r["script_approved"] = bool(patch.script_approved)
            if patch.final_approved is not None:
                r["final_approved"] = bool(patch.final_approved)
            _save_pipeline_runs(runs)
            return {"ok": True, "source": "local_json", "item": r}

    raise HTTPException(status_code=404, detail=f"Run id not found: {run_id}")



