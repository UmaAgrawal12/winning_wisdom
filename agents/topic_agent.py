from openai import OpenAI
from pydantic import BaseModel
from typing import List, Optional
import os
import logging
import random
from datetime import datetime
from dotenv import load_dotenv
from config.system_config import OPENAI_API_KEY, OPENAI_MODEL_TOPIC

load_dotenv()

# ─────────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)


client = OpenAI(api_key=OPENAI_API_KEY)
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


class TopicIdeas(BaseModel):
    topics: List[str]


# ─────────────────────────────────────────────────────────────────────
# AUDIENCE PROFILES
# Each profile gives the model the raw human material it needs:
# who these people are, what they secretly feel, and how they talk
# to themselves. The more specific this is, the more specific the topics.
# ─────────────────────────────────────────────────────────────────────
AUDIENCE_PROFILES = {
    "young_professional": {
        "description": "22–32 year olds in early-to-mid career. Ambitious but quietly exhausted.",
        "situation": "They're doing everything right — working hard, showing up, trying — but still feel behind. They compare themselves to peers constantly. LinkedIn makes it worse.",
        "secret_fear": "That they're wasting their 20s. That everyone else figured something out that they missed.",
        "real_talk": "I work so hard but I feel like I'm going nowhere. Why does everyone else seem so ahead?",
        "daily_reality": "Desk job or hustle culture. Back-to-back meetings or side project at midnight. Feeling underpaid, undervalued, or directionless.",
    },
    "student": {
        "description": "17–24 year olds in college or early adulthood. Self-aware but stuck.",
        "situation": "They know exactly what they should be doing. They just can't make themselves do it. Phone addiction is real. Deadlines pile up. Confidence is shaky.",
        "secret_fear": "That they'll get to 30 and realize they wasted the best years doing nothing important.",
        "real_talk": "I had the whole day free and I wasted it. Again. What is wrong with me?",
        "daily_reality": "Procrastinating on assignments, doom-scrolling, comparing themselves on social media, pulling all-nighters, feeling like a fraud.",
    },
    "entrepreneur": {
        "description": "25–40 year olds building a business or side hustle. Smart, driven, but in the messy middle.",
        "situation": "They've been at it for months. The results aren't matching the effort. Everyone around them seems to be winning. They're starting to question if they're cut out for it.",
        "secret_fear": "That they're not special enough. That success is for other people who have something they don't.",
        "real_talk": "I'm doing the work every day. So why is nothing happening? Maybe I'm the problem.",
        "daily_reality": "Inconsistent revenue, self-doubt spirals, watching competitors grow, exhaustion from wearing every hat, zero validation from outside.",
    },
    "general_self_improver": {
        "description": "18–40 year olds who consume self-improvement content but struggle to execute.",
        "situation": "They start strong every Monday. They've downloaded the apps, read the books, watched the videos. By Friday they've reset again. The gap between knowing and doing is killing them.",
        "secret_fear": "That they'll always be someone who talks about changing but never actually does.",
        "real_talk": "I know everything I need to do. I just don't do it. Why can't I just be consistent?",
        "daily_reality": "All-or-nothing thinking, quitting habits before they stick, motivational content binge, feeling like they're the only one who can't get it together.",
    },
}


