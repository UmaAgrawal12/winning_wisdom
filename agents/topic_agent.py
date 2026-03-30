import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from dotenv import load_dotenv
from pydantic import BaseModel
from winning_wisdom_ai.config.personas import get_persona

try:
    # When running from `winning_wisdom_ai/` as the working directory
    from llm_client import topic_llm
except ModuleNotFoundError:
    # When importing as a package (e.g., `python -m winning_wisdom_ai...`)
    from winning_wisdom_ai.llm_client import topic_llm

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

USED_QUOTES_FILE = Path("data/used_quotes.json")


class TopicsResult(BaseModel):
    topics: List[str]
    generated_at: str


def get_curated_topics(
    persona: str = "arthur",
    n: Optional[int] = 8,
    shuffle: bool = True,
) -> TopicsResult:
    """
    Persona-specific topics defined in code (no external search API).

    When ``n`` is None, returns the full curated list in canonical order
    (used by `/api/topics` for the UI). Otherwise returns up to ``n`` topics,
    optionally shuffled (used for random picks in `/api/topic`).
    """
    persona_cfg = get_persona(persona)
    base = (
        ARTHUR_FALLBACK_TOPICS
        if persona_cfg.name == "arthur"
        else TONY_FALLBACK_TOPICS
    )
    pool = list(base)
    if shuffle:
        random.shuffle(pool)
    if n is not None:
        pool = pool[: min(n, len(pool))]
    return TopicsResult(topics=pool, generated_at=datetime.now().isoformat())


def generate_topics(
    theme: str = "Winning Wisdom: discipline, meaning, resilience, self-mastery",
    n: Optional[int] = 8,
    audience: str = "general_self_improver",
    persona: str = "arthur",
) -> TopicsResult:
    """
    Generate short-form video topics aligned to the Winning Wisdom theme.

    Returns a list of short, actionable topics (not quotes).
    """
    persona_cfg = get_persona(persona)
    llm = topic_llm()

    target_n = n or 8
    prompt = (
        "You are the editorial lead for 'Winning Wisdom' short videos.\n"
        f"Generate topic ideas that fit persona '{persona_cfg.display_name}': {persona_cfg.content_focus}\n"
        "Constraints:\n"
        f"- Audience: {audience}\n"
        f"- Theme: {theme}\n"
        f"- Keywords to prioritize: {', '.join(persona_cfg.topic_keywords)}\n"
        "- Each topic: 4–10 words, plain English, no quotes, no emojis.\n"
        "- Avoid generic filler ('be better', 'success mindset'). Make them specific and human.\n"
        f"- Return exactly {target_n} topics.\n\n"
        "Return ONLY valid JSON with this shape:\n"
        '{ "topics": ["...","..."] }\n'
    )

    try:
        resp = llm.invoke(prompt)
        raw = (resp.content or "").strip()
        data = json.loads(raw)
        topics = [t.strip() for t in data.get("topics", []) if isinstance(t, str) and t.strip()]
        if len(topics) >= 2:
            if n:
                topics = topics[:n]
            return TopicsResult(topics=topics, generated_at=datetime.now().isoformat())
    except Exception:
        # Fall through to fallback topics
        pass

    pool = list(
        ARTHUR_FALLBACK_TOPICS if persona_cfg.name == "arthur" else TONY_FALLBACK_TOPICS
    )
    random.shuffle(pool)
    topics = pool[: (n or 8)]
    return TopicsResult(topics=topics, generated_at=datetime.now().isoformat())


def fetch_winning_wisdom_quote_for_topic(
    topic: str,
    avoid_used: bool = True,
    persona: str = "arthur",
) -> dict:
    """
    Return a quote for ``topic`` using the hardcoded topic→quotes bank,
    or the persona quote pool when the topic is unknown or free-typed.
    """
    persona_cfg = get_persona(persona)
    topic = (topic or "").strip()
    if not topic:
        out = fetch_winning_wisdom_quote(avoid_used=avoid_used, persona=persona_cfg.name)
        return {**out, "topic": ""}

    used_quotes = _load_used_quotes() if avoid_used else set()
    bank = TOPIC_QUOTES_BY_PERSONA.get(persona_cfg.name, {})
    candidates = bank.get(topic)
    if candidates is None:
        t_low = topic.lower()
        for key, quotes in bank.items():
            if key.lower() == t_low:
                topic, candidates = key, quotes
                break

    if candidates:
        pool = [
            c
            for c in candidates
            if (not avoid_used) or c["quote"].strip().lower() not in used_quotes
        ]
        if not pool:
            pool = list(candidates)
        choice = random.choice(pool)
        quote_text = choice["quote"].strip()
        if avoid_used:
            _save_used_quote(quote_text)
        return {
            "topic": topic,
            "quote": quote_text,
            "source": choice["source"],
            "fetched_at": datetime.now().isoformat(),
        }

    base = fetch_winning_wisdom_quote(avoid_used=avoid_used, persona=persona_cfg.name)
    base["topic"] = topic
    return base


