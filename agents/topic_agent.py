import os
from openai import OpenAI
from pydantic import BaseModel
from typing import List
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL_TOPIC = os.getenv("OPENAI_MODEL_TOPIC")

client = OpenAI(api_key=OPENAI_API_KEY)


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
    n: int = 10,
    audience: str = "general_self_improver",
) -> TopicIdeas:
    """
    Generate n viral-ready short-form video topic titles for Winning Wisdom.
    Topics are audience-targeted, emotionally specific, and built on proven virality formulas.
    """

    profile = AUDIENCE_PROFILES.get(audience, AUDIENCE_PROFILES["general_self_improver"])

    prompt = f"""
You are the head content strategist for "Winning Wisdom," a motivational short-form video brand
on YouTube Shorts, TikTok, Instagram Reels, and Facebook Reels.

Your job is to generate {n} topic titles that stop the scroll.
Not conceptually interesting topics. Not generic advice titles.
Topics that make the target viewer feel, in under 3 seconds of reading:
"This is literally about me."

That recognition is what drives likes, saves, shares, and follows.

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
    lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
    topics: List[str] = []
    for line in lines:
        cleaned = line
        # Strip leading "1. " or "1) " or "- " patterns
        if len(line) > 2 and (line[1] in ".)" or (len(line) > 3 and line[2] in ".)")):
            cleaned = line.split(".", 1)[-1].split(")", 1)[-1].strip()
        elif line.startswith("- "):
            cleaned = line[2:].strip()
        topics.append(cleaned)

    return TopicIdeas(topics=topics[:n])