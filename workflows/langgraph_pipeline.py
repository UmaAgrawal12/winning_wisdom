from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, TypedDict
import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import END, StateGraph

from winning_wisdom_ai.llm_client import script_llm
from winning_wisdom_ai.agents.script_agent import generate_daily_wisdom_script
from winning_wisdom_ai.agents.seo_agent import SEOResult, generate_seo_metadata
from winning_wisdom_ai.supabase_db import insert_pipeline_run, is_supabase_configured


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_RUNS_FILE = PROJECT_ROOT / "data" / "pipeline_runs.json"


class PipelineState(TypedDict, total=False):
    chosen_topic: str
    script: str
    seo_result: SEOResult
    quality_report: str
    quality_passed: bool


def _seo_for_storage(seo: SEOResult) -> dict:
    """
    Normalize SEO payload so captions are explicitly available in Supabase.
    """
    raw = seo.model_dump()
    for platform in ("youtube", "instagram", "tiktok", "facebook"):
        block = raw.get(platform)
        if isinstance(block, dict):
            block["caption"] = block.get("description", "")
    return raw


def script_node(state: PipelineState) -> PipelineState:
    """
    Generate a short-form script using the existing Arthur persona generator.
    """
    daily = generate_daily_wisdom_script()
    script_text = daily.spoken_script.full_script.strip()
    return {"script": script_text}


def script_quality_node(state: PipelineState) -> PipelineState:
    """
    Validate the generated script before it moves further down the pipeline.

    Checks:
    - Length (aiming for ~30–45 seconds spoken, roughly 110–220 words).
    - Tone and clarity (direct, practical, motivational, no fluff).
    - Platform suitability (short-form vertical video, strong opening, line breaks).
    - Engagement (hook, insight, takeaway).
    """
    llm = script_llm()
    prompt = ChatPromptTemplate.from_template(
        """
You are a senior editorial lead for "Winning Wisdom," a motivational short-form video brand.
Your job is to strictly evaluate whether a script is ready for production.

SCRIPT TO REVIEW:
\"\"\"
{script}
\"\"\"

Evaluate this script on the following dimensions, each scored 1–10:
1) Length
   - Target: 30–45 seconds spoken (~110–220 words).
   - Penalize if clearly too short or too long for a short-form vertical video.
2) ToneClarity
   - Target: direct, practical, motivational, no fluff.
   - Plain language. No complicated jargon. Feels like it's talking to one person.
3) PlatformFit
   - Target: short-form vertical video (YouTube Shorts, TikTok, Reels style).
   - Strong opening line (hook), short paragraphs/line breaks, no mention of any platform
     by name, no "like/subscribe/follow" style CTAs.
4) Engagement
   - Target: a specific, relatable hook, a clear insight, and a concrete takeaway.
   - Viewer should feel "this is about me" and know what to do differently after.

SCORING RULES:
- Score each dimension from 1–10 with a one-line explanation.
- OVERALL should be PASS only if:
  * All four dimensions are at least 7/10, AND
  * The script clearly fits a 30–45 second short video.
- Otherwise, OVERALL must be FAIL.

OUTPUT FORMAT (must follow this EXACT structure, no extra lines before or after):
Length: <score>/10 - <short reason>
ToneClarity: <score>/10 - <short reason>
PlatformFit: <score>/10 - <short reason>
Engagement: <score>/10 - <short reason>
OVERALL: PASS   (or OVERALL: FAIL)

Do not add any additional commentary outside this format.
"""
    )
    chain = prompt | llm
    resp = chain.invoke({"script": state["script"]})
    report = resp.content.strip()
    passed = "OVERALL: PASS" in report
    return {"quality_report": report, "quality_passed": passed}


def seo_node(state: PipelineState) -> PipelineState:
    script_text = state.get("script", "") or ""
    first_line = script_text.splitlines()[0] if script_text.splitlines() else ""
    derived_topic = state.get("chosen_topic") or first_line or "Daily Winning Wisdom"

    seo_result = generate_seo_metadata(
        topic=derived_topic,
        script_text=script_text,
        audience="general_self_improver",
    )
    return {"seo_result": seo_result}


def _load_pipeline_runs() -> List[Dict[str, Any]]:
    if not PIPELINE_RUNS_FILE.exists():
        return []
    try:
        with PIPELINE_RUNS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def _save_pipeline_run(state: PipelineState) -> Dict[str, Any]:
    run_id = datetime.utcnow().isoformat(timespec="seconds")
    payload: Dict[str, Any] = {
        # Let Supabase generate UUID/created_at if configured
        "id": run_id,
        "created_at": datetime.utcnow().isoformat(),
        "chosen_topic": state.get("chosen_topic", ""),
        "script": state.get("script", ""),
        "quality_report": state.get("quality_report", ""),
        "quality_passed": bool(state.get("quality_passed", False)),
        "topic_approved": False,
        "script_approved": False,
        "final_approved": False,
    }

    seo = state.get("seo_result")
    if isinstance(seo, SEOResult):
        payload["seo_result"] = _seo_for_storage(seo)
    elif seo is not None:
        payload["seo_result"] = seo
    else:
        payload["seo_result"] = None

    # Prefer Supabase if configured; fallback to local JSON file
    if is_supabase_configured():
        # Remove id/created_at so Supabase defaults apply (uuid + now())
        row = {k: v for k, v in payload.items() if k not in {"id", "created_at"}}
        return insert_pipeline_run(row)

    PIPELINE_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_pipeline_runs()
    existing.append(payload)
    with PIPELINE_RUNS_FILE.open("w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)
    return payload


def build_text_only_graph():
    graph = StateGraph(PipelineState)
    # Node names must NOT collide with state keys (e.g., "script")
    graph.add_node("generate_script", script_node)
    graph.add_node("validate_script", script_quality_node)
    graph.add_node("generate_seo", seo_node)

    graph.set_entry_point("generate_script")
    graph.add_edge("generate_script", "validate_script")
    graph.add_edge("validate_script", "generate_seo")
    graph.add_edge("generate_seo", END)

    return graph.compile()


def print_seo_output(seo: SEOResult):
    platforms = {
        "youtube": {
            "title": seo.youtube.title,
            "description": seo.youtube.description,
            "hashtags": seo.youtube.hashtags,
        },
        "instagram": {"caption": seo.instagram.description, "hashtags": seo.instagram.hashtags},
        "tiktok": {"caption": seo.tiktok.description, "hashtags": seo.tiktok.hashtags},
        "facebook": {"caption": seo.facebook.description, "hashtags": seo.facebook.hashtags},
    }
    print(json.dumps(platforms, indent=2, ensure_ascii=False))


def run_langgraph_pipeline():
    app = build_text_only_graph()
    final_state = app.invoke({})

    saved = _save_pipeline_run(final_state)

    print("\n=== Script ===")
    print(final_state["script"])

    print("\n=== Quality Report ===")
    print(final_state["quality_report"])

    print("\n=== SEO JSON ===")
    print_seo_output(final_state["seo_result"])

    print("\n=== Saved Run Metadata ===")
    print(f"ID: {saved['id']}")
    print(f"File: {PIPELINE_RUNS_FILE}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_langgraph_pipeline()