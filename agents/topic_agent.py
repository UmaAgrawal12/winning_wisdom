import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional, List
import re

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

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
SERPAPI_TIMEOUT_S = float(os.getenv("SERPAPI_TIMEOUT_S", "8"))

USED_QUOTES_FILE = Path("data/used_quotes.json")


class TopicsResult(BaseModel):
    topics: List[str]
    generated_at: str


def _serpapi_get(params: dict) -> dict:
    """
    Call SerpAPI with an explicit timeout so the API never hangs requests.
    """
    if not SERPAPI_API_KEY:
        raise ValueError("SERPAPI_API_KEY is REQUIRED. Add SERPAPI_API_KEY to your .env file.")

    import requests

    url = "https://serpapi.com/search.json"
    q = {**params, "api_key": SERPAPI_API_KEY}
    resp = requests.get(url, params=q, timeout=SERPAPI_TIMEOUT_S)
    resp.raise_for_status()
    return resp.json()


def _normalize_topic(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)

    # Drop obvious low-value listicle/quote page titles.
    reject_patterns = [
        r"^top\s*\d+",
        r"\b\d+\s*(best|greatest|most powerful)\b",
        r"\bquotes?\b",
        r"\bby\s+(marcus aurelius|seneca|epictetus)\b",
        r"\b(list|collection|compilation)\b",
        r"\bfor instagram\b",
        r"\bfor tiktok\b",
    ]
    lower = text.lower()
    for pattern in reject_patterns:
        if re.search(pattern, lower, flags=re.I):
            return ""

    # Remove obvious suffixes frequently found in generic SEO titles
    text = re.sub(
        r"\s*[-–|:]\s*(youtube|tiktok|reels|shorts|meaning|explained|guide|202[0-9])\s*$",
        "",
        text,
        flags=re.I,
    )
    text = text.strip(" .-–|:")
    # Keep short topics only
    words = text.split()
    if len(words) < 3 or len(words) > 10:
        return ""
    return text


def generate_topics_serpapi(
    theme: str = "Winning Wisdom: discipline, meaning, resilience, self-mastery",
    n: int = 8,
    location: str = "United States",
    persona: str = "arthur",
) -> TopicsResult:
    """
    SerpAPI-only topic discovery.

    Strategy: search for trending discussions/articles around the theme and
    derive short, actionable topics from result titles.
    """
    persona_cfg = get_persona(persona)
    query_seed = " OR ".join(persona_cfg.topic_queries)
    query = f"{theme} {query_seed} lessons mindset habits"
    results = _serpapi_get(
        {
            "engine": "google",
            "q": query,
            "location": location,
            "hl": "en",
            "num": 10,
        }
    )

    topics: list[str] = []
    seen = set()
    organic = list(results.get("organic_results", []) or [])
    random.shuffle(organic)  # avoid always returning the same first Google result
    for item in organic:
        title = (item.get("title") or "").strip()
        t = _normalize_topic(title)
        if not t:
            continue
        key = t.lower()
        if key in seen:
            continue
        seen.add(key)
        topics.append(t)
        if len(topics) >= n:
            break

    # Guarantee useful output even when Google returns noisy quote/list pages.
    if len(topics) < n:
        curated = ARTHUR_FALLBACK_TOPICS if persona_cfg.name == "arthur" else TONY_FALLBACK_TOPICS
        random.shuffle(curated)
        for item in curated:
            key = item.lower()
            if key in seen:
                continue
            topics.append(item)
            seen.add(key)
            if len(topics) >= n:
                break

    if len(topics) < 2:
        raise RuntimeError("SerpAPI returned insufficient persona-aligned topics.")

    return TopicsResult(topics=topics, generated_at=datetime.now().isoformat())


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

    fallback = ARTHUR_FALLBACK_TOPICS if persona_cfg.name == "arthur" else TONY_FALLBACK_TOPICS
    random.shuffle(fallback)
    topics = fallback[: (n or 8)]
    return TopicsResult(topics=topics, generated_at=datetime.now().isoformat())


