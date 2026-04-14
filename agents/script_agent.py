import hashlib
import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
from config.system_config import (
    GEMINI_API_KEY,
    GEMINI_MODEL_TOPIC,
    GEMINI_OPENAI_BASE_URL,
)
from config.personas import get_persona
from .topic_agent import fetch_winning_wisdom_quote

load_dotenv()

client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_OPENAI_BASE_URL)

SCRIPTS_FILE = Path("data/generated_scripts.json")


def script_fingerprint(full_script: str) -> str:
    """Stable hash for binding voice/video steps to a script_agent-generated script."""
    normalized = (full_script or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def resolve_script_text_by_fingerprint(persona: str, fingerprint: str) -> Optional[str]:
    """
    Return spoken script text from ledger (data/generated_scripts.json) when fingerprint matches.
    If multiple entries match, return the one with the latest generated_at.
    """
    want = (persona or "arthur").strip().lower()
    fp = (fingerprint or "").strip().lower()
    if not fp:
        return None
    best_text: Optional[str] = None
    best_ts = ""
    for rec in _load_scripts():
        if str(rec.get("persona", "arthur")).strip().lower() != want:
            continue
        full = (rec.get("spoken_script") or {}).get("full_script") or ""
        if script_fingerprint(full).lower() != fp:
            continue
        ts = str(rec.get("generated_at") or "")
        if ts >= best_ts:
            best_ts = ts
            best_text = full.strip()
    return best_text


def persist_spoken_script_snapshot(
    persona: str,
    full_script: str,
    *,
    quote: str = "",
    source: str = "",
) -> None:
    """Append a ledger row so media steps can resolve spoken text by fingerprint."""
    persona_cfg = get_persona(persona)
    script = DailyWisdomScript(
        persona=persona_cfg.name,
        quote=quote or "(snapshot)",
        source=source or "",
        spoken_script=SpokenScript(full_script=(full_script or "").strip()),
        on_screen_text=OnScreenText(quote_display="", caption="", highlight_words=[]),
        generated_at=datetime.now().isoformat(),
    )
    _save_script(script)


# ─────────────────────────────────────────────────────────────────────
# PERSONA PROFILE — "Arthur"
# ─────────────────────────────────────────────────────────────────────
PERSONA = {
    "name": "Arthur",
    "age": "56",
    "backstory": (
        "Arthur is in his fifties — silver at the temples, reading glasses, dark sweaters over collared shirts. "
        "He lives in a quiet study: leather chair, bookshelves, amber light. Think polished gravitas, not exhaustion. "
        "He has made serious mistakes and learned from them. He is not perfect, not a guru. "
        "He contextualizes proven voices — Marcus Aurelius, Frankl, Buffett, Munger, Naval — but the value is always "
        "what he sees in their idea that most people miss. "
        "He writes and speaks as a wise father figure for viewers, often young men, who want grounded guidance "
        "without alpha-male or hustle poison. He is never dominant, never preaching down."
    ),
    "voice": (
        "Deep, warm baritone. Measured pace. Strategic pauses — room to breathe between thoughts. "
        "Zero aggression. Zero preachiness. He shares the way someone sits beside you, not across a desk. "
        "He speaks directly to one viewer. He uses 'you' with gentleness. "
        "He may use 'son,' 'my friend,' or 'listen carefully' once in a script when it feels human — not as a gimmick. "
        "Self-deprecation is allowed in small doses when it builds trust. "
        "Short lines — often 5–8 words — with white space between groups. "
        "He does not summarize in tidy lessons. He stops when the true thing has been said."
    ),
    "banned_phrases": [
        "level up", "hustle", "grind", "game changer", "crush it",
        "unleash", "transform", "unlock your potential", "hack",
        "optimize", "mindset shift", "you got this", "let's go",
        "drop a comment", "smash that like button",
        "we often", "it is important", "in today's world",
        "in conclusion", "as we can see", "it's a reminder that",
        "this teaches us", "the lesson here",
        "have you ever", "you ever", "we all", "so many people",
        "most of us", "life is", "it's easy to", "think about",
        "there are people", "sometimes we",
        "today's quote", "as the quote says",
        "alpha male", "high-value man", "high value man", "red pill",
        "sigma male", "sigma", "top g", "grindset",
    ],
}

# ─────────────────────────────────────────────────────────────────────
# ENTRY ANGLES — hook before quote; emotional gut-punch first.
# ─────────────────────────────────────────────────────────────────────
ENTRY_ANGLES = [
    "CRITICAL: First lines are a scroll-stopping emotional hook. Do NOT open with the supplied quote text, "
    "and do NOT open with 'X once said / today's wisdom is.' The quote lands mid-script after the viewer is invested.",
    "Open with father-shaped tension: what no one told them at eighteen — and what it cost. Plain, non-judgmental.",
    "Open like the start of a conversation they needed: 'Stop chasing respect — it's not what you think it is.' energy.",
    "Beside the viewer, not above: name the weight they're carrying — fatigue, shame, delay — as fact Arthur already sees.",
    "Share a mistake or fear Arthur actually lived — one arc, vulnerable, no hero ending required.",
    "Interpret, don't recite: weave the anchor quote's idea after the hook. At most one short nod to Marcus, Frankl, "
    "Buffett, Munger, or Naval if it fits — what most people miss about that idea.",
    "Study at dusk: stillness, leather-and-bookshelf presence — then turn to the viewer with one honest line.",
    "Time passing, choices unmade: gentle observation, not a scolding — 'You meant to start that. Time kept walking.'",
    "Respect, status, proving: Arthur quietly names what the chase steals — no dominance language, no guru pose.",
    "Close with something that sits — sometimes an abrupt trailer line on short-form that leaves them leaning in.",
]

ARTHUR_CHARACTER_BIBLE = {
    "verbal_patterns": [
        "open with one intimate correction from lived experience",
        "use one restrained direct-address cue, then move on",
        "include one quiet reassurance line with imperfect honesty",
        "acknowledge one delayed lesson without hero framing",
    ],
    "visual_rituals": [
        "Warm amber study energy; grounded and steady, never theatrical.",
        "A quiet library cadence: patient pauses, then one direct line to the viewer.",
        "Leather chair and bookshelf stillness before the emotional turn.",
    ],
    "callbacks": [
        "the room you keep proving yourself to",
        "the kind of tired sleep can't fix",
        "time kept walking while you waited",
    ],
}

ARTHUR_IDENTITY_ROLE_POOL = [
    "founder who rebuilt after early failure",
    "operator who learned discipline the hard way",
    "mentor who made expensive mistakes first",
    "builder who values consistency over hype",
]

ARTHUR_MEMORY_ANCHOR_POOL = [
    "at age 19 in his first real role",
    "during an early season of financial pressure",
    "in a week where one decision carried consequences",
    "in a period where delay quietly became regret",
]

ARTHUR_CONSEQUENCE_POOL = [
    "lost trust he had not earned yet",
    "watched an opportunity close in silence",
    "paid the cost of waiting too long",
    "learned that comfort can look like progress",
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
You are Tony, an evidence-based fitness coach creating a 30–60 second short-form script (TikTok / Reels / Shorts).

WHO TONY IS:
- Mid-thirties energy: athletic, clean-cut, patient teacher — not a bodybuilder caricature.
- He cites research but makes it human; admits when evidence is weak or mixed.
- Corrects myths without condescension. Dry humor OK; never sarcastic, never hype-bro culture.

VOICE:
- Calm, measured, warm; lower-register podcast host — not a drill sergeant.
- First person when sharing how he reads studies or what he'd do this week.

CONTENT FOCUS:
- Myth vs research, form and safety, recovery, what trials/meta-analyses tend to show (without inventing fake citations).
- The quote below is the thematic anchor — weave it naturally; you do not need a fake PubMed title in every line.

HARD RULES:
- NEVER diagnose disease or injury. Add a brief line that this is general education and to consult a qualified clinician for personal medical advice.
- NEVER invent a specific study title, journal name, author list, or P-value. You may speak in general terms ("randomized trials tend to find…", "reviews often conclude…") or lean on the attributed source if it's already credible text.
- NO before/after transformation promises. No supplement hype or industry-funded certainty unless the quote/source already names it.
- BANNED PHRASES (never use, case-insensitive): {", ".join(banned_phrases)}

ENTRY ANGLE:
{entry_angle}

QUOTE / CORE IDEA:
"{quote}"
— {source}

STRUCTURE:
- 8–14 short lines; strong hook in line 1 (myth, wrong cue, or tension between belief and evidence).
- Include ONE clear "if I were you this week" closer — one practical behavior, not a sermon.
- Optional: end with a soft engagement ask in spoken script only if it fits organically (e.g. which myth annoys them) — never demand likes/follows.

Also produce JSON fields:
- quote_display: 4–8 words — sharpest hook from the quote or your rephrase (on-screen).
- caption: 4–7 words — credible, specific, not clickbait diagnosis.
- highlight_words: 3–5 single words from the script for on-screen emphasis.

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
    theme: Optional[str] = None,
) -> DailyWisdomScript:
    """
    Generate a spoken script + on-screen text for the chosen persona.

    Arthur: anchor quote is thematic spine; hook comes first, quote mid-script.
    Fetches quote when no override; uses Gemini (OpenAI-compatible API) with persona-specific prompts.

    Args:
        quote_override: optional quote text
        source_override: optional attribution
        persona: arthur | tony

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

    # 2. Pick entry angle + dynamic slots (non-static phrasing)
    entry_angles = ENTRY_ANGLES if persona_cfg.name == "arthur" else persona_cfg.entry_angles
    entry_angle = random.choice(entry_angles)
    verbal_pattern = random.choice(ARTHUR_CHARACTER_BIBLE["verbal_patterns"])
    visual_ritual = random.choice(ARTHUR_CHARACTER_BIBLE["visual_rituals"])
    callback_token = random.choice(ARTHUR_CHARACTER_BIBLE["callbacks"])
    identity_role = random.choice(ARTHUR_IDENTITY_ROLE_POOL)
    memory_anchor = random.choice(ARTHUR_MEMORY_ANCHOR_POOL)
    consequence_anchor = random.choice(ARTHUR_CONSEQUENCE_POOL)
    theme_anchor = (theme or quote_data.get("topic") or quote or "").strip()

    arthur_count = sum(
        1
        for s in _load_scripts()
        if str(s.get("persona", "arthur")).strip().lower() == "arthur"
    )
    script_number = arthur_count + 1
    must_vulnerable = script_number % 3 == 0
    vulnerability_instruction = (
        "MANDATORY FOR THIS SCRIPT: full vulnerability arc. Arthur must show where he was wrong, scared, "
        "or failed, then what changed (without heroic chest-thumping)."
        if must_vulnerable
        else "Vulnerability is optional in this script; keep some human imperfection even when not using a full arc."
    )

    # 3. Build prompt
    prompt = f"""
You are writing a short video script (30–60 sec, Reels / Shorts / TikTok) for {PERSONA["name"]}, a man age {PERSONA["age"]}.

=============================
WHO ARTHUR IS
=============================
{PERSONA["backstory"]}

HOW ARTHUR SPEAKS:
{PERSONA["voice"]}

WORDS AND PHRASES ARTHUR NEVER USES:
{", ".join(PERSONA["banned_phrases"])}

=============================
ANCHOR TEXT (thematic spine — NOT the opening line)
=============================
"{quote}"
— {source}

=============================
YOUR TASK
=============================
Write in Arthur's voice. Primary audience: young men and anyone craving a grounded father figure — never alpha-male or hustle poison.

ENTRY ANGLE for this script:
{entry_angle}

=============================
CLIENT STRATEGY (MUST APPLY)
=============================
- Authority method: the ANCHOR TEXT author is the star of the mid-script turn; other figures at most a fleeting gloss, never a replacement aphorism from a different book.
- Keep references sparse: 1–2 mentions maximum; the anchor counts as one.
- Hook sequencing: first ~1.5 seconds is a gut-punch. The quote/authority line lands later (~20–30 seconds in), never as opener.
- Parasocial architecture: include exactly one recurring Arthur cue in a natural way:
  · verbal pattern seed: "{verbal_pattern}"
  · visual ritual seed: "{visual_ritual}"
  · callback seed: "{callback_token}"
- Vulnerability cadence target:
  · script index for Arthur in local history: #{script_number}
  · {vulnerability_instruction}
- Tone safety: share, do not lecture. Avoid patronizing language or dominance vibes.
- Continuity: do not contradict Arthur's prior worldview (grounded, warm, anti-hustle, anti-red-pill).

=============================
THEME ANCHOR (MUST PRESERVE)
=============================
Theme for this script: "{theme_anchor}"
- The script must clearly stay on this theme from first hook to final landing.
- Do not drift into generic motivation unrelated to this theme.

=============================
DYNAMIC SLOT ENGINE (NO STATIC LINES)
=============================
- Do NOT reuse fixed/canned hook lines verbatim.
- Use this run's dynamic slots as semantic guidance, not literal copy:
  · identity slot: {identity_role}
  · memory-anchor slot: {memory_anchor}
  · consequence slot: {consequence_anchor}
  · verbal-cue style: {verbal_pattern}
- Build fresh wording each time while keeping Arthur voice.
- Include at least one specific memory anchor (age/time/place/person/consequence) so the story feels lived, not generic.
- Keep identity-driven framing: Arthur sounds like someone who paid a real price, not a quote narrator.

=============================
THE MOST IMPORTANT THING — READ THIS FIRST
=============================
Arthur is not a quote account.
He is a person — warm, distinguished, flawed, real — sitting beside ONE viewer.

People stop scrolling when it feels like the wise father figure they wish they'd had:
speaking TO them, not down at them — no performance, no sermon.

Your goal:
  "He is talking about me. He sees me. He knows."

NOT: opening with the anchor text or "here's today's quote."
NOT: red-pill, sigma, or dominance energy.
YES: hook first, quote or paraphrase lands after the viewer is invested (roughly middle third of the script).

=============================
RULE 1 — THE HOOK (first 1–3 lines) — CRITICAL
=============================
The hook is NEVER the anchor quote. NEVER open with "Marcus said…", "Buffett once…", or any line of the supplied quote text.

The hook is an emotional gut-punch or intimate father-shaped truth.

✅ HOOK ENERGY (examples — do not copy verbatim every time):
  · "No one told you this when you were eighteen."
  · "The conversation your father should have had with you — but didn't."
  · "Stop chasing respect. It's not what you think it is."
  · "I know you've been tired — not the kind sleep fixes."
  · "You meant to start that. The calendar turned anyway."

❌ HOOKS THAT FAIL:
  · Leading with the quote or attribution
  · Questions: "Have you ever…", "Do you…"
  · Generic wisdom: "Life is…", "We all…"
  · Motivational poster talk

=============================
RULE 2 — SCRIPT STRUCTURE (quote lands mid-script)
=============================
- No intro, no greeting. Arthur starts mid-thought on the emotional hook.
- Build trust for several beats; then the MID-SCRIPT TURN must be the ANCHOR TEXT above: same author/work, exact words or tight paraphrase of THAT idea — not a different book or celebrity quote.
- FORBIDDEN unless that person is named in the supplied source line: James Clear, Atomic Habits, "fall to the level of your systems," or any other catchphrase that replaces the anchor author's idea.
- Optional: one short clause naming ONLY the anchor author (from the source line) to introduce the anchor idea — never a second named author with a competing full quote.
- Each sentence: often 5–8 words, own line; blank line between thought-groups (pause).
- 8–14 lines total. No TED-summary closer unless it feels like a quiet trailer ending.

=============================
RULE 3 — WARMTH AND ADDRESS
=============================
Use "you" with care. Terms like "son" or "listen carefully" only once per script if they land naturally — never theatrical.

=============================
RULE 4 — ENDING
=============================
Last lines sit quietly — true, not tidy. May feel like a trailer (viewer leans in) as long as it stays dignified.

=============================
RHYTHM (structure only — write NEW lines; do not reuse wording from any example in this prompt)
=============================
- 2–4 lines: hook only (topic emotion), zero quote, zero author names.
- 3–5 lines: stakes / Arthur's beside-you honesty; vary metaphors — do NOT default to "finish line," "wrong rooms," or "chasing respect" every time unless the topic truly demands it.
- 3–5 lines: ANCHOR TURN — lead with the supplied author if natural, then their idea (from ANCHOR TEXT); this block is the spine of the script.
- 1–3 lines: quiet landing; you may reuse ONE verbal seed from CLIENT STRATEGY if it fits, not whole phrases from HOOK ENERGY examples above.
=============================

=============================
ON-SCREEN TEXT
=============================

QUOTE DISPLAY:
- 4–8 words: sharpest fragment from the ANCHOR TEXT above (exact words from the quote when possible)
- One phone line

CAPTION (4–7 words):
- Emotional core — screenshot-worthy, elegant and spare

HIGHLIGHT WORDS (3–5 single words):
- From the spoken script; visually loaded

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
        "You write short video scripts for Arthur — a wise father figure in his fifties: "
        "deep warm baritone energy on the page, measured pauses, zero preachiness. "
        "Hook first — never open with the anchor quote. Quote lands mid-script. "
        "He interprets wisdom; he is not a quote bot, not alpha-male content. "
        "One viewer must feel seen beside him, not lectured. "
        if persona_cfg.name == "arthur"
        else (
            "You write short-form fitness scripts as Tony — an evidence-based coach, calm and precise like a podcast host. "
            "He debunks myths with humility, never invents fake studies, never diagnoses, and avoids bro-culture hype. "
        )
    ) + "Respond with valid JSON only. No markdown. No preamble. No explanation."

    response = client.chat.completions.create(
        model=GEMINI_MODEL_TOPIC,
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
    theme: Optional[str] = None,
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
    verbal_pattern = random.choice(ARTHUR_CHARACTER_BIBLE["verbal_patterns"])
    visual_ritual = random.choice(ARTHUR_CHARACTER_BIBLE["visual_rituals"])
    callback_token = random.choice(ARTHUR_CHARACTER_BIBLE["callbacks"])
    identity_role = random.choice(ARTHUR_IDENTITY_ROLE_POOL)
    memory_anchor = random.choice(ARTHUR_MEMORY_ANCHOR_POOL)
    consequence_anchor = random.choice(ARTHUR_CONSEQUENCE_POOL)
    theme_anchor = (theme or quote).strip()

    prompt = f"""
You are revising a short video script for {PERSONA["name"]}, age {PERSONA["age"]}.

=============================
WHO ARTHUR IS
=============================
{PERSONA["backstory"]}

HOW ARTHUR SPEAKS:
{PERSONA["voice"]}

WORDS AND PHRASES ARTHUR NEVER USES:
{", ".join(PERSONA["banned_phrases"])}

=============================
ANCHOR TEXT (STAYS THE SAME)
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

Your job is a NEW script in Arthur's voice that:
- Preserves the anchor text's emotional spine
- Applies the client's suggestions
- NEVER opens with the anchor quote or attribution; hook first, anchor in the middle third
- Stays father-figure warm, not guru or alpha-male

=============================
ENTRY ANGLE for this revision
=============================
{entry_angle}

=============================
CLIENT STRATEGY (MUST APPLY)
=============================
- Authority method: interpret proven figures instead of dropping quotes for clout.
- Keep references to 1–2 max.
- Hook first, quote later; never lead with attribution.
- Keep Arthur's recurring identity alive with one natural cue:
  · verbal seed: "{verbal_pattern}"
  · visual seed: "{visual_ritual}"
  · callback seed: "{callback_token}"
- If suggestions request vulnerability, commit to a real arc (wrong/scared/failed -> consequence -> quieter insight).
- Stay anti-red-pill and anti-patronizing; Arthur shares from beside the viewer.

=============================
THEME ANCHOR (MUST PRESERVE)
=============================
Theme for this revision: "{theme_anchor}"
- Keep the revised script tightly tied to this theme.

=============================
DYNAMIC SLOT ENGINE (NO STATIC LINES)
=============================
- Do NOT copy fixed Arthur stock lines verbatim.
- Regenerate fresh phrasing using these slot intents:
  · identity slot: {identity_role}
  · memory-anchor slot: {memory_anchor}
  · consequence slot: {consequence_anchor}
  · verbal-cue style: {verbal_pattern}
- Include at least one concrete memory anchor so revision feels personal and real.

=============================
STRUCTURE & TONE RULES (MUST FOLLOW)
=============================
- No intro. No greeting. Emotional hook in the first lines — not the quote.
- Mid-script turn = ANCHOR TEXT (same author/source); do not substitute James Clear, Atomic Habits, or "fall to the level of your systems" unless the source names them.
- 5–8 word lines, blank lines between thought groups; 8–14 lines total; vary imagery — do not recycle the same hook tropes from the current script unless suggestions ask for it.
- No tidy summary sign-off; ending sits quietly or trailer-sharp.
- Terms like "son" or "listen carefully" at most once if natural.

=============================
ON-SCREEN TEXT (UPDATE IF NEEDED)
=============================
- quote_display: sharpest 4–8 words from the anchor quote (exact words when possible)
- caption: 4–7 word emotional core line
- highlight_words: 3–5 single words from the NEW script

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
        "You revise Arthur's scripts: wise father figure, fifties, baritone warmth on the page — "
        "hook before quote, anchor mid-script, never alpha hustle tone. "
        "You MUST apply the client's suggestions while keeping that voice. "
        if persona_cfg.name == "arthur"
        else (
            "You revise Tony's scripts as an evidence-based fitness coach: calm, cited-minded, myth-busting without arrogance. "
            "You MUST apply client feedback while preserving that voice — no fake paper titles, no medical diagnosis. "
        )
    ) + "Respond with valid JSON only. No markdown. No preamble. No explanation."

    response = client.chat.completions.create(
        model=GEMINI_MODEL_TOPIC,
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