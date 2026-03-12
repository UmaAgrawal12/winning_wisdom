from typing import TypedDict, List
import random
import json
import logging

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from llm_client import topic_llm, script_llm
from agents.seo_agent import generate_seo_metadata, SEOResult
from agents.script_agent import generate_script
from agents.topic_agent import generate_topics


class PipelineState(TypedDict, total=False):
    topics: List[str]
    chosen_topic: str
    script: str
    seo_result: SEOResult
    quality_report: str
    quality_passed: bool


def topic_node(state: PipelineState) -> PipelineState:
    """
    Generate topics using SerpAPI (REQUIRED).
    This function uses generate_topics() from topic_agent.py which fetches
    trending topics directly from Google search via SerpAPI.
    """
    logging.info("topic_node() called - using SerpAPI via generate_topics()")
    
    # Use SerpAPI-based topic generation (REQUIRED)
    # Focus on Stoic philosophy and wisdom-based content
    # n=None means return all available trending topics (flexible count)
    topics_result = generate_topics(
        theme="discipline and self-improvement",
        n=None,  # Get all available trending topics (flexible)
        audience="general_self_improver",
    )
    
    topics = topics_result.topics
    chosen = random.choice(topics) if topics else ""
    
    logging.info("topic_node() complete - generated %d topics, chosen: %r", len(topics), chosen)

    return {"topics": topics, "chosen_topic": chosen}


def script_node(state: PipelineState) -> PipelineState:
    """
    Generate a production-ready short-form script using the dedicated script agent.
    """
    script = generate_script(topic=state["chosen_topic"], audience="general_self_improver")
    return {"script": script.text.strip()}


def script_quality_node(state: PipelineState) -> PipelineState:
    """
    Validate the generated script before it moves further down the pipeline.

    Checks:
    - Script length (aiming for ~30–45 seconds spoken, roughly 110–220 words).
    - Tone and clarity (direct, practical, motivational, no fluff).
    - Platform suitability (short-form vertical video, strong opening, short paragraphs,
      no platform name mentions, no like/subscribe/follow CTAs).
    - Engagement potential (clear hook, concrete insight, specific takeaway).

    The node returns:
    - quality_report: a human-readable review with scores.
    - quality_passed: True if the script meets minimum thresholds, False otherwise.
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
    seo_result = generate_seo_metadata(
        topic=state["chosen_topic"],
        script_text=state["script"],
        audience="general_self_improver",
    )
    return {"seo_result": seo_result}


def build_text_only_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("topics", topic_node)
    graph.add_node("script", script_node)
    graph.add_node("script_quality", script_quality_node)
    graph.add_node("seo", seo_node)

    graph.set_entry_point("topics")
    graph.add_edge("topics", "script")
    graph.add_edge("script", "script_quality")
    graph.add_edge("script_quality", "seo")
    graph.add_edge("seo", END)

    return graph.compile()


def print_seo_output(seo: SEOResult):
    platforms = {
        "youtube": {
            "title": seo.youtube.title,
            "description": seo.youtube.description,
            "hashtags": seo.youtube.hashtags,
        },
        "instagram": {
            "caption": seo.instagram.description,
            "hashtags": seo.instagram.hashtags,
        },
        "tiktok": {
            "caption": seo.tiktok.description,
            "hashtags": seo.tiktok.hashtags,
        },
        "facebook": {
            "caption": seo.facebook.description,
            "hashtags": seo.facebook.hashtags,
        },
    }
    print(json.dumps(platforms, indent=2))


def run_langgraph_pipeline():
    app = build_text_only_graph()
    final_state = app.invoke({})

    print("=== Topics ===")
    for i, t in enumerate(final_state["topics"], start=1):
        print(f"{i}. {t}")

    print("\n=== Chosen Topic ===")
    print(final_state["chosen_topic"])

    print("\n=== Script ===")
    print(final_state["script"])

    print("\n=== SEO JSON ===")
    print_seo_output(final_state["seo_result"])