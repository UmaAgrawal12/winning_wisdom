from pathlib import Path
from typing import Optional

from integrations.elevenlabs_api import generate_voice
from config.personas import get_persona


def generate_voice_for_script(
    script_text: str,
    script_id: Optional[str] = None,
    persona: str = "arthur",
) -> str:
    """
    Orchestrate voice generation for a script.

    Returns a normalized audio file path (string).
    """
    prefix = script_id or "winning_wisdom"
    persona_cfg = get_persona(persona)
    # Arthur: warm baritone, measured pauses. Tony: calm evidence coach.
    stability = 0.66 if persona_cfg.name == "arthur" else 0.55
    similarity_boost = 0.83 if persona_cfg.name == "arthur" else 0.80
    return generate_voice(
        script_text=script_text,
        filename_prefix=prefix,
        voice_id=persona_cfg.voice_id,
        stability=stability,
        similarity_boost=similarity_boost,
    )



