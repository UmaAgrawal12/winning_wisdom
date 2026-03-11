from typing import TypedDict, List
import random

from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END

from llm_client import topic_llm, script_llm, seo_llm


class PipelineState(TypedDict, total=False):
    topics: List[str]
    chosen_topic: str
    script: str
    seo_json: str


def topic_node(state: PipelineState) -> PipelineState:
    llm = topic_llm()
    prompt = ChatPromptTemplate.from_template(
        """
You are a content strategist for a motivational short-form video brand called "Winning Wisdom".

- Niche: discipline, consistency, mindset, self-improvement, productivity.
- Platforms: YouTube Shorts, TikTok, Instagram Reels, Facebook Reels.
- Output: 10 short topic ideas.
- Style: 5–10 words each, punchy, curiosity-driven, no clickbait.

Theme to focus on: {theme}

Return only a numbered list of topic titles.
"""
    )
    chain = prompt | llm
    resp = chain.invoke({"theme": "discipline and self-improvement"})
    raw_text = resp.content.strip()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    topics: List[str] = []
    for line in lines:
        cleaned = line
        if "." in line[:3] or ")" in line[:3]:
            cleaned = line.split(".", 1)[-1].split(")", 1)[-1].strip()
        topics.append(cleaned)

    # Pick a random topic from the generated list for more variety
    chosen = random.choice(topics) if topics else ""

    return {"topics": topics, "chosen_topic": chosen}


def script_node(state: PipelineState) -> PipelineState:
    llm = script_llm()
    prompt = ChatPromptTemplate.from_template(
        """
You are a senior short-form script writer for a motivational brand called "Winning Wisdom".

Write a script for a 30–45 second vertical video based on the topic:
"{topic}"

Constraints:
- Structure: Hook → Insight → Example → Takeaway.
- Tone: direct, practical, motivational, no fluff.
- Audience: people who struggle with discipline and consistency.
- Format: Use short paragraphs and line breaks for natural pacing.
- Do NOT mention any platform (YouTube, TikTok, etc.).
- Do NOT ask people to like/subscribe/follow.

Return only the script text.
"""
    )
    chain = prompt | llm
    resp = chain.invoke({"topic": state["chosen_topic"]})
    return {"script": resp.content.strip()}


def seo_node(state: PipelineState) -> PipelineState:
    llm = seo_llm()
    prompt = ChatPromptTemplate.from_template(
        """
You are an expert social media copywriter for a motivational brand "Winning Wisdom".

Here is the script:

\"\"\"{script_text}\"\"\"

1) Create an engaging video TITLE.
2) Write a short DESCRIPTION or CAPTION (1–3 sentences).
3) Suggest 8–12 relevant HASHTAGS (without the # symbol, just words).

Do this separately for each platform:
- YouTube
- Instagram
- TikTok
- Facebook

Return the result strictly as JSON in this format (keys and structure MUST match):

{{
  "youtube": {{
    "title": "...",
    "description": "...",
    "hashtags": ["...", "..."]
  }},
  "instagram": {{
    "title": "...",
    "description": "...",
    "hashtags": ["...", "..."]
  }},
  "tiktok": {{
    "title": "...",
    "description": "...",
    "hashtags": ["...", "..."]
  }},
  "facebook": {{
    "title": "...",
    "description": "...",
    "hashtags": ["...", "..."]
  }}
}}
"""
    )
    chain = prompt | llm
    resp = chain.invoke({"script_text": state["script"]})
    return {"seo_json": resp.content.strip()}


def build_text_only_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("topics", topic_node)
    graph.add_node("script", script_node)
    graph.add_node("seo", seo_node)

    graph.set_entry_point("topics")
    graph.add_edge("topics", "script")
    graph.add_edge("script", "seo")
    graph.add_edge("seo", END)

    return graph.compile()


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
    print(final_state["seo_json"])