def fetch_winning_wisdom_quote_for_topic(
    topic: str,
    avoid_used: bool = True,
    location: str = "United States",
    use_serpapi: bool = True,
    require_serpapi: bool = False,
    persona: str = "arthur",
) -> dict:
    """
    Fetch a quote aligned to a specific topic, still within the Winning Wisdom theme.

    Strategy:
    - Try SerpAPI searches that combine the topic with our author-specific configs
    - Fall back to the generic Winning Wisdom quote picker
    """
    persona_cfg = get_persona(persona)
    topic = (topic or "").strip()
    if not topic:
        return fetch_winning_wisdom_quote(
            avoid_used=avoid_used,
            location=location,
            use_serpapi=use_serpapi,
            require_serpapi=require_serpapi,
            persona=persona_cfg.name,
        )

    used_quotes = _load_used_quotes() if avoid_used else set()

    if use_serpapi:
        if not SERPAPI_API_KEY:
            if require_serpapi:
                raise ValueError(
                    "SERPAPI_API_KEY is REQUIRED. Add SERPAPI_API_KEY to your .env file."
                )
        else:
            configs = (
                WINNING_WISDOM_SEARCH_CONFIG.copy()
                if persona_cfg.name == "arthur"
                else TONY_SEARCH_CONFIG.copy()
            )
            random.shuffle(configs)

            # Try a few focused searches first
            for cfg in configs:
                author_source = cfg["source"]
                query = f'{author_source} quote about {topic}'
                candidates = _search_quotes(query=query, location=location)
                for candidate in candidates:
                    quote_text = candidate.get("quote", "").strip()
                    if not quote_text:
                        continue
                    if avoid_used and quote_text.lower() in used_quotes:
                        continue
                    _save_used_quote(quote_text)
                    return {
                        "topic": topic,
                        "quote": quote_text,
                        "source": author_source,
                        "fetched_at": datetime.now().isoformat(),
                    }

            if require_serpapi:
                raise RuntimeError("SerpAPI returned no clean quote aligned to the topic.")

    # Fallback: generic Winning Wisdom quote selection
    base = fetch_winning_wisdom_quote(
        avoid_used=avoid_used,
        location=location,
        persona=persona_cfg.name,
    )
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


QUOTE_SEARCH_QUERIES = [
    # Core Marcus Aurelius angles
    "Marcus Aurelius Meditations quotes wisdom",
    "Marcus Aurelius best quotes stoicism",
    "Marcus Aurelius quotes on life and purpose",
    "Marcus Aurelius quotes on discipline and self control",
    "Marcus Aurelius quotes on hardship and resilience",
    "Marcus Aurelius quotes on the present moment",
    "Marcus Aurelius quotes on virtue and character",
    "Marcus Aurelius quotes on death and mortality",
    "Marcus Aurelius quotes on inner peace",
    "Marcus Aurelius Meditations book quotes",
    "most powerful Marcus Aurelius quotes",
    "Marcus Aurelius quotes on change and impermanence",
]

# Separate search configs for the multi-author Winning Wisdom theme.
# Each entry encodes both the search query and the author-style source
# label we want to show (so we don't rely on noisy page titles like
# "41 Quotes to Change Your Habits - And Your Life").
WINNING_WISDOM_SEARCH_CONFIG = [
    # Other Stoics — same "flavour" as Marcus
    {"query": "Seneca quotes on discipline and self control", "source": "Seneca"},
    {"query": "Seneca quotes on courage and character", "source": "Seneca"},
    {"query": "Epictetus quotes on inner freedom and self mastery", "source": "Epictetus"},
    {"query": "Epictetus quotes on doing the work", "source": "Epictetus"},

    # Modern \"winning wisdom\" voices
    {"query": "Viktor Frankl quotes on meaning and responsibility", "source": "Viktor Frankl"},
    {"query": "James Clear quotes on habits and systems", "source": "James Clear"},
    {"query": "Jim Rohn quotes on discipline and success", "source": "Jim Rohn"},
    {"query": "F. M. Alexander quotes on habits and life", "source": "F. M. Alexander"},
]

TONY_SEARCH_CONFIG = [
    {"query": "workout motivation quotes consistency discipline", "source": "Fitness Wisdom"},
    {"query": "gym mindset lessons quote", "source": "Gym Mindset"},
    {"query": "fitness psychology wisdom quote", "source": "Fitness Psychology"},
    {"query": "training mindset quotes resilience", "source": "Training Mindset"},
]

