from openai import OpenAI
from pydantic import BaseModel
from typing import List, Dict
import json

from config.system_config import OPENAI_API_KEY, OPENAI_MODEL_SEO

client = OpenAI(api_key=OPENAI_API_KEY)


class PlatformSEO(BaseModel):
    title: str
    description: str
    hashtags: List[str]


class SEOResult(BaseModel):
    youtube: PlatformSEO
    instagram: PlatformSEO
    tiktok: PlatformSEO
    facebook: PlatformSEO


# Audience hashtag layers — niche tags differ by audience
AUDIENCE_HASHTAG_CONTEXT = {
    "young_professional": "career growth, hustle culture critique, early career, work-life balance, ambition",
    "student": "college life, student motivation, study habits, campus life, adulting",
    "entrepreneur": "entrepreneurship, solopreneur, startups, business mindset, founder life",
    "general_self_improver": "self improvement, personal development, habits, mindset, discipline",
}

# Audience-specific caption voice guide
AUDIENCE_CAPTION_VOICE = {
    "young_professional": "Speak to the ambitious but tired. Tone: direct, a little weary, deeply honest.",
    "student": "Speak to the overwhelmed but self-aware. Tone: relatable, slightly casual, cuts through the noise.",
    "entrepreneur": "Speak to the builder who doubts themselves. Tone: grounded, no fluff, respects their intelligence.",
    "general_self_improver": "Speak to the person who starts and stops. Tone: warm but real, validating then challenging.",
}


