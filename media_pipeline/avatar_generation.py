from __future__ import annotations

from typing import Dict, Optional

from winning_wisdom_ai.config.personas import get_persona


def generate_avatar_video(
    audio_path: str,
    script_id: Optional[str] = None,
    persona: str = "arthur",
) -> Dict[str, str]:
    """
    Minimal avatar generation placeholder that selects persona-specific avatar IDs.

    Hook this function into HeyGen/D-ID API calls in your environment.
    """
    persona_cfg = get_persona(persona)
    run_id = script_id or "winning_wisdom"
    return {
        "run_id": run_id,
        "audio_path": audio_path,
        "persona": persona_cfg.name,
        "avatar_id": persona_cfg.avatar_id,
        "status": "configured",
    }
