from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class PersonaConfig:
    name: str
    display_name: str
    description: str
    voice_style: str
    content_focus: str
    topic_keywords: List[str]
    topic_queries: List[str]
    banned_phrases: List[str]
    entry_angles: List[str]
    temperature: float
    voice_id: Optional[str]
    avatar_id: Optional[str]
    seo_base_tags: List[str]


PERSONAS: Dict[str, PersonaConfig] = {
    "arthur": PersonaConfig(
        name="arthur",
        display_name="Arthur",
        description="Stoic philosophy guide with a warm grandfather voice.",
        voice_style="Calm, wise, warm, reflective, deeply human.",
        content_focus="Stoicism, discipline, resilience, meaning, character, self-mastery.",
        topic_keywords=[
            "stoicism",
            "discipline",
            "resilience",
            "self mastery",
            "meaning",
            "character",
        ],
        topic_queries=[
            "stoic quotes",
            "Marcus Aurelius wisdom",
            "philosophy quotes",
        ],
        banned_phrases=[
            "level up",
            "hustle",
            "grind",
            "game changer",
            "crush it",
            "unleash",
            "transform",
            "unlock your potential",
            "hack",
            "optimize",
            "mindset shift",
            "you got this",
            "let's go",
            "drop a comment",
            "smash that like button",
            "in conclusion",
            "as we can see",
            "this teaches us",
            "Marcus Aurelius wrote",
            "Marcus Aurelius said",
            "today's quote",
            "as the quote says",
        ],
        entry_angles=[
            "Open like a private letter to one person who is carrying something heavy.",
            "Open with a quiet truth from Arthur's own life and loss.",
            "Open with what Arthur has watched happen to good people over time.",
            "Open by naming the gap between intention and daily action.",
            "Open with the feeling of time passing faster than expected.",
            "Open in a reflective evening tone with one precise observation.",
            "Open with one hard thing Arthur wished he learned earlier.",
            "Open by calmly naming what the viewer is avoiding.",
            "Open with a line that feels like grandfatherly concern, not lecture.",
            "Open with one direct sentence that makes the viewer feel seen.",
        ],
        temperature=0.88,
        voice_id=os.getenv("ARTHUR_ELEVENLABS_VOICE_ID") or os.getenv("ELEVENLABS_VOICE_ID"),
        avatar_id=None,
        seo_base_tags=["stoicism", "philosophy", "wisdom", "ancientwisdom"],
    ),
    "tony": PersonaConfig(
        name="tony",
        display_name="Tony",
        description="High-energy fitness motivator focused on gym mindset and transformation.",
        voice_style="Energetic, direct, punchy, action-oriented, conversational and commanding.",
        content_focus="Workout motivation, gym mindset, health optimization, recovery, consistency.",
        topic_keywords=[
            "fitness",
            "workout motivation",
            "gym mindset",
            "training psychology",
            "recovery",
            "nutrition",
        ],
        topic_queries=[
            "workout motivation quotes",
            "gym mindset lessons",
            "fitness psychology wisdom",
            "training mindset quotes",
        ],
        banned_phrases=[
            "just believe in yourself",
            "no pain no gain",
            "beast mode",
            "grind",
            "hustle",
            "game changer",
            "you got this",
            "nothing is impossible",
        ],
        entry_angles=[
            "Gym floor realization",
            "Injury comeback story",
            "Nutrition myth buster",
            "Training technique insight",
            "Mindset breakthrough",
            "Workout psychology lesson",
            "Body transformation lesson",
            "Recovery wisdom",
            "Beginner mistake learned",
            "Advanced training secret",
        ],
        temperature=0.92,
        voice_id=os.getenv("TONY_ELEVENLABS_VOICE_ID"),
        avatar_id=None,
        seo_base_tags=["fitness", "gym", "workout", "motivation", "fitnessmotivation", "training"],
    ),
}


def get_persona(persona: str | None) -> PersonaConfig:
    key = (persona or "arthur").strip().lower()
    return PERSONAS.get(key, PERSONAS["arthur"])


def list_persona_keys() -> List[str]:
    return sorted(PERSONAS.keys())
