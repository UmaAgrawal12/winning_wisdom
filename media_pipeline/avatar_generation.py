from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

from config.personas import get_persona

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_API_BASE = os.getenv("HEYGEN_API_BASE", "https://api.heygen.com")
HEYGEN_DEFAULT_VOICE_ID = os.getenv("HEYGEN_VOICE_ID")
ARTHUR_HEYGEN_VOICE_ID = os.getenv("ARTHUR_HEYGEN_VOICE_ID")
TONY_HEYGEN_VOICE_ID = os.getenv("TONY_HEYGEN_VOICE_ID")


def _get_persona_voice_id(persona: str) -> Optional[str]:
    if persona == "tony":
        return TONY_HEYGEN_VOICE_ID or HEYGEN_DEFAULT_VOICE_ID
    return ARTHUR_HEYGEN_VOICE_ID or HEYGEN_DEFAULT_VOICE_ID


def create_heygen_video(
    script_text: str,
    persona: str = "arthur",
    script_id: Optional[str] = None,
    aspect_ratio: str = "9:16",
) -> Dict[str, str]:
    """
    Submit a HeyGen generation job using talking photo avatar + HeyGen TTS.
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY is not set in .env")

    persona_cfg = get_persona(persona)
    if not persona_cfg.avatar_id:
        raise ValueError(f"No HeyGen avatar configured for persona: {persona_cfg.name}")

    voice_id = _get_persona_voice_id(persona_cfg.name)
    if not voice_id:
        raise ValueError(
            "No HeyGen voice configured. Set HEYGEN_VOICE_ID or persona-specific HEYGEN voice ID."
        )

    text = (script_text or "").strip()
    if not text:
        raise ValueError("script_text is empty")

    payload = {
        "title": script_id or f"{persona_cfg.name}_video",
        "aspect_ratio": aspect_ratio,
        "test": False,
        "video_inputs": [
            {
                "character": {"type": "talking_photo", "talking_photo_id": persona_cfg.avatar_id},
                "voice": {"type": "text", "input_text": text, "voice_id": voice_id},
            }
        ],
    }
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    response = requests.post(
        f"{HEYGEN_API_BASE}/v2/video/generate",
        headers=headers,
        json=payload,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    video_id = (
        data.get("data", {}).get("video_id")
        or data.get("video_id")
        or data.get("id")
    )
    if not video_id:
        raise RuntimeError(f"HeyGen response missing video id: {data}")
    return {"video_id": video_id, "status": "submitted", "persona": persona_cfg.name}


def get_heygen_video_status(video_id: str) -> Dict[str, str]:
    """
    Fetch HeyGen video generation status + resulting URL when available.
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY is not set in .env")
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Accept": "application/json",
    }
    response = requests.get(
        f"{HEYGEN_API_BASE}/v1/video_status.get",
        headers=headers,
        params={"video_id": video_id},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()
    payload = data.get("data", data)
    status = (
        payload.get("status")
        or payload.get("video_status")
        or "unknown"
    ).lower()
    video_url = payload.get("video_url") or payload.get("url")

    # HeyGen errors are commonly nested at payload["error"] with keys like:
    # code, message, detail.
    err = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    error_code = err.get("code") or err.get("error_code") or ""
    error_message = err.get("message") or ""
    error_detail = err.get("detail") or ""

    return {
        "video_id": video_id,
        "status": status,
        "video_url": video_url or "",
        "error_code": error_code,
        "error_message": error_message,
        "error_detail": error_detail,
        "raw": payload,
    }
