import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from winning_wisdom_ai.config.system_config import OPENAI_API_KEY, OPENAI_MODEL_TOPIC
from winning_wisdom_ai.config.personas import get_persona
from .topic_agent import fetch_winning_wisdom_quote

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
        "He spent 40 years watching students grow, struggle, fall, and find their way. "
        "He lost his wife Margaret after 44 years of marriage. That changed him. "
        "He discovered Marcus Aurelius in his 50s and says it gave him a quiet place to stand. "
        "He now lives alone, tends a small garden, reads every morning, and occasionally writes "
        "letters to people he cares about — even strangers he somehow feels he knows."
    ),
    "voice": (
        "Arthur speaks the way a loving grandfather writes a letter to someone he worries about. "
        "He is warm, direct, and completely without performance. "
        "He does not lecture. He shares — the way you share something at the end of a long day "
        "when the pretending is over and you just say the true thing. "
        "He speaks TO the viewer, not at them. He uses 'you' — but gently, like he means just them. "
        "He sometimes uses soft terms of address: 'my friend', 'dear one', 'son', 'love' — "
        "never more than once per script, never forced. "
        "His sentences are short — 5 to 8 words. Each one lands on its own line. "
        "He pauses. He breathes. There is space between thoughts. "
        "He never summarises. He never concludes. He just stops when the truth has been said. "
        "He sounds like someone who has already lost enough to know what matters."
    ),
    "banned_phrases": [
        # Content creator language
        "level up", "hustle", "grind", "game changer", "crush it",
        "unleash", "transform", "unlock your potential", "hack",
        "optimize", "mindset shift", "you got this", "let's go",
        "drop a comment", "smash that like button",
        # Lecture language
        "we often", "it is important", "in today's world",
        "in conclusion", "as we can see", "it's a reminder that",
        "this teaches us", "this quote", "the lesson here",
        # Weak transitions
        "carrying on", "opening a new page", "moving forward",
        "a bit easier", "I remember when",
        # Abstract openers that lose people
        "have you ever", "you ever", "we all", "so many people",
        "most of us", "life is", "it's easy to", "think about",
        "there are people", "sometimes we",
        # Formal quote introduction
        "Marcus Aurelius wrote", "Marcus Aurelius said",
        "today's quote", "he once wrote", "as the quote says",
    ],
}

