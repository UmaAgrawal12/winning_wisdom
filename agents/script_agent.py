import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from config.system_config import OPENAI_API_KEY, OPENAI_MODEL_TOPIC
from .topic_agent import fetch_marcus_aurelius_quote

load_dotenv()

client = OpenAI(api_key=OPENAI_API_KEY)

SCRIPTS_FILE = Path("data/generated_scripts.json")

# ─────────────────────────────────────────────────────────────────────
# PERSONA PROFILE — "Arthur"
# ─────────────────────────────────────────────────────────────────────
PERSONA = {
    "name": "Arthur",
    "age": "78",
    "backstory": (
        "Arthur is a retired schoolteacher and widower who raised three children. "
        "He spent 40 years watching people grow, struggle, and find their way. "
        "He has seen enough of life to know what actually matters — and what doesn't. "
        "He discovered Marcus Aurelius in his 50s and says it changed how he lived his last 25 years."
    ),
    "voice": (
        "Warm, unhurried, and plain-spoken. He talks the way a grandfather does at the dinner table — "
        "not lecturing, just sharing something he genuinely believes. "
        "He never sounds like a motivational speaker. He sounds like someone who has lived it. "
        "His sentences are short — 5 to 8 words each. "
        "He pauses between thoughts. Each sentence lands on its own. "
        "He sometimes admits when something was hard for him personally. "
        "He does not use modern slang, buzzwords, or self-help jargon. "
        "He never summarises or concludes. He just stops when the thought is complete."
    ),
    "banned_phrases": [
        "level up", "hustle", "grind", "game changer", "crush it",
        "unleash", "transform", "unlock your potential", "hack",
        "optimize", "mindset shift", "you got this", "let's go",
        "drop a comment", "smash that like button",
        "we often", "it is important", "in today's world",
        "in conclusion", "as we can see", "it's a reminder that",
        "this teaches us", "this quote", "the lesson here",
        "I remember when", "carrying on", "opening a new page",
        "a bit easier", "moving forward",
    ],
}

# ─────────────────────────────────────────────────────────────────────
# ENTRY ANGLE ROTATION
# Different emotional starting points — keeps each script feeling fresh
# ─────────────────────────────────────────────────────────────────────
ENTRY_ANGLES = [
    "Start with a quiet observation about something most people do without realising it.",
    "Start with a specific type of person Arthur has watched over 40 years — what they did wrong.",
    "Start with a simple contrast between what people chase and what actually holds.",
    "Start with something Arthur got wrong himself for a long time before he understood.",
    "Start with the feeling of being stuck — something the viewer has felt this week but not named.",
    "Start with a hard truth most people know but won't say to themselves.",
    "Start with what it looks like 20 years later when someone ignores this wisdom.",
    "Start with a small, specific moment — the kind that seems ordinary but means everything.",
]


# ─────────────────────────────────────────────────────────────────────
# OUTPUT MODELS
# ─────────────────────────────────────────────────────────────────────
class SpokenScript(BaseModel):
    full_script: str


class OnScreenText(BaseModel):
    quote_display: str
    caption: str
    highlight_words: list[str]


class DailyWisdomScript(BaseModel):
    quote: str
    source: str
    spoken_script: SpokenScript
    on_screen_text: OnScreenText
    generated_at: str