def generate_seo_metadata(
    topic: str,
    script_text: str,
    audience: str = "general_self_improver",
) -> SEOResult:
    """
    Generate audience-targeted SEO metadata for YouTube, Instagram, TikTok, and Facebook.

    Notes by platform:
    - YouTube: real video title + description + hashtags (separate field).
    - Instagram Reels, TikTok, Facebook Reels: caption (description) is kept clean,
      hashtags are stored separately in the hashtags field only — NOT appended to caption.
    """

    hashtag_context = AUDIENCE_HASHTAG_CONTEXT.get(
        audience, AUDIENCE_HASHTAG_CONTEXT["general_self_improver"]
    )
    caption_voice = AUDIENCE_CAPTION_VOICE.get(
        audience, AUDIENCE_CAPTION_VOICE["general_self_improver"]
    )

    prompt = f"""
You are the senior social media strategist for "Winning Wisdom," a motivational short-form video brand.
Your metadata is responsible for the first impression: whether someone taps play or scrolls past.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VIDEO CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Topic: {topic}

Full script:
\"\"\"
{script_text}
\"\"\"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TARGET AUDIENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Caption voice guide: {caption_voice}
Audience content universe: {hashtag_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLATFORM-BY-PLATFORM INSTRUCTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── YOUTUBE ──
TITLE (required):
- 45–65 characters.
- Must make someone stop mid-scroll and feel personally addressed.
- Use one of these proven formats:
    • Hard truth: "The Real Reason You Can't Stay Consistent"
    • Audience callout: "If You Keep Quitting, Watch This"
    • Reframe: "Discipline Isn't What You Think It Is"
    • Curiosity gap: "The One Habit Quietly Killing Your Progress"
- No emojis. No platform names. No "How To" unless genuinely instructional.
- Must reflect the script's actual core message — no bait-and-switch.

DESCRIPTION (required):
- 2–4 lines max. Ultra-clear. Benefit-first.
- Line 1: Restate the core tension or insight from the script in a fresh way.
- Line 2: Optionally add context or a second angle.
- Line 3 (optional): One soft, natural CTA — "Save this for the next time you want to quit."
  or "Send this to someone who needs to hear it." — NO subscribe/follow/like language.
- Do NOT repeat the title verbatim.
- Hashtags go in the hashtags field, NOT in this description text.

── INSTAGRAM REELS ──
TITLE: must be "" (empty string — Instagram has no separate title field).

DESCRIPTION / CAPTION:
- This IS the caption. It must work standalone.
- Voice: {caption_voice}
- Structure:
    Line 1 (Hook): First line must stop the scroll. Bold claim, direct callout, or painful truth.
                   Instagram shows only the first ~125 characters before "more" — make it count.
    Lines 2–3 (Body): 1–2 lines that deepen the hook or tease the insight.
    Do NOT include any hashtags in the description — they belong in the hashtags field only.
- Tone: emotional resonance first, insight second. Instagram rewards saves and shares.
- Avoid: generic phrases like "Swipe to learn more," "double tap if you agree," "drop a comment."

── TIKTOK ──
TITLE: must be "" (empty string — TikTok has no separate title field).

DESCRIPTION / CAPTION:
- Voice: {caption_voice}
- TikTok captions are short and punchy — max 2–3 tight lines.
- Line 1: The most direct, provocative version of the video's core truth.
- Lines 2–3 (optional): Reinforce with a short follow-up or contrasting line.
- TikTok skews younger and more direct — cut anything that sounds like it's trying too hard.
- Do NOT include any hashtags in the description — they belong in the hashtags field only.

── FACEBOOK REELS ──
TITLE: must be "" (empty string).

DESCRIPTION / CAPTION:
- Voice: {caption_voice}
- Facebook audience skews slightly older and prefers slightly more context.
- 2–4 lines. Can be a tiny bit warmer and more conversational than TikTok.
- Still lead with a strong first line — Facebook autoplay means captions compete for attention too.
- Do NOT include any hashtags in the description — they belong in the hashtags field only.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HASHTAG RULES (apply to all platforms)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- 9–12 hashtags per platform.
- Return as plain words WITHOUT the "#" symbol.
- Strategy: mix 3 tiers:
    Tier 1 — Niche (high relevance, lower competition): e.g., "disciplinedaily", "selfimprovementjourney"
    Tier 2 — Mid-broad (audience universe): e.g., "mindsetshift", "motivationmatters"
    Tier 3 — Broad reach: e.g., "motivation", "success", "personaldevelopment"
- Always include: "winningwisdom" as a brand tag.
- Tailor Tier 1 tags to the audience context: {hashtag_context}
- All lowercase. No spaces. Use camelCase for multi-word tags (e.g., "morningRoutine").
- No duplicate tags across tiers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
QUALITY CHECK — before finalizing, verify:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ YouTube title does NOT repeat verbatim in any caption.
✓ Each platform's caption feels native to that platform's voice and audience behavior.
✓ No caption (description field) contains any hashtags — hashtags are ONLY in the hashtags array.
✓ Instagram caption's first 125 characters are the strongest possible hook.
✓ No generic filler: "check this out," "so true," "game changer," "life-changing."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return ONLY valid JSON. No preamble, no explanation, no markdown fences.

{{
  "youtube": {{
    "title": "...",
    "description": "...",
    "hashtags": ["...", "..."]
  }},
  "instagram": {{
    "title": "",
    "description": "...",
    "hashtags": ["...", "..."]
  }},
  "tiktok": {{
    "title": "",
    "description": "...",
    "hashtags": ["...", "..."]
  }},
  "facebook": {{
    "title": "",
    "description": "...",
    "hashtags": ["...", "..."]
  }}
}}
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL_SEO,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior social media strategist specializing in short-form video metadata. "
                    "You understand platform-specific audience behavior, search intent, and the psychology "
                    "of what makes someone tap play vs scroll past. You output only valid JSON."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.6,
        response_format={"type": "json_object"},
    )

    raw_json = response.choices[0].message.content
    parsed: Dict = json.loads(raw_json)

    # Post-process YouTube: clean hashtags
    yt = parsed.get("youtube", {})
    parsed["youtube"] = {
        "title": yt.get("title", "") or "",
        "description": yt.get("description", "") or "",
        "hashtags": [h.lstrip("#").strip() for h in yt.get("hashtags", []) if isinstance(h, str)],
    }

    # For IG / TikTok / FB: force title="", keep caption and hashtags SEPARATE
    # Hashtags are NOT appended to the caption/description text
    for platform in ["instagram", "tiktok", "facebook"]:
        block = parsed.get(platform, {})
        base_description = block.get("description", "") or ""
        if not isinstance(base_description, str):
            base_description = ""

        raw_tags = block.get("hashtags", [])
        if not isinstance(raw_tags, list):
            raw_tags = []
        hashtags = [h.lstrip("#").strip() for h in raw_tags if isinstance(h, str)]

        parsed[platform] = {
            "title": "",
            "description": base_description.strip(),
            "hashtags": hashtags,
        }

    normalized_json = json.dumps(parsed)
    return SEOResult.parse_raw(normalized_json)