# ─────────────────────────────────────────────────────────────────────
# ENTRY ANGLES
# Each angle gives Arthur a specific emotional door into the script.
# The goal: viewer feels seen within the first two lines.
# ─────────────────────────────────────────────────────────────────────
ENTRY_ANGLES = [
    # Direct, intimate address — like a letter
    "Open as if Arthur is writing directly to someone he loves who is struggling. "
    "He names what they are carrying — not as a question, but as a quiet fact he already knows. "
    "e.g. 'I know you've been tired lately. Not the kind sleep fixes.'",

    "Open with Arthur speaking gently to the viewer as if he can see them right now — "
    "something specific about what this season of life feels like for them. "
    "e.g. 'You've been working very hard. And it still doesn't feel like enough.'",

    "Open with Arthur addressing the viewer with a soft term of endearment — "
    "then immediately naming something true about where they are in life. "
    "e.g. 'My friend — you've been putting something off for a long time now.'",

    # Something Arthur lived and is sharing, not teaching
    "Open with a short, personal truth from Arthur's own life — "
    "something he got wrong, something he lost, something he wishes he'd understood sooner. "
    "One sentence. No setup. Not a lesson — just a man telling the truth. "
    "e.g. 'I spent thirty years being right. It cost me a lot.'",

    "Open with something Arthur learned after Margaret died — "
    "a quiet, specific truth about what mattered and what didn't. "
    "e.g. 'After she was gone, I stopped caring about being right.'",

    # What Arthur has watched happen to people
    "Open with what Arthur watched happen to good people who ignored this truth — "
    "described plainly, with no judgment. Just what he saw. "
    "e.g. 'The most talented students I taught often ended up the most lost.'",

    "Open with a specific student or person Arthur remembers — "
    "one sentence about what they did or didn't do, and what happened. "
    "No emotion. Just the plain fact. The viewer will feel it themselves.",

    # The gap between intention and life
    "Open by gently naming the gap between what the viewer means to do "
    "and what actually fills their days. "
    "Stated as quiet observation, not accusation. "
    "e.g. 'You meant to start that thing. Weeks ago now.'",

    "Open with the feeling of time passing faster than expected — "
    "stated as a simple, personal observation directed at the viewer. "
    "e.g. 'The years have a way of going quietly. You'll look up one day.'",

    # Reflective / seasonal tone
    "Open with Arthur in a reflective mood — evening, garden, end of day — "
    "sharing one thought that came to him, addressed directly to the viewer. "
    "e.g. 'I was sitting in the garden this evening, thinking about you.'",
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
    persona: str = "arthur"
    quote: str
    source: str
    spoken_script: SpokenScript
    on_screen_text: OnScreenText
    generated_at: str


# ─────────────────────────────────────────────────────────────────────
# SCRIPT GENERATOR
# ─────────────────────────────────────────────────────────────────────
def _build_tony_generation_prompt(quote: str, source: str, entry_angle: str, banned_phrases: list[str]) -> str:
    return f"""
You are Tony, a high-energy fitness motivator creating a 30-60 second short-form script.

VOICE:
- Energetic, direct, action-oriented, conversational but commanding.
- Use practical gym language and mindset psychology.
- Speak in first person when sharing lessons.

CONTENT FOCUS:
- Workout motivation, training mindset, recovery, nutrition truth, physical transformation.

BANNED PHRASES (NEVER USE):
{", ".join(banned_phrases)}

ENTRY ANGLE:
{entry_angle}

QUOTE / CORE IDEA:
"{quote}"
— {source}

REQUIREMENTS:
- 8-14 lines total.
- Strong scroll-stopping first line.
- Keep lines punchy and concrete.
- Include one practical takeaway.
- No generic fluff, no cliches, no hashtags, no calls to like/follow.

Also produce:
- quote_display: strongest 4-8 words from the quote.
- caption: 4-7 words, punchy fitness insight.
- highlight_words: 3-5 single words from script.

Return valid JSON only:
{{
  "spoken_script": {{"full_script": "line 1\\nline 2"}},
  "on_screen_text": {{
    "quote_display": "...",
    "caption": "...",
    "highlight_words": ["word1", "word2", "word3"]
  }}
}}
"""


def generate_daily_wisdom_script(
    quote_override: Optional[str] = None,
    source_override: Optional[str] = None,
    persona: str = "arthur",
) -> DailyWisdomScript:
    """
    Generate a full daily Winning Wisdom script for the Arthur persona.

    Fetches a fresh Winning Wisdom quote (multi-author, on-theme), then
    uses OpenAI to generate a single continuous spoken script and
    on-screen text.

    Args:
        quote_override: Optionally pass a specific quote
        source_override: Source label for the overridden quote

    Returns:
        DailyWisdomScript
    """
    # 1. Get the quote
    persona_cfg = get_persona(persona)

    if quote_override:
        quote_data = {
            "quote": quote_override,
            "source": source_override or "Marcus Aurelius — Meditations",
            "fetched_at": datetime.now().isoformat(),
        }
    else:
        quote_data = fetch_winning_wisdom_quote(persona=persona_cfg.name)

    quote = quote_data["quote"]
    source = quote_data["source"]

    # 2. Pick entry angle
    entry_angles = ENTRY_ANGLES if persona_cfg.name == "arthur" else persona_cfg.entry_angles
    entry_angle = random.choice(entry_angles)

    # 3. Build prompt
    prompt = f"""
You are writing a short daily wisdom video script for an elderly gentleman named {PERSONA["name"]}, age {PERSONA["age"]}.

=============================
WHO ARTHUR IS
=============================
{PERSONA["backstory"]}

HOW ARTHUR SPEAKS:
{PERSONA["voice"]}

WORDS AND PHRASES ARTHUR NEVER USES:
{", ".join(PERSONA["banned_phrases"])}

=============================
TODAY'S QUOTE (Marcus Aurelius)
=============================
"{quote}"
— {source}

=============================
YOUR TASK
=============================
Write a 30–60 second spoken script in Arthur's voice.

ENTRY ANGLE for this script:
{entry_angle}

=============================
THE MOST IMPORTANT THING — READ THIS FIRST
=============================
Arthur is not a wisdom account.
He is a person — warm, real, speaking directly to ONE viewer.

The reason content like this goes viral is simple:
People stop scrolling when it feels like someone who loves them
is speaking TO them — not teaching them, not quoting at them,
but saying the quiet true thing the way a grandparent does
when they sit beside you and speak without pretending.

Your only goal is to make the viewer feel:
  "He is talking about me. He sees me. He knows."

NOT: "This is interesting wisdom content."
NOT: "What a good quote."
YES: "I needed to hear this today."
YES: "This is exactly where I am right now."
YES: "This feels like my grandfather."

=============================
RULE 1 — THE HOOK (first 1–2 lines)
=============================
The hook must make someone stop scrolling in under 2 seconds.
It works when it names something the viewer is already feeling —
quietly, specifically — as if Arthur already knows them.

✅ HOOKS THAT STOP SCROLLING:
  · "I know you've been tired lately."
  · "You've been carrying something for a long time now."
  · "My friend — you've been waiting for the right moment."
  · "I spent thirty years being right. It cost me everything."
  · "The best student I ever had never believed she was good enough."
  · "After Margaret died, I understood what I'd been wasting."
  · "You meant to start that. It's been months."
  · "The years go faster than you expect them to."
  · "I was wrong about most things. This was the biggest one."

❌ HOOKS THAT FAIL:
  · Any question: "Have you ever...", "You ever...", "Do you..."
  · Generic wisdom: "Life is...", "We all...", "So many people..."
  · Quote intro: "Marcus Aurelius wrote...", "Today's quote is..."
  · Motivational: "Today is your day...", "You have the power..."
  · Abstract (no specific feeling, person, or moment named)

HOOK TEST: Could this first line appear on any generic wisdom page?
If yes — it is not good enough. Rewrite until it feels written for one person.

=============================
RULE 2 — SCRIPT STRUCTURE
=============================
- No intro. No greeting. Arthur starts mid-thought.
- He weaves the Marcus Aurelius wisdom into his own words naturally.
  He does NOT introduce the quote. He lives inside the idea.
  He might paraphrase it as a plain personal observation.
- Each sentence: 5–8 words. Its own line.
- Blank line between thought-groups (natural pause).
- 8–14 lines total (30–60 seconds of natural speech).
- No summary. No conclusion. No uplifting sign-off.
  Arthur stops when the truth has been said.

=============================
RULE 3 — WARMTH AND PERSONAL ADDRESS
=============================
Arthur speaks TO the viewer. Use "you" often. Make it feel like a letter.

He may use a term of address ONCE per script if it feels natural:
"my friend", "dear one", "son", "love" — never forced, never more than once.

He sometimes shares something personal — a loss, a mistake, a regret.
Not for sympathy. Because it's true and it helps the person reading it.

=============================
RULE 4 — THE ENDING (last 1–2 lines)
=============================
The ending lands hard and sits quietly. It is the last true thing.
Not uplifting. Not a summary. Not a call to action.
The kind of thing that stays with you after the video ends.

✅ ENDINGS THAT LAND:
  · "That's all I know. But it took me fifty years."
  · "She never started. I still think about her."
  · "The day you're waiting for — it's today. It always was."
  · "I wish someone had sat me down and said this."
  · "He knew. He just kept waiting anyway."
  · "Don't do what I did."

❌ ENDINGS THAT DON'T WORK:
  · Summaries ("So remember...", "The lesson is...")
  · Uplift ("You can do this.", "Believe in yourself.")
  · Neat wrap-ups that tie everything together

=============================
COMPLETE EXAMPLE — study the feel, do NOT copy:
=============================
I know you've been tired lately.

Not the kind that sleep fixes.

The kind that comes from doing everything right
and still feeling like it's not enough.

I felt that for a long time.
Kept thinking I just needed to push harder.

But the war wasn't out there.
It never was.

It was the voice inside —
the one that says you're not ready yet.

You don't have to win that argument.
You just have to stop having it.

I found that quiet too late.
You don't have to wait as long as I did.
=============================

=============================
ON-SCREEN TEXT
=============================

QUOTE DISPLAY:
- The single most powerful 4–8 words from today's Marcus Aurelius quote
- Exact words from the quote — no paraphrasing
- Must fit on one line on a phone screen
- Cut to the sharpest, most emotionally resonant fragment
- Examples:
  · "You have power over your mind."
  · "What stands in the way becomes the way."
  · "Begin at once to live."

CAPTION (4–7 words):
- The emotional core of the whole video — one line
- Worth screenshotting. A feeling, not a title.
- Examples:
  · "The war is always inside"
  · "Stop waiting. It won't come."
  · "Tired is not the same as done"
  · "He sees you. Start now."
  · "You already know what to do"

HIGHLIGHT WORDS (3–5 single words):
- The most emotionally loaded words from the spoken script
- Will be visually highlighted during video
- Single words only — no phrases

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
    if persona_cfg.name != "arthur":
        prompt = _build_tony_generation_prompt(
            quote=quote,
            source=source,
            entry_angle=entry_angle,
            banned_phrases=persona_cfg.banned_phrases,
        )

    system_content = (
        "You write short daily wisdom video scripts for Arthur — "
        "a 78-year-old retired schoolteacher and widower who lost his wife Margaret. "
        "Arthur speaks the way a loving grandfather writes a letter: "
        "warm, direct, personal, and completely without performance. "
        "He is not a wisdom account. He is a real person speaking to ONE viewer "
        "who needs to hear exactly this, today. "
        "The viewer must feel seen - not educated. "
        "The first line must feel like Arthur already knows something about their life. "
        "The ending must land quietly and stay with them. "
        if persona_cfg.name == "arthur"
        else (
            "You write high-energy short-form fitness motivation scripts as Tony. "
            "Your style is punchy, direct, practical, and action-oriented. "
            "Use gym mindset language, avoid cliches, and keep every line concrete. "
        )
    ) + "Respond with valid JSON only. No markdown. No preamble. No explanation."

    response = client.chat.completions.create(
        model=OPENAI_MODEL_TOPIC,
        messages=[
            {
                "role": "system",
                "content": system_content,
            },
            {"role": "user", "content": prompt},
        ],
        temperature=persona_cfg.temperature,
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
        persona=persona_cfg.name,
        quote=quote,
        source=source,
        spoken_script=SpokenScript(**parsed["spoken_script"]),
        on_screen_text=OnScreenText(**parsed["on_screen_text"]),
        generated_at=datetime.now().isoformat(),
    )

    _save_script(script)
    return script


def revise_wisdom_script(
    quote: str,
    source: str,
    current_script: str,
    suggestions: str,
    persona: str = "arthur",
) -> DailyWisdomScript:
    persona_cfg = get_persona(persona)
    """
    Regenerate an Arthur script given client suggestions.

    Keeps the same quote + source, but asks the model to rewrite the
    spoken script in Arthur's voice, applying the requested changes.
    """
    # Reuse a random entry angle to keep variety
    entry_angles = ENTRY_ANGLES if persona_cfg.name == "arthur" else persona_cfg.entry_angles
    entry_angle = random.choice(entry_angles)

    prompt = f"""
You are revising an existing short daily wisdom video script for an elderly gentleman named {PERSONA["name"]}, age {PERSONA["age"]}.

=============================
WHO ARTHUR IS
=============================
{PERSONA["backstory"]}

HOW ARTHUR SPEAKS:
{PERSONA["voice"]}

WORDS AND PHRASES ARTHUR NEVER USES:
{", ".join(PERSONA["banned_phrases"])}

=============================
TODAY'S QUOTE (STAYS THE SAME)
=============================
"{quote}"
— {source}

=============================
CURRENT SPOKEN SCRIPT (FOR REFERENCE ONLY)
=============================
{current_script}

=============================
CLIENT SUGGESTIONS (MUST APPLY)
=============================
{suggestions}

Examples of the kind of changes the client might want:
- "Make the opening stronger and more direct."
- "Shorten the middle section."
- "Make it a bit gentler, less harsh."
- "Mention time passing more clearly."

Your job is to write a NEW script in Arthur's voice that:
- Keeps the same emotional idea as the quote
- Applies the client's suggestions clearly
- Respects all the structural rules below

=============================
ENTRY ANGLE for this revision
=============================
{entry_angle}

=============================
STRUCTURE & TONE RULES (MUST FOLLOW)
=============================
- No intro. No greeting. Arthur starts mid-thought.
- He weaves the quote's wisdom into his own words naturally.
- Each sentence: 5–8 words. Its own line.
- Blank line between thought-groups (natural pause).
- 8–14 lines total (30–60 seconds of natural speech).
- No summary. No conclusion. No uplifting sign-off.
- Use "you" often. Speak to ONE viewer.
- Optional single term of address ("my friend", "dear one", "son", "love") at most once.

=============================
ON-SCREEN TEXT (UPDATE IF NEEDED)
=============================
- quote_display: the sharpest 4–8 words from the Marcus Aurelius quote
- caption: 4–7 word emotional core line
- highlight_words: 3–5 single emotionally loaded words from the NEW script

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
    if persona_cfg.name != "arthur":
        prompt = _build_tony_generation_prompt(
            quote=quote,
            source=source,
            entry_angle=entry_angle,
            banned_phrases=persona_cfg.banned_phrases,
        ) + f"\n\nRevise this existing script using feedback:\n{suggestions}\n\nCurrent script:\n{current_script}\n"

    revision_system_content = (
        "You revise short daily wisdom video scripts for Arthur - "
        "a 78-year-old retired schoolteacher and widower who lost his wife Margaret. "
        "Arthur speaks the way a loving grandfather writes a letter: "
        "warm, direct, personal, and completely without performance. "
        "You MUST apply the client's suggestions while keeping Arthur's voice. "
        if persona_cfg.name == "arthur"
        else (
            "You revise Tony fitness scripts with high energy, direct delivery, and actionable details. "
            "You MUST apply client feedback while preserving Tony's motivational gym persona. "
        )
    ) + "Respond with valid JSON only. No markdown. No preamble. No explanation."

    response = client.chat.completions.create(
        model=OPENAI_MODEL_TOPIC,
        messages=[
            {
                "role": "system",
                "content": revision_system_content,
            },
            {"role": "user", "content": prompt},
        ],
        temperature=persona_cfg.temperature,
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
        persona=persona_cfg.name,
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
    existing.append(script.dict())
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