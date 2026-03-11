from openai import OpenAI
from pydantic import BaseModel
from config.system_config import OPENAI_API_KEY, OPENAI_MODEL_SCRIPT

client = OpenAI(api_key=OPENAI_API_KEY)


class Script(BaseModel):
    topic: str
    text: str


# Audience profiles — inner monologue, scene contexts, language register
AUDIENCE_PROFILES = {
    "young_professional": {
        "description": "22–32 year olds, ambitious, early career, often feel behind their peers",
        "pains": "imposter syndrome, burnout, comparing themselves to peers, fear of wasting their 20s",
        "inner_voice": "I work hard but nothing moves. Everyone else seems further ahead. Am I doing something wrong?",
        "scene_hooks": [
            "If you're in your 20s and you feel like you're falling behind...",
            "If you've ever sat at your desk at midnight wondering if any of this is even working...",
            "If you're giving everything you have and still feel like it's not enough...",
            "Picture this. You're doing all the right things. Working late. Saying yes to everything. And yet...",
        ],
        "language": "Direct, slightly worn-out but still hungry. Respects honesty over hype. No corporate clichés.",
    },
    "student": {
        "description": "17–24 year olds in college or figuring out early adulthood",
        "pains": "procrastination, phone addiction, not knowing what they want, pressure to have it all figured out",
        "inner_voice": "I know what I should do. I just can't make myself do it. I waste hours and then hate myself for it.",
        "scene_hooks": [
            "If you've ever opened your phone for one minute and looked up two hours later...",
            "Remember the last time you had a deadline, and you still couldn't start?",
            "If you're in college and you feel like everyone else has their life figured out except you...",
            "Think about the last Sunday you told yourself, 'This week is going to be different.'",
        ],
        "language": "Casual, self-aware, blunt but not harsh. Talks like a slightly older friend, not a life coach.",
    },
    "entrepreneur": {
        "description": "25–40 year olds building a business or side hustle, dealing with slow progress and doubt",
        "pains": "inconsistency, self-doubt, slow results, isolation, second-guessing every decision",
        "inner_voice": "Maybe I'm not cut out for this. Everyone around me seems to be winning. What am I missing?",
        "scene_hooks": [
            "If you've been building something for months and you're starting to wonder if it's worth it...",
            "There's a specific feeling. When you're doing the work every day, and nothing seems to be moving.",
            "If you've ever looked at someone else's success and wondered what they know that you don't...",
            "Picture the version of you six months ago, full of energy, ready to go. Now compare that to right now.",
        ],
        "language": "Grounded, zero fluff, respects their intelligence. Talks like a mentor who has been there.",
    },
    "general_self_improver": {
        "description": "18–40 year olds who want to level up but keep falling back into old patterns",
        "pains": "starting strong and quitting, motivation vs discipline gap, all-or-nothing thinking",
        "inner_voice": "I start things. I don't finish things. Every Monday I reset. Every Friday I'm back to zero.",
        "scene_hooks": [
            "If you've ever started something with everything you had, and then quietly stopped...",
            "Think about the last habit you tried to build. How long did it last?",
            "If you've told yourself 'I'll start Monday' more times than you can count...",
            "There's a version of you that wakes up early, stays consistent, and actually follows through. You've seen glimpses of that person.",
        ],
        "language": "Warm but real. Validates the struggle, then challenges. Like a friend who cares enough to be honest.",
    },
}


