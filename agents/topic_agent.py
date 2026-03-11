from openai import OpenAI
from pydantic import BaseModel
from typing import List
from config.system_config import OPENAI_API_KEY, OPENAI_MODEL_TOPIC

client = OpenAI(api_key=OPENAI_API_KEY)


class TopicIdeas(BaseModel):
    topics: List[str]


# Audience segments with their core pain points and desires
AUDIENCE_PROFILES = {
    "young_professional": {
        "description": "22–32 year olds early in their career, ambitious but overwhelmed, comparing themselves to peers",
        "pains": "imposter syndrome, burnout, feeling behind, social comparison, lack of focus",
        "desires": "career success, financial freedom, being taken seriously, proving themselves",
    },
    "student": {
        "description": "17–24 year olds in college or early adulthood, figuring out identity and direction",
        "pains": "procrastination, distraction (phone/social media), pressure to have it figured out, low motivation",
        "desires": "academic success, clarity on life path, confidence, building good habits early",
    },
    "entrepreneur": {
        "description": "25–40 year olds building a business or side hustle, dealing with uncertainty and slow progress",
        "pains": "self-doubt, inconsistency, isolation, slow results, fear of failure",
        "desires": "financial independence, recognition, building something meaningful, discipline",
    },
    "general_self_improver": {
        "description": "18–40 year olds who consume motivational content daily, want to level up but struggle with consistency",
        "pains": "starting strong but quitting, all-or-nothing thinking, motivation vs discipline gap, comparison",
        "desires": "becoming their best self, building habits that stick, mental toughness, inner peace",
    },
}


def generate_topics(
    theme: str = "discipline and self-improvement",
    n: int = 10,
    audience: str = "general_self_improver",
) -> TopicIdeas:
    """
    Generate n short-form video topic ideas for Winning Wisdom,
    targeted to a specific audience segment.
    """

    profile = AUDIENCE_PROFILES.get(audience, AUDIENCE_PROFILES["general_self_improver"])

    prompt = f"""
You are a world-class content strategist for "Winning Wisdom," a motivational short-form video brand
that dominates YouTube Shorts, TikTok, Instagram Reels, and Facebook Reels.

Your job is to generate {n} scroll-stopping video topic ideas that will make the TARGET AUDIENCE
immediately think: "This is literally about me. I have to watch this."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TARGET AUDIENCE PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Who they are: {profile["description"]}
What hurts them: {profile["pains"]}
What they want: {profile["desires"]}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTENT THEME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{theme}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOPIC GENERATION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each topic must:
1. FEEL PERSONAL — speak directly to the audience's lived experience, not generic advice.
   Bad: "Why discipline matters"
   Good: "Why you're disciplined for others but never for yourself"

2. CREATE TENSION or CURIOSITY — use contrast, a surprising truth, or a counterintuitive angle.
   Bad: "How to build habits"
   Good: "The habit that's quietly destroying your momentum every morning"

3. BE SPECIFIC — vague topics get skipped. Specific topics get watched.
   Bad: "Improving your mindset"
   Good: "What your 2 AM thoughts are actually telling you"

4. TRIGGER RECOGNITION — the viewer should feel called out or seen within the first read.
   Use language the audience actually uses internally: "I'll start Monday," "I'm just tired,"
   "Everyone else seems to have it together."

5. VARY THE ANGLE — mix these perspectives across the {n} topics:
   - Hard truth / pattern interrupt ("The real reason you can't stick to anything")
   - Permission slip / self-compassion ("You're not lazy. You're depleted.")
   - Reframe ("What you call procrastination is actually fear")
   - Tactical insight ("The 2-minute rule that fixes 80% of your mornings")
   - Identity shift ("Stop trying to be motivated. Become the person who shows up anyway.")

FORMAT:
- Return ONLY a numbered list of {n} topic titles.
- 6–12 words each. No full sentences, no punctuation at the end.
- No emojis, no hashtags.
- Make every single topic feel like it was written specifically for someone in this audience,
  not for the internet in general.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL_TOPIC,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert short-form content strategist who specializes in "
                    "audience-targeted motivational content. You deeply understand human psychology, "
                    "pain points, and what makes people stop scrolling."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.85,
    )

    raw_text = response.choices[0].message.content.strip()
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    topics: List[str] = []
    for line in lines:
        cleaned = line
        if len(line) > 2 and (line[1] in ".)" or line[2] in ".)"):
            cleaned = line.split(".", 1)[-1].split(")", 1)[-1].strip()
        topics.append(cleaned)

    return TopicIdeas(topics=topics[:n])
