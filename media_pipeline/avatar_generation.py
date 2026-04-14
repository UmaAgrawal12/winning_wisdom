from __future__ import annotations

import hashlib
import os
import random
from copy import deepcopy
from pathlib import Path
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

from agents.prompt_agent import generate_heygen_prompt
from config.personas import get_persona

_ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY")
HEYGEN_API_BASE = os.getenv("HEYGEN_API_BASE", "https://api.heygen.com")
HEYGEN_DEFAULT_VOICE_ID = os.getenv("HEYGEN_VOICE_ID")
HEYGEN_DEFAULT_AVATAR_ID = os.getenv("HEYGEN_AVATAR_ID")
ARTHUR_HEYGEN_VOICE_ID = os.getenv("ARTHUR_HEYGEN_VOICE_ID")
TONY_HEYGEN_VOICE_ID = os.getenv("TONY_HEYGEN_VOICE_ID")
# studio = POST /v2/video/generate (talking_photo_id or studio avatar_id)
# avatar_iv = POST /v2/videos (flat body; needs HeyGen "avatar_id", not talking_photo_id)
HEYGEN_VIDEO_MODE = (os.getenv("HEYGEN_VIDEO_MODE") or "studio").strip().lower()
# For studio mode only: talking_photo | avatar
HEYGEN_CHARACTER_TYPE = (os.getenv("HEYGEN_CHARACTER_TYPE") or "talking_photo").strip().lower()
ARTHUR_HEYGEN_CHARACTER_TYPE = (os.getenv("ARTHUR_HEYGEN_CHARACTER_TYPE") or "avatar").strip().lower()
TONY_HEYGEN_CHARACTER_TYPE = (os.getenv("TONY_HEYGEN_CHARACTER_TYPE") or HEYGEN_CHARACTER_TYPE).strip().lower()
HEYGEN_SEND_DYNAMIC_PROMPT = (os.getenv("HEYGEN_SEND_DYNAMIC_PROMPT") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HEYGEN_USE_PROMPT_AGENT = (os.getenv("HEYGEN_USE_PROMPT_AGENT") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HEYGEN_PROMPT_DETERMINISTIC = (os.getenv("HEYGEN_PROMPT_DETERMINISTIC") or "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
HEYGEN_PROMPT_DEBUG = (os.getenv("HEYGEN_PROMPT_DEBUG") or "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _preview(value: object, limit: int = 700) -> str:
    text = str(value or "")
    return text if len(text) <= limit else text[:limit] + "...<truncated>"


def _print_video_trace(stage: str, **fields: object) -> None:
    if not HEYGEN_PROMPT_DEBUG:
        return
    print(f"\n[VIDEO_TRACE] stage={stage}")
    for key, value in fields.items():
        print(f"{key}={_preview(value)}")
    print("[/VIDEO_TRACE]\n")


BASE_REALISM_RULES = (
    "Create a photorealistic short-form talking-head reel. "
    "Precise natural lip-sync with provided audio. "
    "Natural skin texture and soft facial detail; avoid plastic smoothing. "
    "Avoid robotic mouth movement and exaggerated expressions. "
    "Keep subtle natural imperfections and vertical composition optimized for 9:16. "
    "Maintain medium-to-waist-up framing frequently enough that forearms and hands can appear naturally. "
    "Use restrained but visible conversational hand gestures and subtle torso sway; avoid frozen shoulders-only framing."
)

CAMERA_BASE = {
    "framing": "medium close-up to waist-up mix with periodic hand visibility",
    "lens": "50mm",
    "composition": "slightly off-center",
    "depth": "shallow depth of field",
}

LIGHTING_BASE = {
    "direction": "window light from left",
    "type": "soft cinematic",
    "contrast": "subject brighter than background",
}

IDENTITY_STATIC = {
    "face_structure": "keep face geometry fully consistent across frames",
    "hair": "keep hairstyle stable with only minimal micro movement",
    "clothing": "keep same wardrobe texture and color with no frame flicker",
    "voice_face_match": "preserve consistent voice-face identity for the persona",
}

PERSONA_TONE_POOL = {
    "arthur": [
        "calm mentor, wise, deliberate, composed, warm authority",
        "steady father-figure guidance, reflective and grounded",
        "measured, reassuring, dignified, quietly confident",
    ],
    "tony": [
        "sharp strategist, direct, modern, persuasive, controlled confidence",
        "evidence-driven coach energy, clear and assertive",
        "focused, practical, concise authority with calm delivery",
    ],
}

SCENE_POOL = {
    "arthur": [
        "private lounge with warm ambient practical lights and layered background depth",
        "window-side setup with neutral professional background and subtle daylight parallax",
        "modern office with soft window light and practical lamp depth cues",
        "luxury car interior with realistic daylight reflections and moving depth highlights",
    ],
    "tony": [
        "modern office with soft window light",
        "window-side setup with neutral professional background",
        "luxury car interior with realistic daylight reflections",
        "private lounge with warm ambient practical lights",
    ],
}

CAMERA_BEHAVIOR_POOL = {
    "arthur": [
        "mostly locked frame with natural micro movement and occasional reframe",
        "subtle cinematic push-in followed by hold",
        "very mild lateral drift with stable subject lock",
    ],
    "tony": [
        "subtle cinematic push-in",
        "locked tripod with micro movement realism",
        "slight handheld drift (very mild)",
    ],
}

GESTURE_PROFILE_POOL = {
    "arthur": [
        "low",
        "medium",
        "expressive but restrained",
    ],
    "tony": [
        "medium",
        "expressive but restrained",
        "low",
    ],
}

ENERGY_PROFILE_POOL = {
    "arthur": [
        "reflective",
        "direct",
        "urgent",
    ],
    "tony": [
        "direct",
        "urgent",
        "reflective",
    ],
}


def _stable_seed(*parts: str) -> int:
    raw = "|".join(parts).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()[:16]
    return int(digest, 16)


def _pool_for_persona(pool: dict, persona: str, fallback: str = "arthur") -> list[str]:
    p = (persona or fallback).strip().lower()
    return pool.get(p) or pool.get(fallback) or []


def _character_type_for_persona(persona: str) -> str:
    p = (persona or "arthur").strip().lower()
    if p == "arthur":
        return ARTHUR_HEYGEN_CHARACTER_TYPE if ARTHUR_HEYGEN_CHARACTER_TYPE in {"avatar", "talking_photo"} else "avatar"
    if p == "tony":
        return TONY_HEYGEN_CHARACTER_TYPE if TONY_HEYGEN_CHARACTER_TYPE in {"avatar", "talking_photo"} else HEYGEN_CHARACTER_TYPE
    return HEYGEN_CHARACTER_TYPE if HEYGEN_CHARACTER_TYPE in {"avatar", "talking_photo"} else "talking_photo"


def _camera_base_text() -> str:
    return (
        f"{CAMERA_BASE['framing']} framing, {CAMERA_BASE['composition']} composition, "
        f"{CAMERA_BASE['lens']} lens feel, {CAMERA_BASE['depth']}"
    )


def _lighting_base_text() -> str:
    return (
        f"{LIGHTING_BASE['direction']}, {LIGHTING_BASE['type']} lighting, "
        f"{LIGHTING_BASE['contrast']}"
    )


def _identity_static_text() -> str:
    return (
        f"{IDENTITY_STATIC['face_structure']}; "
        f"{IDENTITY_STATIC['hair']}; "
        f"{IDENTITY_STATIC['clothing']}; "
        f"{IDENTITY_STATIC['voice_face_match']}"
    )


def analyze_script_dynamics(script_text: str) -> str:
    lines = [ln.strip() for ln in (script_text or "").splitlines() if ln.strip()]
    if not lines:
        return "normal"
    short_lines = sum(1 for ln in lines if len(ln.split()) < 8)
    has_exclaim = "!" in script_text
    if short_lines > len(lines) * 0.5:
        return "high_pause"
    if has_exclaim:
        return "high_energy"
    return "normal"


def _enforce_coherence(persona: str, energy: str, camera_behavior: str) -> tuple[str, str]:
    p = (persona or "").lower()
    if p == "arthur" and energy == "urgent":
        return "direct", "subtle cinematic push-in"
    if p == "arthur" and camera_behavior == "slight handheld drift (very mild)":
        return energy if energy != "urgent" else "direct", "locked tripod with micro movement realism"
    if p == "tony" and energy == "reflective" and camera_behavior == "subtle cinematic push-in":
        return "direct", "locked tripod with micro movement realism"
    return energy, camera_behavior


def _delivery_style_for_script(script_text: str) -> str:
    mode = analyze_script_dynamics(script_text)
    if mode == "high_pause":
        return "pause-driven delivery with clean thought breaks and restrained gesture timing"
    if mode == "high_energy":
        return "assertive pacing with controlled emphasis and tighter gesture cadence"
    return "balanced conversational pacing with natural pauses and semantic emphasis"


def _micro_expression_style(script_text: str, energy_profile: str) -> str:
    mode = analyze_script_dynamics(script_text)
    if energy_profile == "urgent" or mode == "high_energy":
        return "active eyebrow emphasis, tighter blink rhythm, controlled cheek movement on stressed words"
    if mode == "high_pause":
        return "measured eyebrow lifts, natural blink spacing, subtle micro-smile only at resolution beats"
    return "natural eyebrow movement, conversational blink cadence, restrained cheek and eye-squint emphasis"


def _compose_natural_fallback_prompt(
    script_text: str,
    identity_static: str,
    camera_base: str,
    lighting_base: str,
    delivery_style: str,
    micro_expression_style: str,
    persona_tone: str,
    scene: str,
    camera_behavior: str,
    gesture_profile: str,
    energy_profile: str,
) -> str:
    movement_layer = (
        "For realism, keep upper-body movement alive: include natural posture shifts, subtle shoulder breathing, "
        "and controlled hand gestures aligned to emphasis words. Ensure forearms/hands enter frame in a believable cadence "
        "instead of a static portrait lock."
    )
    return (
        "Generate a photorealistic short-form talking-head reel with precise natural lip-sync, "
        "natural skin texture, and subtle real-world imperfections suitable for vertical 9:16 output. "
        f"Identity anchors must remain stable ({identity_static}). "
        f"Keep the on-camera presence {persona_tone}, place the subject in {scene}, and use {camera_behavior} "
        f"while preserving static camera base ({camera_base}) and static lighting base ({lighting_base}). "
        f"Body language should stay {gesture_profile}, delivery energy should feel {energy_profile}, and motion should remain "
        f"human with natural blinking, micro head movement, a {delivery_style}, and {micro_expression_style}. "
        f"{movement_layer} "
        f"Use this script exactly as spoken content: {script_text.strip()}"
    )


def build_dynamic_reel_prompt(
    script_text: str,
    persona: str = "arthur",
    script_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Build a non-static HeyGen instruction prompt using 5 dynamic blocks.
    The selection is deterministic per script/persona/script_id so retries stay stable.
    """
    p = (persona or "arthur").strip().lower()
    tone_pool = _pool_for_persona(PERSONA_TONE_POOL, p)
    scene_pool = _pool_for_persona(SCENE_POOL, p)
    camera_pool = _pool_for_persona(CAMERA_BEHAVIOR_POOL, p)
    gesture_pool = _pool_for_persona(GESTURE_PROFILE_POOL, p)
    energy_pool = _pool_for_persona(ENERGY_PROFILE_POOL, p)
    if HEYGEN_PROMPT_DETERMINISTIC:
        seed = _stable_seed(p, script_id or "", (script_text or "").strip()[:240])
        rng = random.Random(seed)
    else:
        # Non-deterministic by default so repeated requests don't produce identical prompts.
        rng = random.SystemRandom()

    persona_tone = rng.choice(tone_pool)
    scene_seed = _stable_seed(p, (script_text or "").strip()[:240], "scene")
    scene = scene_pool[scene_seed % len(scene_pool)]
    camera_behavior = rng.choice(camera_pool)
    gesture_profile = rng.choice(gesture_pool)
    energy_profile = rng.choice(energy_pool)
    energy_profile, camera_behavior = _enforce_coherence(p, energy_profile, camera_behavior)
    delivery_style = _delivery_style_for_script(script_text)
    micro_expression_style = _micro_expression_style(script_text, energy_profile)
    identity_static = _identity_static_text()
    camera_base = _camera_base_text()
    lighting_base = _lighting_base_text()

    fallback_prompt = _compose_natural_fallback_prompt(
        script_text=(script_text or "").strip(),
        identity_static=identity_static,
        camera_base=camera_base,
        lighting_base=lighting_base,
        delivery_style=delivery_style,
        micro_expression_style=micro_expression_style,
        persona_tone=persona_tone,
        scene=scene,
        camera_behavior=camera_behavior,
        gesture_profile=gesture_profile,
        energy_profile=energy_profile,
    )
    prompt = fallback_prompt
    prompt_source = "fallback"
    prompt_agent_error = ""
    if HEYGEN_USE_PROMPT_AGENT:
        try:
            agent_prompt = generate_heygen_prompt(
                script_text=(script_text or "").strip(),
                persona=p,
                base_realism_rules=BASE_REALISM_RULES,
                identity_static=identity_static,
                camera_base=camera_base,
                lighting_base=lighting_base,
                delivery_style=delivery_style,
                micro_expression_style=micro_expression_style,
                persona_tone=persona_tone,
                scene=scene,
                camera_behavior=camera_behavior,
                gesture_profile=gesture_profile,
                energy_profile=energy_profile,
                # Avoid duplicate terminal output: outer HEYGEN_PROMPT_DEBUG already prints the final prompt.
                echo=False if HEYGEN_PROMPT_DEBUG else None,
            )
            if agent_prompt:
                prompt = agent_prompt
                prompt_source = "agent"
        except Exception as exc:
            # Keep generation resilient even when LLM prompt-writing fails.
            prompt = fallback_prompt
            prompt_source = "fallback"
            prompt_agent_error = f"prompt_agent_call_failed: {str(exc)[:220]}"
    result = {
        "prompt": prompt,
        "fallback_prompt": fallback_prompt,
        "prompt_source": prompt_source,
        "prompt_agent_error": prompt_agent_error,
        "persona_tone": persona_tone,
        "identity_static": identity_static,
        "camera_base": camera_base,
        "lighting_base": lighting_base,
        "delivery_style": delivery_style,
        "micro_expression_style": micro_expression_style,
        "scene": scene,
        "camera_behavior": camera_behavior,
        "gesture_profile": gesture_profile,
        "energy_profile": energy_profile,
    }
    if HEYGEN_PROMPT_DEBUG:
        print("\n[HEYGEN_PROMPT] build_dynamic_reel_prompt")
        print(f"persona={p} script_id={script_id or ''}")
        print(f"source={prompt_source} error={prompt_agent_error}")
        print(
            "blocks="
            f"tone={persona_tone} | scene={scene} | camera={camera_behavior} | "
            f"gesture={gesture_profile} | energy={energy_profile}"
        )
        print(result["prompt"])
        print("[/HEYGEN_PROMPT]\n")
    return result


def _get_persona_voice_id(persona: str) -> Optional[str]:
    if persona == "tony":
        return TONY_HEYGEN_VOICE_ID or HEYGEN_DEFAULT_VOICE_ID
    return ARTHUR_HEYGEN_VOICE_ID or HEYGEN_DEFAULT_VOICE_ID


def _heygen_error_message(data: object) -> str:
    if not isinstance(data, dict):
        return str(data)
    err = data.get("error")
    if isinstance(err, dict):
        return str(err.get("message") or err.get("detail") or err)
    if err:
        return str(err)
    return str(data)


def _raise_for_heygen_response(response: requests.Response) -> dict:
    try:
        data = response.json() if response.content else {}
    except Exception:
        response.raise_for_status()
        return {}
    if not response.ok:
        raise RuntimeError(_heygen_error_message(data) or response.reason or f"HTTP {response.status_code}")
    err = data.get("error")
    if err and not data.get("data"):
        raise RuntimeError(_heygen_error_message(data))
    return data


def _submit_with_prompt_fallback(
    url: str,
    headers: dict,
    payload: dict,
    payload_without_prompt: Optional[dict] = None,
) -> tuple[dict, bool]:
    """
    Submit once with prompt fields. If HeyGen rejects prompt-related fields,
    retry without those fields so generation still succeeds.
    """
    response = requests.post(url, headers=headers, json=payload, timeout=60)
    try:
        return _raise_for_heygen_response(response), True
    except RuntimeError as first_err:
        if not payload_without_prompt:
            raise
        msg = str(first_err).lower()
        prompt_rejected = any(
            token in msg
            for token in (
                "unknown field",
                "invalid parameter",
                "invalid field",
                "unrecognized",
                "schema",
                "bad request",
            )
        )
        if not prompt_rejected:
            raise
        retry_resp = requests.post(url, headers=headers, json=payload_without_prompt, timeout=60)
        return _raise_for_heygen_response(retry_resp), False


def create_heygen_video(
    script_text: str,
    persona: str = "arthur",
    script_id: Optional[str] = None,
    aspect_ratio: str = "9:16",
    *,
    external_audio_url: Optional[str] = None,
    generation_prompt_override: Optional[str] = None,
) -> Dict[str, str]:
    """
    Submit a HeyGen generation job using talking photo avatar + HeyGen TTS,
    or (studio mode) lip-sync from an external audio URL (e.g. ElevenLabs).
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY is not set in .env")

    persona_cfg = get_persona(persona)
    avatar_id = (persona_cfg.avatar_id or HEYGEN_DEFAULT_AVATAR_ID or "").strip()
    if not avatar_id:
        raise ValueError(
            f"No HeyGen avatar configured for persona: {persona_cfg.name}. "
            "Set ARTHUR_HEYGEN_AVATAR_ID / TONY_HEYGEN_AVATAR_ID or HEYGEN_AVATAR_ID in .env."
        )

    use_external_audio = bool((external_audio_url or "").strip())
    if use_external_audio and HEYGEN_VIDEO_MODE == "avatar_iv":
        raise ValueError(
            "Custom audio (ElevenLabs) requires HEYGEN_VIDEO_MODE=studio "
            "(POST /v2/video/generate with talking_photo or studio avatar)."
        )

    voice_id: Optional[str] = None
    if not use_external_audio:
        voice_id = _get_persona_voice_id(persona_cfg.name)
        if not voice_id:
            raise ValueError(
                "No HeyGen voice configured. Set HEYGEN_VOICE_ID or persona-specific HEYGEN voice ID."
            )

    text = (script_text or "").strip()
    if not text:
        raise ValueError("script_text is empty")

    if (generation_prompt_override or "").strip():
        o = generation_prompt_override.strip()
        built = build_dynamic_reel_prompt(
            script_text=text,
            persona=persona_cfg.name,
            script_id=script_id,
        )
        dynamic_prompt = {
            **built,
            "prompt": o,
            "fallback_prompt": o,
            "prompt_source": "client",
            "prompt_agent_error": "",
        }
    else:
        dynamic_prompt = build_dynamic_reel_prompt(
            script_text=text,
            persona=persona_cfg.name,
            script_id=script_id,
        )
    requested_ar = aspect_ratio or "9:16"
    ar = "9:16"
    _print_video_trace(
        "create_heygen_video.input",
        persona=persona_cfg.name,
        script_id=script_id or "",
        requested_aspect_ratio=requested_ar,
        aspect_ratio=ar,
        use_external_audio=use_external_audio,
        external_audio_url=(external_audio_url or "").strip(),
        prompt_source=dynamic_prompt.get("prompt_source", ""),
        generation_prompt=dynamic_prompt.get("prompt", ""),
        script_text=text,
    )
    headers = {
        "x-api-key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    base = HEYGEN_API_BASE.rstrip("/")

    if HEYGEN_VIDEO_MODE == "avatar_iv":
        # Photo / Avatar IV quick create — requires a real avatar_id from HeyGen (not talking_photo_id).
        payload = {
            "avatar_id": avatar_id,
            "voice_id": voice_id,
            "script": text,
            "title": script_id or f"{persona_cfg.name}_video",
            "aspect_ratio": ar,
        }
        payload_without_prompt = deepcopy(payload)
        if HEYGEN_SEND_DYNAMIC_PROMPT:
            payload["prompt"] = dynamic_prompt["prompt"]
        if HEYGEN_PROMPT_DEBUG:
            print("\n[HEYGEN_SUBMIT] endpoint=/v2/videos")
            print(f"persona={persona_cfg.name} prompt_source={dynamic_prompt.get('prompt_source')}")
            print(f"script={text}")
            print(f"prompt={payload.get('prompt','')}")
            print("[/HEYGEN_SUBMIT]\n")

        data, prompt_applied = _submit_with_prompt_fallback(
            url=f"{base}/v2/videos",
            headers=headers,
            payload=payload,
            payload_without_prompt=payload_without_prompt if HEYGEN_SEND_DYNAMIC_PROMPT else None,
        )
        _print_video_trace(
            "create_heygen_video.response",
            endpoint="/v2/videos",
            prompt_applied=prompt_applied,
            raw_response=data,
        )
        code = data.get("code")
        if code is not None and str(code).strip() != "100":
            raise RuntimeError(f"HeyGen API error (code {code}): {data.get('message') or data}")

        inner = data.get("data") if isinstance(data.get("data"), dict) else data
        video_id = (
            (inner or {}).get("video_id")
            or (inner or {}).get("id")
            or data.get("video_id")
            or data.get("id")
        )
    else:
        # Default: AI Studio — supports talking_photo_id (and studio avatar_id).
        character_type = _character_type_for_persona(persona_cfg.name)
        if character_type == "avatar":
            character = {"type": "avatar", "avatar_id": avatar_id}
        else:
            character = {"type": "talking_photo", "talking_photo_id": avatar_id}
        if use_external_audio:
            au = (external_audio_url or "").strip()
            voice_obj: dict = {"type": "audio", "audio_url": au}
        else:
            voice_obj = {
                "type": "text",
                "input_text": text,
                "voice_id": voice_id,
            }
        payload = {
            "title": script_id or f"{persona_cfg.name}_video",
            "aspect_ratio": ar,
            "video_inputs": [
                {
                    "character": character,
                    "voice": voice_obj,
                }
            ],
        }
        payload_without_prompt = deepcopy(payload)
        if HEYGEN_SEND_DYNAMIC_PROMPT:
            payload["video_inputs"][0]["character"]["prompt"] = dynamic_prompt["prompt"]
        if HEYGEN_PROMPT_DEBUG:
            print("\n[HEYGEN_SUBMIT] endpoint=/v2/video/generate")
            print(f"persona={persona_cfg.name} prompt_source={dynamic_prompt.get('prompt_source')}")
            print(f"script={text}")
            print(f"prompt={payload['video_inputs'][0]['character'].get('prompt','')}")
            print("[/HEYGEN_SUBMIT]\n")

        data, prompt_applied = _submit_with_prompt_fallback(
            url=f"{base}/v2/video/generate",
            headers=headers,
            payload=payload,
            payload_without_prompt=payload_without_prompt if HEYGEN_SEND_DYNAMIC_PROMPT else None,
        )
        _print_video_trace(
            "create_heygen_video.response",
            endpoint="/v2/video/generate",
            prompt_applied=prompt_applied,
            raw_response=data,
        )
        inner = data.get("data") if isinstance(data.get("data"), dict) else {}
        video_id = inner.get("video_id") or data.get("video_id")

    if not video_id:
        raise RuntimeError(
            f"HeyGen response missing video id: {data}. "
            "If you see 'look not found' or 'avatar not found', open HeyGen → Avatars, "
            "then set IDs from List Avatars API (GET /v2/avatars) — talking_photo_id vs avatar_id differ."
        )
    return {
        "video_id": video_id,
        "status": "submitted",
        "persona": persona_cfg.name,
        "generation_prompt": dynamic_prompt["prompt"],
        "prompt_applied": prompt_applied,
        "prompt_source": dynamic_prompt.get("prompt_source", "fallback"),
        "prompt_agent_error": dynamic_prompt.get("prompt_agent_error", ""),
        "prompt_blocks": {
            "persona_tone": dynamic_prompt["persona_tone"],
            "identity_static": dynamic_prompt["identity_static"],
            "camera_base": dynamic_prompt["camera_base"],
            "lighting_base": dynamic_prompt["lighting_base"],
            "delivery_style": dynamic_prompt["delivery_style"],
            "micro_expression_style": dynamic_prompt["micro_expression_style"],
            "scene": dynamic_prompt["scene"],
            "camera_behavior": dynamic_prompt["camera_behavior"],
            "gesture_profile": dynamic_prompt["gesture_profile"],
            "energy_profile": dynamic_prompt["energy_profile"],
        },
    }


def get_heygen_video_status(video_id: str) -> Dict[str, str]:
    """
    Fetch HeyGen video generation status + resulting URL when available.
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY is not set in .env")
    headers = {
        "x-api-key": HEYGEN_API_KEY,
        "Accept": "application/json",
    }
    response = requests.get(
        f"{HEYGEN_API_BASE.rstrip('/')}/v1/video_status.get",
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