def _load_used_quotes() -> set:
    if not USED_QUOTES_FILE.exists():
        return set()
    try:
        with open(USED_QUOTES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data.get("used", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def _save_used_quote(quote_text: str) -> None:
    USED_QUOTES_FILE.parent.mkdir(parents=True, exist_ok=True)
    used = _load_used_quotes()
    used.add(quote_text.strip().lower())
    with open(USED_QUOTES_FILE, "w", encoding="utf-8") as f:
        json.dump({"used": list(used)}, f, indent=2)


# ─────────────────────────────────────────────────────────────────────
# HARD-CODED FALLBACK QUOTES — WINNING WISDOM (MULTI-AUTHOR)
# ─────────────────────────────────────────────────────────────────────
WINNING_WISDOM_QUOTES = [
    # Marcus (kept in the mix)
    {"quote": "You have power over your mind, not outside events. Realize this, and you will find strength.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The impediment to action advances action. What stands in the way becomes the way.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Waste no more time arguing about what a good man should be. Be one.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Begin at once to live, and count each separate day as a separate life.", "source": "Marcus Aurelius — Meditations"},

    # Other Stoics
    {"quote": "We suffer more often in imagination than in reality.", "source": "Seneca — Letters from a Stoic"},
    {"quote": "Luck is what happens when preparation meets opportunity.", "source": "Seneca"},
    {"quote": "If a man knows not to which port he sails, no wind is favorable.", "source": "Seneca"},
    {"quote": "First say to yourself what you would be; and then do what you have to do.", "source": "Epictetus — Discourses"},
    {"quote": "No man is free who is not master of himself.", "source": "Epictetus"},

    # Modern "winning wisdom" voices
    {"quote": "Between stimulus and response there is a space. In that space is our power to choose our response. In our response lies our growth and our freedom.", "source": "Viktor Frankl — Man's Search for Meaning"},
    {"quote": "You will never always be motivated, so you must learn to be disciplined.", "source": "Unknown"},
    {"quote": "Success is nothing more than a few simple disciplines, practiced every day.", "source": "Jim Rohn"},
    {"quote": "You do not rise to the level of your goals. You fall to the level of your systems.", "source": "James Clear — Atomic Habits"},
    {"quote": "People do not decide their futures, they decide their habits and their habits decide their futures.", "source": "F. M. Alexander"},
    {"quote": "Suffer the pain of discipline or suffer the pain of regret.", "source": "Unknown"},
]

TONY_FITNESS_QUOTES = [
    {"quote": "The first principle is that you must not fool yourself — and you are the easiest person to fool.", "source": "Richard Feynman"},
    {"quote": "In God we trust; all others must bring data.", "source": "W. Edwards Deming"},
    {"quote": "The plural of anecdote is not data.", "source": "Common analytics aphorism"},
    {"quote": "Strong opinions, loosely held — update when better evidence arrives.", "source": "Paul Saffo (paraphrased)"},
    {"quote": "The iron never lies to you.", "source": "Henry Rollins"},
    {"quote": "Your body can stand almost anything. It is your mind you have to convince.", "source": "Unknown"},
    {"quote": "The only bad workout is the one that did not happen.", "source": "Unknown"},
    {"quote": "Strength comes from overcoming what you thought you could not do.", "source": "Rikki Rogers"},
    {"quote": "Take care of your body. It is the only place you have to live.", "source": "Jim Rohn"},
    {"quote": "Discipline is choosing between what you want now and what you want most.", "source": "Unknown"},
    {"quote": "You do not get the body you wish for. You get the body you work for.", "source": "Unknown"},
    {"quote": "Progress is built one rep at a time.", "source": "Unknown"},
    {"quote": "Consistency beats intensity when intensity cannot last.", "source": "Unknown"},
    {"quote": "The work you avoid is usually the work you need most.", "source": "Unknown"},
    {"quote": "Motivation gets you started. Habit keeps you going.", "source": "Jim Ryun"},
    {"quote": "Champions keep going when they have nothing left in the tank.", "source": "Unknown"},
    {"quote": "Do not limit your challenges. Challenge your limits.", "source": "Jerry Dunn"},
    {"quote": "A one hour workout is 4 percent of your day.", "source": "Unknown"},
    {"quote": "Results happen over time, not overnight.", "source": "Unknown"},
    {"quote": "When you feel like quitting, remember why you started.", "source": "Unknown"},
    {"quote": "Train for life, not just for looks.", "source": "Unknown"},
    {"quote": "Recovery is where adaptation happens.", "source": "Unknown"},
    {"quote": "Sleep is part of the program, not a break from it.", "source": "Unknown"},
    {"quote": "The scale does not measure discipline, only gravity.", "source": "Unknown"},
    {"quote": "Technique before load. Always.", "source": "Unknown"},
    {"quote": "You earn confidence by keeping promises to yourself.", "source": "Unknown"},
    {"quote": "Small daily wins become visible transformations.", "source": "Unknown"},
    {"quote": "Form is your long-term progress insurance.", "source": "Unknown"},
    {"quote": "What you repeat, you become.", "source": "Unknown"},
    {"quote": "You are one workout away from a better mood.", "source": "Unknown"},
    {"quote": "The mirror reflects effort, not excuses.", "source": "Unknown"},
    {"quote": "Train with intent, fuel with purpose, recover with discipline.", "source": "Unknown"},
    {"quote": "The strongest muscle is the mind that shows up.", "source": "Unknown"},
    {"quote": "Focus on performance and the physique follows.", "source": "Unknown"},
    {"quote": "Build a body that carries your future.", "source": "Unknown"},
    {"quote": "You do not have to be extreme, just consistent.", "source": "Unknown"},
]

ARTHUR_FALLBACK_TOPICS = [
    "What no one told you at eighteen — and what it cost",
    "The conversation a father should have had — but didn't",
    "Stop chasing respect: what it's actually made of",
    "The hardest part isn't failure — it's the silence after",
    "When you learned to perform strength instead of feeling it",
    "The gap between who you are and who you perform for",
    "What Buffett-style patience has to do with your anxiety",
    "Frankl on meaning when the plan breaks mid-life",
    "Why you keep waiting for permission to live",
    "The respect you want versus the quiet you need",
    "One thing Marcus gets right about the voice in your head",
    "Letters to my younger self: what I'd whisper first",
    "When ambition became a way to avoid grief",
    "The myth of arriving — and what to do Monday anyway",
    "Naval on leverage — what young men misread",
    "Munger on inversion — one habit worth stealing",
]

TONY_FALLBACK_TOPICS = [
    "What studies actually say about stretching before lifting",
    "Squats and knee pain: myth versus systematic reviews",
    "Protein timing: what trials changed our minds",
    "When no pain no gain collides with sports science",
    "Ice after injury: what newer research suggests",
    "Spot reduction myths versus how fat loss really works",
    "Static versus dynamic warm-ups: what reviews conclude",
    "Training to every set to failure: evidence on the tradeoffs",
    "Core stability myths that refuse to die online",
    "Cardio and strength gains: what longitudinal studies see",
    "Detox trends versus what physiology trials support",
    "Progressive overload versus muscle confusion in the data",
    "Electrolytes and cramping: what we know and do not",
    "Sleep debt and gym performance: dose-response patterns",
    "Supplement hype versus independent trial design",
    "Comment bait: the fitness myth that annoys you most",
]


def _pair_quotes_for_topics(
    topics: list[str],
    quote_pool: list[dict],
) -> dict[str, list[dict]]:
    """Map each curated topic to two quotes from the persona's hardcoded pool."""
    n = len(quote_pool)
    if n < 1:
        return {t: [] for t in topics}
    out: dict[str, list[dict]] = {}
    for i, topic in enumerate(topics):
        a = quote_pool[(i * 2) % n]
        b = quote_pool[(i * 2 + 1) % n]
        out[topic] = [
            {"quote": a["quote"], "source": a["source"]},
            {"quote": b["quote"], "source": b["source"]},
        ]
    return out


TOPIC_QUOTES_BY_PERSONA: dict[str, dict[str, list[dict]]] = {
    "arthur": _pair_quotes_for_topics(ARTHUR_FALLBACK_TOPICS, WINNING_WISDOM_QUOTES),
    "tony": _pair_quotes_for_topics(TONY_FALLBACK_TOPICS, TONY_FITNESS_QUOTES),
}


def fetch_winning_wisdom_quote(
    avoid_used: bool = True,
    persona: str = "arthur",
) -> dict:
    """
    Pick a quote from the persona's hardcoded bank (tracked in ``used_quotes`` when enabled).
    """
    persona_cfg = get_persona(persona)
    used_quotes = _load_used_quotes() if avoid_used else set()

    candidates = (
        WINNING_WISDOM_QUOTES.copy()
        if persona_cfg.name == "arthur"
        else TONY_FITNESS_QUOTES.copy()
    )
    random.shuffle(candidates)

    for candidate in candidates:
        quote_text = candidate["quote"]
        if avoid_used and quote_text.lower() in used_quotes:
            continue
        _save_used_quote(quote_text)
        return {
            "quote": quote_text,
            "source": candidate["source"],
            "fetched_at": datetime.now().isoformat(),
        }

    raise RuntimeError(
        "All Winning Wisdom quotes have been used. Run reset_used_quotes() to start fresh."
    )


def reset_used_quotes() -> None:
    """Clear the used quotes tracker."""
    if USED_QUOTES_FILE.exists():
        USED_QUOTES_FILE.write_text(json.dumps({"used": []}, indent=2))
        print("Used quotes tracker has been reset.")
    else:
        print("No used quotes file found — nothing to reset.")


def get_used_quotes_count() -> int:
    """Return how many quotes have been used so far."""
    return len(_load_used_quotes())