# ─────────────────────────────────────────────────────────────────────
# SCRIPT GENERATOR
# ─────────────────────────────────────────────────────────────────────
def generate_daily_wisdom_script(
    quote_override: Optional[str] = None,
    source_override: Optional[str] = None,
) -> DailyWisdomScript:
    """
    Generate a full daily wisdom script for the Arthur persona.

    Fetches a fresh Marcus Aurelius quote, then uses OpenAI to generate
    a single continuous spoken script and on-screen text.

    Args:
        quote_override: Optionally pass a specific quote
        source_override: Source label for the overridden quote

    Returns:
        DailyWisdomScript
    """
    # 1. Get the quote
    if quote_override:
        quote_data = {
            "quote": quote_override,
            "source": source_override or "Marcus Aurelius — Meditations",
            "fetched_at": datetime.now().isoformat(),
        }
    else:
        quote_data = fetch_marcus_aurelius_quote()

    quote = quote_data["quote"]
    source = quote_data["source"]

    # 2. Pick entry angle
    entry_angle = random.choice(ENTRY_ANGLES)

    # 3. Build prompt
    prompt = f"""
You are writing a short daily wisdom video script for an elderly gentleman named {PERSONA["name"]}, age {PERSONA["age"]}.

=============================
WHO ARTHUR IS
=============================
{PERSONA["backstory"]}

HOW HE SPEAKS:
{PERSONA["voice"]}

BANNED — never use these words or phrases:
{", ".join(PERSONA["banned_phrases"])}

=============================
TODAY'S QUOTE
=============================
"{quote}"
— Marcus Aurelius, Meditations

=============================
YOUR TASK
=============================
Write a 30–60 second spoken script for Arthur.

ENTRY ANGLE — how to open this script:
{entry_angle}

RULES FOR THE SPOKEN SCRIPT:
- No hook. No intro. Arthur starts talking immediately — mid-thought, like you walked in on a conversation.
- Do NOT introduce the quote formally. Arthur weaves the wisdom into his own words naturally.
  He might say the quote almost in passing, or paraphrase it in his own language first.
  He does NOT say "Marcus Aurelius wrote..." or "Today's quote is..." or "He said..."
- Each sentence is 5–8 words. Written on its own line.
- Short pause between thoughts — shown by a blank line between groups.
- No conclusion. No summary. No soft ending.
- Write 8–14 lines total (enough for 30–60 seconds of natural speech).

MOST IMPORTANT RULE — THE REFRAME:
No matter how dark or heavy the quote is, Arthur NEVER dwells in the darkness.
He uses it as a mirror — to make the viewer see something about their own life RIGHT NOW.
The script must make the viewer feel: "This is about me. Today. Not about death."

If the quote is about mortality or impermanence, Arthur reframes it as:
→ urgency to stop wasting the time they have
→ the specific thing they keep putting off
→ the cost of sleepwalking through ordinary days
→ what it feels like to look back and wish you'd chosen differently

SCROLL-STOPPING RULE:
The first 2 lines must make someone stop scrolling.
They must feel immediately personal — like Arthur already knows something about the viewer's life.
Not philosophical. Not poetic. Specific and human.
Examples of scroll-stopping openers (study the pull, do NOT copy):
· "Most people I knew never did the thing they kept talking about."
· "There's a kind of tired that has nothing to do with sleep."
· "I've watched good people waste their best years being careful."
· "You know the thing you keep saying you'll do next week."

THE ENDING:
The last 1–2 lines must be the hardest landing in the whole script.
Not a summary. A final thought that sits with the viewer after the video ends.
Like the last thing someone says before they walk out of the room.
Examples of strong endings (study the weight, do NOT copy):
· "That's the only freedom any of us ever had."
· "Most people never start. That was the whole problem."
· "The day you're waiting for is today. It always was."
· "He knew. He just kept waiting anyway."
· "Forty years I watched that. Never got easier to see."

STRONG EXAMPLE of the right register (do NOT copy — study the rhythm, reframe, and ending):
---
Most people I knew
never did the thing they kept talking about.

Not because they couldn't.
Because they thought there was more time.

Life doesn't announce itself.
It just moves.

One morning you're forty.
Then you're sitting where I'm sitting.

Whatever you're putting off —
it's already later than you think.

Start today.
That's all there ever is.
---

=============================
ON-SCREEN TEXT
=============================
QUOTE DISPLAY:
- Pick ONE phrase from the quote — the single most powerful 4–8 words
- Must fit on one line on a phone screen
- No paraphrasing — exact words from the quote
- If the full quote is short (under 10 words), use it whole
- If long, cut ruthlessly to the sharpest part
- Examples of the right length and weight:
  · "Begin at once to live."
  · "You have power over your mind."
  · "What stands in the way becomes the way."

CAPTION (4–7 words):
- The emotional core of the whole video in one line
- Should feel like something worth screenshotting
- Not a title. Not a summary. A feeling.
- Examples of the right register:
  · "The war is always inside"
  · "You already know what to do"
  · "Time won't wait for readiness"
  · "Stillness is the real strength"
  · "Every day is the whole thing"

HIGHLIGHT WORDS (3–5 words):
- The most emotionally loaded single words from the spoken script
- These will be highlighted in an amber box during video generation
- Pick words that carry the weight of the whole piece
- Single words only, no phrases

=============================
OUTPUT — valid JSON only, no markdown, no extra text
=============================
{{
  "spoken_script": {{
    "full_script": "line 1\\nline 2\\n\\nline 3\\nline 4"
  }},
  "on_screen_text": {{
    "quote_display": "...",
    "caption": "...",
    "highlight_words": ["word1", "word2", "word3"]
  }}
}}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL_TOPIC,
        messages=[
            {
                "role": "system",
                "content": (
                    f"You write short video scripts for Arthur, a 78-year-old retired schoolteacher. "
                    "Arthur speaks the way a wise grandfather talks at the dinner table — "
                    "warm, unhurried, specific, and always personal. "
                    "He never sounds like a motivational speaker or a content creator. "
                    "Every line sounds like it came from someone who actually lived it. "
                    "His endings hit hard and stay quiet — never uplifting, never summarising, just true. "
                    "Respond with valid JSON only. No markdown. No preamble. No explanation."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.88,
    )

    raw = response.choices[0].message.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    parsed = json.loads(raw)

    script = DailyWisdomScript(
        quote=quote,
        source=source,
        spoken_script=SpokenScript(**parsed["spoken_script"]),
        on_screen_text=OnScreenText(**parsed["on_screen_text"]),
        generated_at=datetime.now().isoformat(),
    )

    _save_script(script)
    return script


def generate_youtube_wisdom_script(
    quote_override: Optional[str] = None,
    source_override: Optional[str] = None,
) -> DailyWisdomScript:
    return generate_daily_wisdom_script(
        quote_override=quote_override,
        source_override=source_override,
    )


def generate_tiktok_wisdom_script(
    quote_override: Optional[str] = None,
    source_override: Optional[str] = None,
) -> DailyWisdomScript:
    return generate_daily_wisdom_script(
        quote_override=quote_override,
        source_override=source_override,
    )


def generate_facebook_wisdom_script(
    quote_override: Optional[str] = None,
    source_override: Optional[str] = None,
) -> DailyWisdomScript:
    return generate_daily_wisdom_script(
        quote_override=quote_override,
        source_override=source_override,
    )


# ─────────────────────────────────────────────────────────────────────
# STORAGE HELPERS
# ─────────────────────────────────────────────────────────────────────
def _save_script(script: DailyWisdomScript) -> None:
    SCRIPTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_scripts()
    existing.append(script.model_dump())
    with open(SCRIPTS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def _load_scripts() -> list:
    if not SCRIPTS_FILE.exists():
        return []
    try:
        with open(SCRIPTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return []


def get_all_scripts() -> list[DailyWisdomScript]:
    return [DailyWisdomScript(**s) for s in _load_scripts()]


def get_scripts_count() -> int:
    return len(_load_scripts())


# ─────────────────────────────────────────────────────────────────────
# PRETTY PRINT
# ─────────────────────────────────────────────────────────────────────
def print_script(script: DailyWisdomScript) -> None:
    print("\n" + "═" * 60)
    print(f"  DAILY WISDOM — {script.generated_at[:10]}")
    print("═" * 60)

    print(f"\n📖  QUOTE")
    print(f'  "{script.quote}"')
    print(f"  — {script.source}")

    print(f"\n🎙️  SPOKEN SCRIPT")
    print()
    for line in script.spoken_script.full_script.split("\n"):
        print(f"  {line}" if line.strip() else "")

    print(f"\n📱  ON-SCREEN TEXT")
    print(f"\n  [QUOTE DISPLAY]\n  {script.on_screen_text.quote_display}")
    print(f"\n  [CAPTION]\n  {script.on_screen_text.caption}")
    print(f"\n  [HIGHLIGHT WORDS]\n  {', '.join(script.on_screen_text.highlight_words)}")

    print("\n" + "═" * 60 + "\n")