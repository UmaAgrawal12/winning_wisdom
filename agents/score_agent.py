"""
AI Scoring Agent for Reel Scripts
==================================
Evaluates generated scripts specifically for Instagram/TikTok reel content.
Provides actionable feedback and scores across multiple dimensions critical
for short-form video performance.
"""

import json
from typing import Optional
from pydantic import BaseModel, Field
from openai import OpenAI
from winning_wisdom_ai.config.system_config import OPENAI_API_KEY, OPENAI_MODEL_TOPIC
from winning_wisdom_ai.config.personas import get_persona
from .script_agent import DailyWisdomScript


client = OpenAI(api_key=OPENAI_API_KEY)


# ─────────────────────────────────────────────────────────────────────
# SCORING MODELS
# ─────────────────────────────────────────────────────────────────────
class DimensionScore(BaseModel):
    """Score for a single dimension (1-10 scale)"""
    score: int = Field(ge=1, le=10, description="Score from 1-10")
    reasoning: str = Field(description="Why this score was given")


class ScriptStrengths(BaseModel):
    """What the script does well"""
    strengths: list[str] = Field(description="2-4 specific strengths")


class ScriptWeaknesses(BaseModel):
    """Areas for improvement"""
    weaknesses: list[str] = Field(description="2-4 specific weaknesses")
    suggestions: list[str] = Field(description="Actionable improvement suggestions")


class ReelScriptScore(BaseModel):
    """Complete scoring breakdown for a reel script"""
    # Dimension scores (1-10)
    hook_strength: DimensionScore = Field(
        description="Opening impact: combined hook strength and scroll-stopping power in the first 2-3 seconds"
    )
    pacing: DimensionScore = Field(description="Appropriate for 30-60 second reel format")
    emotional_impact: DimensionScore = Field(description="Does it resonate and connect?")
    structure: DimensionScore = Field(description="Clear flow, beginning-middle-end")
    persona_consistency: DimensionScore = Field(description="Matches selected persona voice and style")
    visual_potential: DimensionScore = Field(description="Can it work well with video/visuals?")
    
    # Overall assessment
    overall_score: int = Field(ge=1, le=10, description="Overall quality score (weighted average)")
    strengths: ScriptStrengths
    weaknesses: ScriptWeaknesses
    
    # Quick verdict
    verdict: str = Field(description="One-line verdict: 'Ready to post', 'Needs minor tweaks', 'Needs revision', or 'Regenerate'")
    priority_fix: Optional[str] = Field(default=None, description="The single most important thing to fix if score < 7")


