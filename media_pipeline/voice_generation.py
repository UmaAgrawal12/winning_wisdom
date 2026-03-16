from pathlib import Path
from typing import Optional

from integrations.elevenlabs_api import generate_voice


def generate_voice_for_script(script_text: str, script_id: Optional[str] = None) -> str:
    """
    Orchestrate voice generation for a script.

    Returns a normalized audio file path (string).
    """
    prefix = script_id or "winning_wisdom"
    return generate_voice(script_text=script_text, filename_prefix=prefix)