# ─────────────────────────────────────────────────────────────────────
# PROVEN VIRAL TOPIC FORMULAS
# These are extracted from studying high-performing motivational shorts.
# Each formula has a different psychological trigger.
# ─────────────────────────────────────────────────────────────────────
VIRAL_TOPIC_FORMULAS = """
FORMULA BANK — use these as structural templates, not word-for-word copies.
Each formula targets a different psychological trigger. Rotate across all of them.

1. THE PERSONAL CALLOUT (makes viewer feel seen instantly)
   Pattern: "If you [specific situation they're in]..."
   Examples:
     - "If You're in Your 20s and Feel Like You're Falling Behind"
     - "If You've Ever Started Something and Quietly Given Up"
     - "If You Work Hard but Still Feel Like Nothing Is Moving"

2. THE SECRET / NOBODY TELLS YOU (creates curiosity gap + perceived insider knowledge)
   Pattern: "The [thing] Nobody Talks About" / "What Nobody Tells You About [X]"
   Examples:
     - "What Nobody Tells You About Starting Over at 25"
     - "The Part of Discipline Nobody Talks About"
     - "What Actually Happens When You Stop Seeking Motivation"

3. THE HARD TRUTH / CALLOUT (pattern interrupt — slightly uncomfortable)
   Pattern: "Stop [doing the thing they're doing]" / "You're Not [what they think] — You're [real truth]"
   Examples:
     - "Stop Waiting to Feel Ready — Here's Why"
     - "You're Not Lazy. You're Avoiding Something."
     - "The Reason You Keep Quitting Has Nothing to Do With Willpower"

4. THE REFRAME (flips a belief they already hold — makes them think differently)
   Pattern: "[Common belief] Is Wrong" / "The Real Reason You [struggle]"
   Examples:
     - "Discipline Isn't About Motivation — It Never Was"
     - "The Real Reason You Can't Stay Consistent"
     - "Why Trying Harder Is Making Things Worse"

5. THE CONTRAST (uses before/after or two opposing states to create tension)
   Pattern: "[Type A people] do this. [Type B people] do that."
   Examples:
     - "The Difference Between People Who Change and People Who Just Try"
     - "What Consistent People Do That Nobody Else Does"
     - "Average People Chase Motivation. Disciplined People Do This."

6. THE SPECIFIC SCENARIO (paints a picture the viewer has literally lived)
   Pattern: Reference a specific moment, time of day, or situation they recognize
   Examples:
     - "That Feeling at 11pm When You've Wasted the Whole Day"
     - "What It Means When You Set an Alarm You Know You'll Ignore"
     - "The Sunday Night Reset That Never Actually Works"

7. THE IDENTITY CHALLENGE (attacks their self-image in a way that motivates change)
   Pattern: Challenge who they think they are vs. who they could be
   Examples:
     - "You're Not Behind. You're Just Lying to Yourself."
     - "The Version of You Who Shows Up Every Day Already Exists"
     - "Most People Will Stay the Same. You Don't Have To."

8. THE UNCOMFORTABLE MIRROR (validates their exact pain before offering anything)
   Pattern: Name the specific loop they're stuck in
   Examples:
     - "Why You Start Every Week Strong and End It Empty"
     - "The Loop That Keeps You Resetting Every Monday"
     - "Why You Know Everything But Change Nothing"
"""


