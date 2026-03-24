import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")  # configure Arthur's voice here

MEDIA_ROOT = Path("media/audio")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def generate_voice(
    script_text: str,
    filename_prefix: Optional[str] = None,
    voice_id: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.8,
) -> str:
    """
    Generate an audio file for the given script text using ElevenLabs.

    Returns the path to the saved audio file (relative to project root).
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY is not set in .env")
    selected_voice_id = (voice_id or ELEVENLABS_VOICE_ID or "").strip()
    if not selected_voice_id:
        raise ValueError("ELEVENLABS_VOICE_ID is not set in .env")

    text = (script_text or "").strip()
    if not text:
        raise ValueError("script_text is empty; cannot generate voice.")

    # Basic filename derived from prefix or first words of script
    base_name = filename_prefix or text[:40].replace(" ", "_").replace("\n", "_")
    output_path = MEDIA_ROOT / f"{base_name}.mp3"

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{selected_voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(response.content)

    return str(output_path)