# ─────────────────────────────────────────────────────────────────────
# HARD-CODED FALLBACK QUOTES — MARCUS ONLY
# ─────────────────────────────────────────────────────────────────────
FALLBACK_QUOTES = [
    {"quote": "You have power over your mind, not outside events. Realize this, and you will find strength.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The impediment to action advances action. What stands in the way becomes the way.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Never let the future disturb you. You will meet it, if you have to, with the same weapons of reason which today arm you against the present.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "It is not death that a man should fear, but he should fear never beginning to live.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The first rule is to keep an untroubled spirit. The second is to look things in the face and know them for what they are.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "If it is not right, do not do it. If it is not true, do not say it.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Very little is needed to make a happy life; it is all within yourself, in your way of thinking.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Waste no more time arguing about what a good man should be. Be one.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "You could leave life right now. Let that determine what you do and say and think.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The soul becomes dyed with the colour of its thoughts.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Accept the things to which fate binds you, and love the people with whom fate brings you together.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "When you wake up in the morning, tell yourself: the people I deal with today will be meddling, ungrateful, arrogant, dishonest, jealous and surly.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Do not indulge in dreams of what you have not, but count the blessings you actually possess.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Confine yourself to the present.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The best revenge is to be unlike him who performed the injury.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Whenever you are about to find fault with someone, ask yourself the following question: What fault of mine most nearly resembles the one I am about to criticize?", "source": "Marcus Aurelius — Meditations"},
    {"quote": "How much more grievous are the consequences of anger than the causes of it.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Begin at once to live, and count each separate day as a separate life.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Loss is nothing else but change, and change is nature's delight.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Treat yourself with respect. If a man can treat himself with respect, others cannot help but treating him with respect.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "He who lives in harmony with himself lives in harmony with the universe.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "It never ceases to amaze me: we all love ourselves more than other people, but care more about their opinion than our own.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Look well into thyself; there is a source of strength which will always spring up if thou wilt always look.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The object of life is not to be on the side of the majority, but to escape finding oneself in the ranks of the insane.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Do not act as if you had ten thousand years to live.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Think of yourself as dead. You have lived your life. Now take what's left and live it properly.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "A man's life is a mere moment, his existence a flux, his perception clouded, his body's composition corruptible.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "The universe is change; our life is what our thoughts make it.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "Just as nature takes every obstacle, every impediment, and works around it — turns it to its purposes, incorporates it into itself — so, too, a rational being can turn each setback into raw material and use it to achieve its goals.", "source": "Marcus Aurelius — Meditations"},
    {"quote": "You always own the option of having no opinion. There is never any need to get worked up or to trouble your soul about things you can't control.", "source": "Marcus Aurelius — Meditations"},
]


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
    "Stop waiting for confidence",
    "Discipline on the hard days",
    "The cost of staying comfortable",
    "What you can control today",
    "How to face criticism calmly",
    "When motivation disappears",
    "Doing the right thing quietly",
    "The difference between pain and suffering",
    "The price of avoiding hard choices",
    "Building calm under pressure",
    "How to practice self-command daily",
    "Turning setbacks into character",
    "Choosing action over overthinking",
    "Using discomfort as a teacher",
    "What real resilience looks like",
    "Living by values when stressed",
]

TONY_FALLBACK_TOPICS = [
    "Why your workouts keep stalling",
    "The discipline behind body change",
    "Gym mindset when motivation drops",
    "Recovery habits that build strength",
    "Beginner lifting mistakes to avoid",
    "Nutrition myths hurting your progress",
    "Training consistency beats intensity",
    "How to train through plateaus",
    "What to do on low-energy days",
    "The warm-up mistake ruining lifts",
    "How to build unbreakable gym habits",
    "When to push and when to deload",
    "Fixing form before adding weight",
    "Mindset shifts for body recomposition",
    "Recovery rules for faster progress",
    "Why sleep is your secret workout",
]


def fetch_marcus_aurelius_quote(
    avoid_used: bool = True,
    location: str = "United States",
) -> dict:
    """
    Fetch a clean Marcus Aurelius quote.

    First tries SerpAPI. If the result is dirty or all quotes are used,
    falls back to the verified hardcoded quote bank.

    Returns:
        dict with keys: quote, source, fetched_at
    """
    if not SERPAPI_API_KEY:
        raise ValueError(
            "SERPAPI_API_KEY is REQUIRED. "
            "Add SERPAPI_API_KEY to your .env file."
        )

    used_quotes = _load_used_quotes() if avoid_used else set()

    queries = QUOTE_SEARCH_QUERIES.copy()
    random.shuffle(queries)

    for query in queries:
        candidates = _search_quotes(query=query, location=location)
        for candidate in candidates:
            quote_text = candidate.get("quote", "").strip()
            if not quote_text:
                continue
            if avoid_used and quote_text.lower() in used_quotes:
                continue
            _save_used_quote(quote_text)
            return {
                "quote": quote_text,
                "source": "Marcus Aurelius — Meditations",
                "fetched_at": datetime.now().isoformat(),
            }

    # Fallback: use hardcoded verified quotes
    print("SerpAPI returned no clean quotes — using verified fallback bank.")
    fallbacks = FALLBACK_QUOTES.copy()
    random.shuffle(fallbacks)
    for candidate in fallbacks:
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
        "All quotes have been used. Run reset_used_quotes() to start fresh."
    )


