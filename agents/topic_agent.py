import os
import json
import random
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

USED_QUOTES_FILE = Path("data/used_quotes.json")


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

# ─────────────────────────────────────────────────────────────────────
# HARD-CODED FALLBACK QUOTES
# Clean, verified Marcus Aurelius quotes used when SerpAPI
# returns dirty/incomplete results
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


def _search_quotes(query: str, location: str) -> list[dict]:
    """
    Run a SerpAPI Google search and extract CLEAN quotes only.
    Strict filtering — rejects anything that looks like a snippet or summary.
    """
    try:
        from serpapi import GoogleSearch

        params = {
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "location": location,
            "hl": "en",
            "num": 10,
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        candidates = []

        # 1. Answer box — highest quality, often a clean quote
        answer_box = results.get("answer_box", {})
        if answer_box:
            text = (
                answer_box.get("answer")
                or answer_box.get("snippet")
                or ""
            ).strip()
            cleaned = _clean_quote(text)
            if cleaned and _is_clean_quote(cleaned):
                candidates.append({"quote": cleaned})

        # 2. Organic rich snippets — list items are usually standalone quotes
        for result in results.get("organic_results", []):
            for item in result.get("rich_snippet", {}).get("top", {}).get("extensions", []):
                cleaned = _clean_quote(item)
                if cleaned and _is_clean_quote(cleaned):
                    candidates.append({"quote": cleaned})

        return candidates

    except ImportError:
        raise ImportError(
            "google-search-results package not installed. "
            "Install with: pip install google-search-results"
        )
    except Exception as e:
        print(f"SerpAPI error for query={query!r}: {e}")
        return []


def _is_clean_quote(text: str) -> bool:
    """
    Strict check: is this a clean, standalone quote?
    Rejects summaries, listicles, partial snippets, and metadata.
    """
    text = text.strip()

    # Length bounds — quotes are typically 10–200 characters
    if len(text) < 15 or len(text) > 300:
        return False

    # Reject if it contains commentary/summary language
    reject_phrases = [
        "this quote", "reminds us", "teaches us", "according to",
        "in this quote", "meaning", "summary", "list of", "top 10",
        "http", "www.", "click", "learn more", "see more",
        ":", "–", "...\"",  # mid-sentence breaks typical of snippets
    ]
    text_lower = text.lower()
    for phrase in reject_phrases:
        if phrase in text_lower:
            return False

    # Must be mostly alphabetic
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.65:
        return False

    # Should end like a sentence, not trail off
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