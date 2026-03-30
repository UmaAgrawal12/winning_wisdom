import os
from pathlib import Path
from typing import Optional
import wave

import requests
from dotenv import load_dotenv

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")  # configure Arthur's voice here

MEDIA_ROOT = Path("media/audio")
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)


def _write_silent_wav(output_path: Path, seconds: float = 2.0, sample_rate: int = 16000) -> None:
    """
    Create a tiny local fallback audio file when ElevenLabs is not configured.
    """
    n_frames = max(1, int(sample_rate * max(0.5, seconds)))
    silence = b"\x00\x00" * n_frames  # 16-bit mono PCM
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(silence)


def generate_voice(
    script_text: str,
    filename_prefix: Optional[str] = None,
    voice_id: Optional[str] = None,
    stability: float = 0.5,
    similarity_boost: float = 0.8,
) -> str:
    """
    Generate an audio file for the given script text.

    Uses ElevenLabs when API key + voice id are configured.
    Falls back to a local silent WAV file otherwise.

    Returns the saved audio path (relative to project root).
    """
    text = (script_text or "").strip()
    if not text:
        raise ValueError("script_text is empty; cannot generate voice.")

    # Basic filename derived from prefix or first words of script
    base_name = filename_prefix or text[:40].replace(" ", "_").replace("\n", "_")
    selected_voice_id = (voice_id or ELEVENLABS_VOICE_ID or "").strip()

    if not ELEVENLABS_API_KEY or not selected_voice_id:
        output_path = MEDIA_ROOT / f"{base_name}.wav"
        # Roughly map words to duration so the timeline feels realistic in UI.
        words = len(text.split())
        seconds = min(12.0, max(2.0, words / 2.8))
        _write_silent_wav(output_path, seconds=seconds)
        return str(output_path)

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