# ─────────────────────────────────────────────────────────────────────
# SCORING FUNCTION
# ─────────────────────────────────────────────────────────────────────
def score_reel_script(script: DailyWisdomScript) -> ReelScriptScore:
    """
    Score a reel script across multiple dimensions critical for short-form video.
    
    Evaluates:
    - Opening impact / hook strength (first 3 seconds)
    - Pacing for 30-60 second format
    - Emotional impact
    - Structure and flow
    - Persona consistency (selected persona voice)
    - Visual potential
    
    Args:
        script: The DailyWisdomScript to evaluate
        
    Returns:
        ReelScriptScore with detailed breakdown
    """
    persona_cfg = get_persona(getattr(script, "persona", None))
    spoken_lines = script.spoken_script.full_script.split("\n")
    spoken_text = script.spoken_script.full_script
    first_lines = "\n".join(spoken_lines[:3]) if len(spoken_lines) >= 3 else spoken_text[:100]
    
    prompt = f"""
You are an expert content strategist specializing in short-form video (Instagram Reels, TikTok).
You're evaluating a script for daily reel content that needs to perform well in a competitive feed.

=============================
THE SCRIPT TO EVALUATE
=============================
QUOTE:
"{script.quote}"
— {script.source}

SPOKEN SCRIPT:
{spoken_text}

ON-SCREEN TEXT:
Quote Display: {script.on_screen_text.quote_display}
Caption: {script.on_screen_text.caption}
Highlight Words: {', '.join(script.on_screen_text.highlight_words)}

=============================
THE PERSONA
=============================
{json.dumps(
    {
        "name": persona_cfg.display_name,
        "description": persona_cfg.description,
        "voice_style": persona_cfg.voice_style,
        "content_focus": persona_cfg.content_focus,
        "banned_phrases": persona_cfg.banned_phrases,
    },
    indent=2,
)}

=============================
SCORING CRITERIA
=============================

1. OPENING IMPACT / HOOK STRENGTH (1-10):
   - Measures the combined power of the first 2-3 seconds:
     · How strong and specific the hook is
     · How likely it is to stop scrolling
   - Evaluate opening in the selected persona style.
   - Do NOT over-penalize non-shouty openings if they still feel specific and emotionally direct.
   - Creates tension, curiosity, or clear recognition of a real problem
   - Examples of strong openings:
     · "Most people I knew never did the thing they kept talking about."
     · "There's a kind of tired that has nothing to do with sleep."
   - Score 9-10: Irresistible; very likely to stop scrolling
   - Score 7-8: Strong but could be sharper or more specific
   - Score 5-6: Somewhat generic or soft; may not consistently stop scrolling
   - Score 1-4: Weak opening; unlikely to stop scrolling

3. PACING (1-10):
   - Appropriate for 30-60 second reel format
   - Pacing should fit the selected persona style and still land in 30-60s reel delivery.
   - Not too rushed, not too slow
   - Natural pauses between thoughts
   - Score 9-10: Perfect pacing for reel format
   - Score 7-8: Good pacing, minor adjustments needed
   - Score 5-6: Too fast/slow or wrong rhythm
   - Score 1-4: Pacing doesn't work for reels

4. EMOTIONAL IMPACT (1-10):
   - Does it resonate? Does it connect?
   - Does it make the viewer feel something?
   - Is it relatable and human?
   - Score 9-10: Deeply moving, stays with you
   - Score 7-8: Good emotional connection
   - Score 5-6: Somewhat generic or surface-level
   - Score 1-4: Doesn't connect emotionally

5. STRUCTURE (1-10):
   - Clear flow: hook → body → landing
   - Strong ending that hits hard
   - No rambling or weak conclusion
   - Score 9-10: Perfect structure, powerful ending
   - Score 7-8: Good structure, ending could be stronger
   - Score 5-6: Unclear flow or weak ending
   - Score 1-4: Poor structure, no clear arc

6. PERSONA CONSISTENCY (1-10):
   - Matches selected persona voice and energy
   - Respects persona banned phrases list
   - Score 9-10: Perfect persona voice
   - Score 7-8: Mostly consistent, minor voice issues
   - Score 5-6: Some voice inconsistencies
   - Score 1-4: Doesn't sound like selected persona

7. VISUAL POTENTIAL (1-10):
   - Can this work well with video/visuals?
   - Does it have moments that would benefit from visual emphasis?
   - Are there natural places for cuts, transitions, text overlays?
   - Score 9-10: Highly visual, perfect for reel format
   - Score 7-8: Good visual potential
   - Score 5-6: Somewhat visual but could be better
   - Score 1-4: Not very visual-friendly

=============================
CRITICAL RULES
=============================

- The first 2 lines should create opening impact according to selected persona style.
- If any persona banned phrase appears, persona_consistency should be penalized.
- The ending MUST hit hard. If it's soft, summary-like, or uplifting in a generic way, structure score should be penalized.
- Sentences should be SHORT (5-8 words). If sentences are too long, pacing should be penalized.
- The script should feel PERSONAL and SPECIFIC, not philosophical or abstract. If it's too abstract, emotional_impact should be penalized.

=============================
OUTPUT FORMAT
=============================
Return valid JSON only, no markdown, no preamble:

{{
  "hook_strength": {{
    "score": 8,
    "reasoning": "Strong, specific opening that feels personal and is likely to stop scrolling"
  }},
  "pacing": {{
    "score": 7,
    "reasoning": "Good pacing overall, but a few sentences are slightly long"
  }},
  "emotional_impact": {{
    "score": 8,
    "reasoning": "Connects well, makes viewer reflect on their own life"
  }},
  "structure": {{
    "score": 9,
    "reasoning": "Clear flow with powerful ending that lands hard"
  }},
  "persona_consistency": {{
    "score": 8,
    "reasoning": "Mostly consistent with Arthur's voice, minor phrase that feels slightly off"
  }},
  "visual_potential": {{
    "score": 7,
    "reasoning": "Good visual potential, could benefit from more specific visual moments"
  }},
  "overall_score": 8,
  "strengths": {{
    "strengths": [
      "Hook is strong and scroll-stopping",
      "Ending hits hard and stays with you",
      "Emotional connection is genuine"
    ]
  }},
  "weaknesses": {{
    "weaknesses": [
      "A few sentences are slightly longer than ideal",
      "Could use one more specific visual moment"
    ],
    "suggestions": [
      "Break up the longer sentences into 5-8 word chunks",
      "Add one more concrete, visual detail that viewers can picture"
    ]
  }},
  "verdict": "Ready to post",
  "priority_fix": null
}}

Calculate overall_score as a weighted average:
- hook_strength (opening impact): 35%
- emotional_impact: 15%
- structure: 15%
- pacing: 10%
- persona_consistency: 10%
- visual_potential: 15%

Verdict rules:
- overall_score >= 8.0: "Ready to post"
- overall_score >= 7.0: "Needs minor tweaks"
- overall_score >= 5.0: "Needs revision"
- overall_score < 5.0: "Regenerate"

Priority fix: Only include if overall_score < 7.0. Pick the single most impactful fix.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL_TOPIC,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert content strategist specializing in short-form video content. "
                    "You evaluate scripts for Instagram Reels and TikTok with precision and actionable feedback. "
                    "You understand what makes content stop scrolling and perform well. "
                    "Respond with valid JSON only. No markdown. No preamble. No explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,  # Lower temperature for more consistent scoring
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    
    # Strip markdown fences if present (fallback if response_format didn't work)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()
    
    # Parse JSON
    parsed = json.loads(raw)
    
    # Round overall_score to integer (AI may return float like 7.3)
    overall_score = int(round(parsed["overall_score"]))
    
    # Build the score object
    score = ReelScriptScore(
        hook_strength=DimensionScore(**parsed["hook_strength"]),
        pacing=DimensionScore(**parsed["pacing"]),
        emotional_impact=DimensionScore(**parsed["emotional_impact"]),
        structure=DimensionScore(**parsed["structure"]),
        persona_consistency=DimensionScore(**parsed["persona_consistency"]),
        visual_potential=DimensionScore(**parsed["visual_potential"]),
        overall_score=overall_score,
        strengths=ScriptStrengths(**parsed["strengths"]),
        weaknesses=ScriptWeaknesses(**parsed["weaknesses"]),
        verdict=parsed["verdict"],
        priority_fix=parsed.get("priority_fix"),
    )
    
    return score


# ─────────────────────────────────────────────────────────────────────
# PRETTY PRINT
# ─────────────────────────────────────────────────────────────────────
def print_score(score: ReelScriptScore) -> None:
    """Pretty print the score breakdown"""
    print("\n" + "═" * 70)
    print("  REEL SCRIPT SCORE")
    print("═" * 70)
    
    # Overall score with emoji
    emoji = "🔥" if score.overall_score >= 9 else "✅" if score.overall_score >= 8 else "⚠️" if score.overall_score >= 7 else "❌"
    print(f"\n{emoji}  OVERALL SCORE: {score.overall_score}/10")
    print(f"   Verdict: {score.verdict}")
    
    if score.priority_fix:
        print(f"\n⚠️  PRIORITY FIX: {score.priority_fix}")
    
    # Dimension scores
    print("\n📊  DIMENSION SCORES:")
    print(f"   Opening Impact:       {score.hook_strength.score}/10 — {score.hook_strength.reasoning}")
    print(f"   Pacing:               {score.pacing.score}/10 — {score.pacing.reasoning}")
    print(f"   Emotional Impact:     {score.emotional_impact.score}/10 — {score.emotional_impact.reasoning}")
    print(f"   Structure:            {score.structure.score}/10 — {score.structure.reasoning}")
    print(f"   Persona Consistency:  {score.persona_consistency.score}/10 — {score.persona_consistency.reasoning}")
    print(f"   Visual Potential:     {score.visual_potential.score}/10 — {score.visual_potential.reasoning}")
    
    # Strengths
    print("\n✅  STRENGTHS:")
    for strength in score.strengths.strengths:
        print(f"   • {strength}")
    
    # Weaknesses & Suggestions
    print("\n⚠️  AREAS FOR IMPROVEMENT:")
    for weakness in score.weaknesses.weaknesses:
        print(f"   • {weakness}")
    
    if score.weaknesses.suggestions:
        print("\n💡  SUGGESTIONS:")
        for suggestion in score.weaknesses.suggestions:
            print(f"   • {suggestion}")
    
    print("\n" + "═" * 70 + "\n")