def generate_topics(
    theme: str = "discipline and self-improvement",
    n: Optional[int] = None,
    audience: str = "general_self_improver",
) -> TopicIdeas:
    """
    Generate topics DIRECTLY from SerpAPI (Google Search Engine Results API).
    
    This function uses ONLY SerpAPI to fetch trending topics from Google search.
    NO OpenAI is used - topics come directly from Google search results.
    
    REQUIRES SERPAPI_API_KEY - This function will not work without a valid SerpAPI key.
    
    Args:
        theme: Content theme (used to build search query)
        n: Optional number of topics to return. If None, returns all available trending topics.
        audience: Target audience (not used for SerpAPI, kept for API compatibility)
    
    Returns:
        TopicIdeas with topics directly from Google search results (may be fewer than requested)
    
    Raises:
        ValueError: If SERPAPI_API_KEY is not set or if topics cannot be fetched
    """
    logger.info("generate_topics() called | theme=%r | n=%s | audience=%r", theme, n, audience)

    if not SERPAPI_API_KEY:
        logger.error("SERPAPI_API_KEY is not set — aborting generate_topics()")
        raise ValueError(
            "SERPAPI_API_KEY is REQUIRED for topic generation. "
            "This function uses ONLY SerpAPI (no OpenAI). "
            "Get free API key at https://serpapi.com (100 free searches/month) "
            "and add SERPAPI_API_KEY to your .env file."
        )
    
    # Use flexible number - get what's available
    target_count = n if n is not None else 15  # Default to 15 if not specified
    
    # Add randomization to queries to get different results each time
    current_year = datetime.now().year
    current_month = datetime.now().strftime("%B")
    
    # Randomize search query variations to get fresh results
    query_variations = [
        f"trending {theme} {current_year}",
        f"{theme} viral content {current_month}",
        f"latest {theme} motivation",
        f"{theme} trending now",
        f"popular {theme} topics",
        f"{theme} self improvement {current_year}",
        f"top {theme} content",
        f"{theme} motivational shorts {current_year}",
    ]
    
    # Shuffle to get different results each run
    random.shuffle(query_variations)
    
    logger.debug("Fetching trending topics from Google via SerpAPI | theme=%r | target=%d", theme, target_count)
    
    all_topics: List[str] = []
    seen = set()
    
    # Try multiple varied queries to get diverse trending topics
    for i, query in enumerate(query_variations[:5]):  # Use first 5 variations
        if len(all_topics) >= target_count:
            break
            
        logger.debug("Search query %d/%d: %r", i+1, min(5, len(query_variations)), query)
        
        topics = fetch_trending_topics(
            query=query,
            max_results=target_count,
            location="United States",
        )
        
        # Add unique topics
        for topic in topics:
            topic_lower = topic.lower()
            if topic_lower not in seen:
                all_topics.append(topic)
                seen.add(topic_lower)
                if len(all_topics) >= target_count:
                    break
        
        logger.debug("Query %r returned %d new unique topics (total: %d)", query, len(topics), len(all_topics))
    
    # Shuffle final results for variety
    random.shuffle(all_topics)
    
    if not all_topics:
        logger.error("No topics returned from SerpAPI for theme=%r", theme)
        raise ValueError(
            "Failed to fetch topics from SerpAPI. "
            "Please check your SERPAPI_API_KEY and try again."
        )

    # Return what we have (may be less than requested, that's okay)
    final_topics = all_topics[:target_count] if n is not None else all_topics
    logger.info("generate_topics() complete | returning %d topics (requested: %s)", len(final_topics), n)
    
    return TopicIdeas(topics=final_topics)


# ─────────────────────────────────────────────────────────────────────
# TRENDING TOPICS FETCHER (SerpAPI Integration)
# Functions to fetch trending topics from Google search via SerpAPI
# ─────────────────────────────────────────────────────────────────────


def fetch_trending_topics(
    query: str = "trending motivational topics self improvement 2024",
    max_results: int = 10,
    location: str = "United States",
) -> List[str]:
    """
    Fetch trending topics using SerpAPI (Google Search Engine Results API).
    
    SerpAPI provides real Google search results, giving you access to what's
    actually trending on Google right now.
    
    Args:
        query: Search query to find trending topics
        max_results: Maximum number of results to return
        location: Location for localized search results
    
    Returns:
        List of trending topic titles/headlines from Google search results
    """
    logger.debug(
        "fetch_trending_topics() | query=%r | max_results=%d | location=%r",
        query, max_results, location,
    )

    try:
        from serpapi import GoogleSearch

        if not SERPAPI_API_KEY:
            logger.error("SERPAPI_API_KEY is missing inside fetch_trending_topics()")
            raise ValueError(
                "SERPAPI_API_KEY is REQUIRED. "
                "Topic generation requires SerpAPI. "
                "Get free API key at https://serpapi.com (100 free searches/month) "
                "and add SERPAPI_API_KEY to your .env file."
            )

        # Add randomization to get different results each time
        # Use different start positions or add random terms to vary results
        params = {
            "q": query,
            "api_key": SERPAPI_API_KEY,
            "location": location,
            "num": max_results,
            "hl": "en",
            # Add random start position to get different pages of results
            "start": random.randint(0, 10) if random.random() > 0.5 else 0,
        }

        logger.debug("Calling SerpAPI GoogleSearch with params (key redacted)")
        search = GoogleSearch(params)
        results = search.get_dict()

        topics: List[str] = []

        organic = results.get("organic_results", [])
        logger.debug("SerpAPI returned %d organic results", len(organic))
        for result in organic[:max_results]:
            title = result.get("title", "").strip()
            if title:
                topics.append(title)

        if len(topics) < max_results and "top_stories" in results:
            stories = results["top_stories"]
            logger.debug("Supplementing with %d top_stories results", len(stories))
            for story in stories[: max_results - len(topics)]:
                title = story.get("title", "").strip()
                if title and title not in topics:
                    topics.append(title)

        if len(topics) < max_results and "videos" in results:
            videos = results["videos"]
            logger.debug("Supplementing with %d video results", len(videos))
            for video in videos[: max_results - len(topics)]:
                title = video.get("title", "").strip()
                if title and title not in topics:
                    topics.append(title)

        logger.info(
            "fetch_trending_topics() collected %d topics for query=%r", len(topics), query
        )
        return topics[:max_results]

    except ImportError:
        logger.exception("google-search-results package is not installed")
        raise ImportError(
            "google-search-results package not installed. "
            "Install with: pip install google-search-results"
        )
    except Exception as e:
        logger.exception("Unexpected error in fetch_trending_topics() | query=%r | error=%s", query, e)
        return []


