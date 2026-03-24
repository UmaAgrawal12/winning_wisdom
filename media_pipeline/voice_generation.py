from pathlib import Path
from typing import Optional

try:
    # When running from `winning_wisdom_ai/` as the working directory
    from integrations.elevenlabs_api import generate_voice
except ModuleNotFoundError:
    # When importing as a package (e.g., uvicorn winning_wisdom_ai.app:app)
    from winning_wisdom_ai.integrations.elevenlabs_api import generate_voice
from winning_wisdom_ai.config.personas import get_persona


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
    # Tone tuning per persona for better delivery.
    stability = 0.62 if persona_cfg.name == "arthur" else 0.38
    similarity_boost = 0.82 if persona_cfg.name == "arthur" else 0.76
    return generate_voice(
        script_text=script_text,
        filename_prefix=prefix,
        voice_id=persona_cfg.voice_id,
        stability=stability,
        similarity_boost=similarity_boost,
    )