def fetch_winning_wisdom_quote(
    avoid_used: bool = True,
    location: str = "United States",
    use_serpapi: bool = True,
    require_serpapi: bool = False,
    persona: str = "arthur",
) -> dict:
    """
    Fetch a quote for the Winning Wisdom theme.

    First tries SerpAPI with multi-author \"winning wisdom\" queries
    aimed at specific authors (Seneca, Epictetus, Frankl, etc.).
    If SerpAPI is unavailable or returns nothing clean, it falls back
    to the curated WINNING_WISDOM_QUOTES hardcoded bank.

    Returns:
        dict with keys: quote, source, fetched_at
    """
    persona_cfg = get_persona(persona)
    used_quotes = _load_used_quotes() if avoid_used else set()

    # ── 1. Try SerpAPI first (multi-author) ───────────────────────────
    if use_serpapi:
        if not SERPAPI_API_KEY:
            if require_serpapi:
                raise ValueError(
                    "SERPAPI_API_KEY is REQUIRED. Add SERPAPI_API_KEY to your .env file."
                )
        else:
            configs = (
                WINNING_WISDOM_SEARCH_CONFIG.copy()
                if persona_cfg.name == "arthur"
                else TONY_SEARCH_CONFIG.copy()
            )
            random.shuffle(configs)

            for cfg in configs:
                query = cfg["query"]
                author_source = cfg["source"]
                candidates = _search_quotes(query=query, location=location)
                for candidate in candidates:
                    quote_text = candidate.get("quote", "").strip()
                    if not quote_text:
                        continue
                    if avoid_used and quote_text.lower() in used_quotes:
                        continue
                    _save_used_quote(quote_text)
                    # Use the configured author-style source instead of
                    # noisy page titles like "41 Quotes to Change Your Habits..."
                    source = author_source
                    return {
                        "quote": quote_text,
                        "source": source,
                        "fetched_at": datetime.now().isoformat(),
                    }

            if require_serpapi:
                raise RuntimeError("SerpAPI returned no clean Winning Wisdom quotes.")

    # ── 2. Fallback: hardcoded multi-author bank ──────────────────────
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


def _search_quotes(query: str, location: str) -> list[dict]:
    """
    Run a SerpAPI Google search and extract CLEAN quotes only.
    """
    try:
        results = _serpapi_get(
            {
                "engine": "google",
                "q": query,
                "location": location,
                "hl": "en",
                "num": 10,
            }
        )
        candidates: list[dict] = []

        # 1. Answer box — highest quality, often a clean quote
        answer_box = results.get("answer_box", {}) or {}
        if isinstance(answer_box, dict) and answer_box:
            text = (answer_box.get("answer") or answer_box.get("snippet") or "").strip()
            cleaned = _clean_quote(text)
            if cleaned and _is_clean_quote(cleaned):
                source = answer_box.get("title") or "Winning Wisdom"
                candidates.append({"quote": cleaned, "source": source})

        # 2. Organic snippets — check full snippet text
        for result in results.get("organic_results", []) or []:
            if not isinstance(result, dict):
                continue
            snippet = (result.get("snippet") or "").strip()
            cleaned = _clean_quote(snippet)
            if cleaned and _is_clean_quote(cleaned):
                title = (result.get("title") or "").strip()
                source = title or "Winning Wisdom"
                candidates.append({"quote": cleaned, "source": source})

            # 3. Rich snippet extensions — often contain standalone quotes
            rich = result.get("rich_snippet") or {}
            top = rich.get("top") or {}
            for item in (top.get("extensions") or []) if isinstance(top, dict) else []:
                cleaned = _clean_quote(str(item))
                if cleaned and _is_clean_quote(cleaned):
                    title = (result.get("title") or "").strip()
                    source = title or "Winning Wisdom"
                    candidates.append({"quote": cleaned, "source": source})

        return candidates
    except Exception as e:
        print(f"SerpAPI error for query={query!r}: {e}")
        return []


def _is_clean_quote(text: str) -> bool:
    """
    Check if text is a clean, standalone quote.
    Rejects summaries, snippets, and metadata.
    """
    text = text.strip()

    # Length bounds
    if len(text) < 15 or len(text) > 400:
        return False

    # Reject commentary and metadata language only
    reject_phrases = [
        "this quote", "reminds us", "teaches us", "according to",
        "in this quote", "summary", "list of", "top 10",
        "http", "www.", "click here", "learn more", "see more",
        "read more", "shop now", "buy now",
    ]
    text_lower = text.lower()
    for phrase in reject_phrases:
        if phrase in text_lower:
            return False

    # Must be mostly alphabetic
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.55:
        return False

    # Should not trail off mid-sentence
    if text.endswith("...") or text.endswith("…"):
        return False

    return True


def _clean_quote(text: str) -> str:
    """Strip surrounding quotes, attribution, and whitespace."""
    if not text:
        return ""
    text = text.strip()
    # Remove surrounding quote marks
    text = text.strip('"\'').strip("\u201c\u201d\u2018\u2019")
    # Remove trailing attribution
    for suffix in [
        " — Marcus Aurelius", " - Marcus Aurelius",
        "~ Marcus Aurelius", " —Marcus Aurelius",
        " by Marcus Aurelius",
    ]:
        if text.lower().endswith(suffix.lower()):
            text = text[: -len(suffix)].strip()
    return text.strip()


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