def fetch_platform_trending_topics(
    platform: str = "youtube",
    niche: str = "self improvement motivation",
    max_results: int = 10,
    location: str = "United States",
) -> List[str]:
    """
    Fetch trending topics from specific platforms using SerpAPI.
    
    Args:
        platform: Platform to search (youtube, tiktok, instagram, etc.)
        niche: Content niche/keywords
        max_results: Maximum number of results
        location: Location for localized results
    
    Returns:
        List of trending topic titles
    """
    logger.info(
        "fetch_platform_trending_topics() | platform=%r | niche=%r | max_results=%d",
        platform, niche, max_results,
    )
    query = f"{platform} trending {niche} shorts reels 2024"
    logger.debug("Constructed query: %r", query)
    return fetch_trending_topics(query=query, max_results=max_results, location=location)


def fetch_multiple_sources_trending(
    niches: Optional[List[str]] = None,
    max_results_per_source: int = 5,
    location: str = "United States",
) -> List[str]:
    """
    Fetch trending topics from multiple search queries and combine results.
    
    Uses SerpAPI to search multiple niches and combines the results.
    
    Args:
        niches: List of niche keywords to search
        max_results_per_source: Number of results per search query
        location: Location for localized search results
    
    Returns:
        Combined list of trending topics from all sources
    """
    if niches is None:
        niches = [
            "discipline motivation",
            "productivity tips",
            "self improvement",
            "mindset growth",
            "motivational shorts",
        ]

    logger.info(
        "fetch_multiple_sources_trending() | niches=%s | max_results_per_source=%d",
        niches, max_results_per_source,
    )

    all_topics: List[str] = []
    for niche in niches:
        query = f"trending {niche} 2024"
        logger.debug("Fetching topics for niche=%r | query=%r", niche, query)
        topics = fetch_trending_topics(
            query=query,
            max_results=max_results_per_source,
            location=location,
        )
        logger.debug("Niche %r returned %d topics", niche, len(topics))
        all_topics.extend(topics)

    seen: set = set()
    unique_topics: List[str] = []
    for topic in all_topics:
        if topic.lower() not in seen:
            seen.add(topic.lower())
            unique_topics.append(topic)

    logger.info(
        "fetch_multiple_sources_trending() done | total=%d | unique=%d",
        len(all_topics), len(unique_topics),
    )
    return unique_topics


# ─────────────────────────────────────────────────────────────────────
# TOPIC GENERATION WITH TRENDING INSPIRATION
# ─────────────────────────────────────────────────────────────────────