def generate_script(topic: str, audience: str = "general_self_improver") -> Script:
    """
    Generate a 35-50 second avatar-ready spoken script.
    Structure: Scene-Setting Hook -> Pain Mirror -> Reframe/Insight -> Concrete Example -> Identity Shift Takeaway
    """

    profile = AUDIENCE_PROFILES.get(audience, AUDIENCE_PROFILES["general_self_improver"])

    # Build example hooks as a formatted list for the prompt
    hook_examples = "\n".join(f'  * "{h}"' for h in profile["scene_hooks"])

    prompt = f"""
You are the lead scriptwriter for "Winning Wisdom," a motivational short-form video brand.
Your scripts are delivered by an AI avatar on YouTube Shorts, Instagram Reels, TikTok, and Facebook Reels.

Your single most important job: write a script that makes the viewer think, in the first 4 seconds,
"This is about ME. I need to hear this."

=============================
AUDIENCE
=============================
Who they are: {profile["description"]}
What hurts them: {profile["pains"]}
What is playing in their head right now: "{profile["inner_voice"]}"
How they speak and what they respond to: {profile["language"]}

=============================
TOPIC
=============================
{topic}

=============================
SCRIPT STRUCTURE — follow this exactly
=============================

-- SECTION 1: THE HOOK (first 4-5 seconds, 2-3 lines) --

The hook must place the viewer INSIDE a scene or situation they have actually lived.
Not a concept. Not a quote. A moment they recognize immediately.

Use a SCENE-SETTING or DIRECT-ADDRESS opening. Examples for this audience:
{hook_examples}

The hook formula:
  [Specific situation the viewer has been in] + [the exact feeling they had in that moment]

GOOD examples:
  "If you've ever set an alarm for 5am... and still woke up at 8... you already know what I'm about to say."
  "There's a moment most people have. Usually late at night. Where you ask yourself — what am I actually doing?"
  "Picture this. You write out the whole plan. You feel ready. And then... you don't start."

BAD examples — NEVER do these:
  "Consistency is really important for success."
  "Today I want to talk about why talent isn't everything."
  "A lot of people struggle with discipline."

Rules:
- Open with "If you...", "Think about...", "Picture this.", "There's a moment...", or a "You" address.
- Max 3 lines. The first line must create instant recognition.
- Do NOT open with "I". Do NOT open with the topic name directly.
- No generic observations. Open with a scene or a feeling.

-- SECTION 2: PAIN MIRROR (3-4 lines) --

Describe what the viewer already feels, in their own language. This is not advice. It is a mirror.
Make them feel completely understood before you offer anything.

Use specifics: a time of day, a physical detail, a thought they've actually had.

NOT this: "Many people struggle to stay consistent."
YES this: "You start the week strong. By Wednesday you're already negotiating. By Friday you've reset again."

Do not give solutions here. Just reflect their reality back at them.

-- SECTION 3: THE REFRAME (3-5 lines) --

Shift how they see the problem. One quiet insight. Not a lecture.
It should feel like something clicked, not like a lesson was given.

Ways to do this:
  - Rename the problem: "It's not laziness. It's fear dressed up as laziness."
  - Reveal the hidden mechanism: "Every time you quit, your brain files that away. And it pulls that file out the next time you try."
  - Challenge the belief they're holding: "You think you need more motivation. But motivation is actually the last thing you need."

One strong reframe beats three weak ones. Keep it simple.

-- SECTION 4: THE CONCRETE SCENE (3-5 lines) --

Make the insight real. Give the viewer a scene they can picture.
A specific person. A specific action. A specific moment. Second person works best here.

GOOD: "Think about someone who trains every single day. Not when they feel like it. Every day.
      They don't wait to feel ready. They don't negotiate.
      They just put their shoes on. That is the entire system."

BAD: "Successful people stay consistent and build good habits over time."

-- SECTION 5: THE IDENTITY SHIFT TAKEAWAY (2-4 lines) --

End by changing WHO they believe they are, not just what they should do.
Identity drives behavior. Give them a new self-image to step into.

GOOD: "You are not someone who lacks discipline.
      You are someone who hasn't decided yet.
      Decide. And act like it. Starting with one thing. Tonight."

BAD: "So stay consistent and keep working hard. You've got this."
BAD: "Remember, every small step matters on your journey."

The last line should have weight. Something they think about after the video ends.

=============================
AI AVATAR DELIVERY — CRITICAL RULES
=============================
This script is spoken aloud by an AI avatar. Write for the EAR, not the eye.
Every punctuation mark you use is a delivery instruction to the avatar.

LINE LENGTH:
- One thought per line. Two ideas in one line = split it into two lines.
- Short lines (4-8 words) = punchy, fast. Use for hooks and payoff lines.
- Medium lines (9-14 words) = normal pace. Use for explanation and story.
- Hard limit: no line longer than 15 words. The avatar must be able to say it in one breath.

PUNCTUATION AS PACING:
- Period (.)     = full stop. Avatar pauses. Lets the line land.
- Comma (,)      = micro-pause. Keeps rhythm, connects related thoughts.
- Ellipsis (...)  = slow down, breathe. Use before a reveal or a heavy truth.
- Em dash (--)    = a beat, then pivot. Use for contrast or a surprise turn.
- Question mark  = rising tone. Pulls the viewer in.
- AVOID: semicolons, colons, parentheses. Avatars do not handle these well.

LANGUAGE RULES:
- Always use contractions: "you're" not "you are", "it's" not "it is", "didn't" not "did not."
- Always use second person: "you", "your". This is a personal conversation, not a speech.
- Active voice only. "You quit" not "quitting happened."
- 8th grade vocabulary. No jargon. No five-syllable words.
- No platform names. No subscribe or follow asks. No "in today's video." No "Winning Wisdom."
- No filler openers: never start with "In this video...", "Today we're going to...", "Let me tell you..."

TONE:
- Calm authority. Like a slightly older version of the viewer talking to them honestly.
- Not a hype man. Not a TED talk. Not a life coach.
- The feeling should be: "I've been where you are. Here's what I wish I'd known."

=============================
LENGTH
=============================
Target: 90 to 120 words total. This is 35-50 seconds spoken by an AI avatar.
Do not exceed 120 words.

=============================
OUTPUT FORMAT
=============================
Return ONLY the spoken script.
One thought per line. The line break is the pacing cue for the avatar.
No section headers. No labels. No stage directions. No word count.
Just the clean script, ready to paste directly into an avatar tool.

Before you finish: read your script out loud once.
If any line sounds like something you would write in an essay rather than say in a conversation, rewrite it.
"""

    response = client.chat.completions.create(
        model=OPENAI_MODEL_SCRIPT,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert short-form video scriptwriter. Your scripts are spoken aloud by AI avatars. "
                    "You understand spoken rhythm, pacing through punctuation, and how to make someone in a "
                    "short-form feed stop scrolling and feel personally addressed in the first 4 seconds. "
                    "You write entirely for the ear. Every word you write will be spoken out loud."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.75,
    )

    text = response.choices[0].message.content.strip()
    return Script(topic=topic, text=text)