def generate_topics_with_trending_inspiration(
    theme: str = "discipline and self-improvement",
    n: int = 10,
    audience: str = "general_self_improver",
    use_trending: bool = True,
    trending_sources: Optional[List[str]] = None,
) -> TopicIdeas:
    """
    Generate topics using SerpAPI (Google Search Engine Results API) to fetch trending topics as inspiration.
    
    REQUIRES SERPAPI_API_KEY - This function will not work without a valid SerpAPI key.
    SerpAPI provides real Google search results, giving you access to what's actually
    trending on Google right now.
    
    Args:
        theme: Content theme
        n: Number of topics to generate
        audience: Target audience profile
        use_trending: Whether to fetch and use trending topics (must be True - SerpAPI is required)
        trending_sources: Optional list of niche keywords for trending search
    
    Returns:
        TopicIdeas with generated topics
    
    Raises:
        ValueError: If SERPAPI_API_KEY is not set or if trending topics cannot be fetched
    """
    logger.info(
        "generate_topics_with_trending_inspiration() | theme=%r | n=%d | audience=%r | use_trending=%s",
        theme, n, audience, use_trending,
    )

    if not SERPAPI_API_KEY:
        logger.error("SERPAPI_API_KEY is not set — aborting")
        raise ValueError(
            "SERPAPI_API_KEY is REQUIRED for topic generation. "
            "Get free API key at https://serpapi.com (100 free searches/month) "
            "and add SERPAPI_API_KEY to your .env file."
        )

    if not use_trending:
        logger.error("use_trending=False passed — this function requires trending to be enabled")
        raise ValueError(
            "use_trending must be True. This function requires SerpAPI trending topics. "
            "If you want to generate topics without trending, use generate_topics() instead."
        )

    trending_context = ""
    logger.info("Fetching trending topics via SerpAPI")

    if trending_sources:
        logger.debug("Using custom trending_sources: %s", trending_sources)
        trending_topics = fetch_multiple_sources_trending(
            niches=trending_sources,
            max_results_per_source=3,
        )
    else:
        default_niches = [
            f"{theme} motivation",
            "viral motivational shorts",
            "trending self improvement",
        ]
        logger.debug("Using default niches: %s", default_niches)
        trending_topics = fetch_multiple_sources_trending(
            niches=default_niches,
            max_results_per_source=3,
        )

    if not trending_topics:
        logger.error("SerpAPI returned no trending topics — aborting")
        raise ValueError(
            "Failed to fetch trending topics from SerpAPI. "
            "Please check your SERPAPI_API_KEY and try again."
        )

    logger.info("Fetched %d trending topics for inspiration", len(trending_topics))

    trending_context = f"""
=============================
CURRENT TRENDING TOPICS (for inspiration only — do NOT copy these)
=============================
These are trending topics found via SerpAPI (Google Search Engine Results API). 
These are real Google search results showing what people are actually searching for.
Use them to understand what's currently resonating, but generate FRESH topics that are:
- More specific to our audience profile
- Aligned with our viral topic formulas
- Better suited for our brand voice

Trending examples:
{chr(10).join(f"- {topic}" for topic in trending_topics[:10])}

IMPORTANT: Do NOT copy these titles. Use them only to understand trending themes 
and angles. Generate original topics that feel more personal and specific to our audience.
"""

    profile = AUDIENCE_PROFILES.get(audience, AUDIENCE_PROFILES["general_self_improver"])
    logger.debug("Using audience profile: %r", audience)

    prompt = f"""
You are the head content strategist for "Winning Wisdom," a motivational short-form video brand
on YouTube Shorts, TikTok, Instagram Reels, and Facebook Reels.

Your job is to generate {n} topic titles that stop the scroll.
Not conceptually interesting topics. Not generic advice titles.
Topics that make the target viewer feel, in under 3 seconds of reading:
"This is literally about me."

That recognition is what drives likes, saves, shares, and follows.

{trending_context}

=============================
WHO YOU ARE WRITING FOR
=============================
Who they are: {profile["description"]}
Their daily situation: {profile["situation"]}
Their secret fear: {profile["secret_fear"]}
What they say to themselves: "{profile["real_talk"]}"
What their day actually looks like: {profile["daily_reality"]}

=============================
CONTENT THEME
=============================
{theme}

=============================
VIRAL TOPIC FORMULAS — your toolkit
=============================
{VIRAL_TOPIC_FORMULAS}

=============================
WHAT MAKES A TOPIC TITLE WORK
=============================
The single best-performing topics on motivational short-form video do ONE of these things
in the title alone — before anyone even clicks play:

1. CALL OUT A SPECIFIC SITUATION
   The viewer reads it and thinks "how does this know my exact life right now?"
   Bad: "How to Build Better Habits"
   Good: "Why You Build Habits for Two Weeks and Then Stop"

2. NAME A FEELING THEY HAVE BUT HAVEN'T ARTICULATED
   The viewer has felt this but never heard it said this clearly.
   Bad: "Dealing with Procrastination"
   Good: "The Guilt You Feel at the End of a Wasted Day"

3. CHALLENGE SOMETHING THEY BELIEVE
   Flip a common belief they hold. Creates an open loop they need closed.
   Bad: "Why Motivation Matters"
   Good: "Motivation Is Actually Making You Worse"

4. MAKE THEM FEEL CALLED OUT (gently)
   Not mean. Not harsh. But specific enough that it stings a little in a relatable way.
   Bad: "Stop Procrastinating"
   Good: "You Don't Procrastinate Because You're Lazy — Read This"

=============================
TOPIC TITLE RULES
=============================
Every title must:
- Be 6–14 words. Long enough to be specific, short enough to scan instantly.
- Sound like something a real person would say, not a content marketing headline.
- Contain ZERO corporate or self-help clichés:
  BANNED WORDS AND PHRASES: "game changer," "level up," "hustle," "grind," "unstoppable," 
  "supercharge," "hack," "unlock your potential," "maximize," "optimize," "dominate,"
  "crush it," "skyrocket," "secrets," "tips," "strategies," "transform your life."
- Feel specific to this audience's actual daily experience, not generic life advice.
- Create either CURIOSITY (open loop), RECOGNITION (that's me), or TENSION (discomfort).

Vary the angle across the {n} topics. Do NOT generate {n} versions of the same formula.
Use the formula bank above and rotate: callout, reframe, hard truth, contrast, mirror, identity shift.

=============================
QUALITY TEST — before including any topic, ask:
=============================
- Would someone in this audience read this and feel called out or seen? (YES = include it)
- Does it sound like something a person would actually say? (YES = include it)
- Does it use any banned clichés or generic language? (YES = rewrite it)
- Could this title belong to a video by any generic motivational account? (YES = make it more specific)

=============================
OUTPUT FORMAT
=============================
Return ONLY a numbered list of {n} topic titles.
No explanations. No formulas labels. No extra commentary.
Just the titles, one per line.
"""

    logger.info("Sending prompt to OpenAI | model=%r | n=%d", OPENAI_MODEL_TOPIC, n)

    response = client.chat.completions.create(
        model=OPENAI_MODEL_TOPIC,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert short-form content strategist who studies what makes motivational "
                    "videos go viral. You understand audience psychology deeply — what people feel but "
                    "don't say, what makes them stop scrolling, and what makes them share something with "
                    "a friend. You write topic titles that feel personal, not professional."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.88,
    )

    raw_text = response.choices[0].message.content.strip()
    logger.debug("OpenAI raw response length: %d chars", len(raw_text))

    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    topics: List[str] = []
    for line in lines:
        cleaned = line
        if len(line) > 2 and (line[1] in ".)" or (len(line) > 3 and line[2] in ".)")):
            cleaned = line.split(".", 1)[-1].split(")", 1)[-1].strip()
        elif line.startswith("- "):
            cleaned = line[2:].strip()
        topics.append(cleaned)

    logger.info(
        "generate_topics_with_trending_inspiration() complete | parsed %d topics from OpenAI response",
        len(topics[:n]),
    )
    return TopicIdeas(topics=topics[:n])