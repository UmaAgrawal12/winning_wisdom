from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.responses import JSONResponse
from typing import Optional, Any
from pathlib import Path
import json
import random
import concurrent.futures
from datetime import datetime
import os
import time
import hmac
import hashlib
import base64
import shutil
import subprocess
import uuid

import requests

# Supabase (optional; falls back to local JSON file if not configured)
from supabase_db import (
    is_supabase_configured,
    list_pipeline_runs as sb_list_pipeline_runs,
    list_approved_pipeline_runs as sb_list_approved_pipeline_runs,
    patch_pipeline_run_approvals as sb_patch_pipeline_run_approvals,
    insert_pipeline_run,
)

# Prefer package imports (works when running from project root)
from agents.topic_agent import (
    fetch_winning_wisdom_quote_for_topic,
    generate_topics,
    get_curated_topics,
)
from agents.script_agent import (
    generate_daily_wisdom_script,
    DailyWisdomScript,
    revise_wisdom_script,
    resolve_script_text_by_fingerprint,
    script_fingerprint,
    persist_spoken_script_snapshot,
)
from agents.score_agent import score_reel_script
from agents.seo_agent import generate_seo_metadata, SEOResult
from media_pipeline.voice_generation import generate_voice_for_script
from media_pipeline.avatar_generation import (
    create_heygen_video,
    get_heygen_video_status,
)

from openai import APIError, RateLimitError


def _raise_http_for_llm_error(exc: BaseException) -> None:
    """Map OpenAI-client errors (OpenAI or Gemini OpenAI-compatible API) to HTTP responses."""
    if isinstance(exc, RateLimitError):
        raise HTTPException(
            status_code=429,
            detail=(
                "LLM quota or rate limit exceeded. "
                "Wait and retry; for Gemini see https://ai.dev/rate-limit ; for OpenAI see your dashboard limits. "
                "You can set GEMINI_MODEL_* or OPENAI_MODEL in .env."
            ),
        ) from exc
    if isinstance(exc, APIError):
        raise HTTPException(status_code=503, detail=f"LLM API error: {exc}") from exc
    raise exc


class TopicProposal(BaseModel):
    topic: str
    quote: str
    source: str
    persona: str = "arthur"


class TopicQuoteRequest(BaseModel):
    topic: str
    persona: str = "arthur"


class DailyFullFlowResponse(BaseModel):
    topic: str
    quote: str
    source: str
    script: DailyWisdomScript
    seo: SEOResult


class TopicApproval(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    persona: str = "arthur"


class ScriptApproval(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    approved_script: str
    persona: str = "arthur"


class KeywordRequest(BaseModel):
    keyword: str
    persona: str = "arthur"


class ScriptRevision(BaseModel):
    topic: Optional[str] = None
    quote: str
    source: str
    current_script: str
    suggestions: str
    persona: str = "arthur"


class DailyFlowResponse(BaseModel):
    script: DailyWisdomScript
    score: dict
    seo: SEOResult


class ScriptVoiceRequest(BaseModel):
    script_text: str
    persona: str = "arthur"
    script_id: Optional[str] = None


class ScriptVideoRequest(BaseModel):
    script_text: str
    persona: str = "arthur"
    script_id: Optional[str] = None
    aspect_ratio: str = "9:16"


class ScriptVideoBoundRequest(BaseModel):
    """HeyGen video from ledger script + ElevenLabs file + optional visual prompt."""

    script_fingerprint: str
    audio_path: str
    persona: str = "arthur"
    script_id: Optional[str] = None
    aspect_ratio: str = "9:16"
    generation_prompt: Optional[str] = None


class DemoArthurReelRequest(BaseModel):
    aspect_ratio: str = "9:16"
    approved: bool = False
    approved_prompts: Optional[list[str]] = None


def _seo_for_storage(seo: SEOResult) -> dict:
    """
    Normalize SEO payload so captions are explicitly available in Supabase.
    We keep `description` and also add `caption` for convenience.
    """
    raw = seo.model_dump()
    for platform in ("youtube", "instagram", "tiktok", "facebook"):
        block = raw.get(platform)
        if isinstance(block, dict):
            block["caption"] = block.get("description", "")
    return raw


# Stored pipeline runs live at project root /data
PROJECT_ROOT = Path(__file__).resolve().parent
PIPELINE_RUNS_FILE = PROJECT_ROOT / "data" / "pipeline_runs.json"
MEDIA_AUDIO_DIR = (PROJECT_ROOT / "media" / "audio").resolve()
MEDIA_REELS_DIR = (PROJECT_ROOT / "media" / "reels").resolve()
MEDIA_REELS_DIR.mkdir(parents=True, exist_ok=True)
HEYGEN_REEL_SECTIONS = max(2, int(os.getenv("HEYGEN_REEL_SECTIONS", "3")))
VIDEO_FLOW_DEBUG = (os.getenv("VIDEO_FLOW_DEBUG") or "true").strip().lower() in {"1", "true", "yes", "on"}

ARTHUR_DEMO_SCENES: list[dict[str, str]] = [
    {"line": "You’re feeling it, aren’t you?", "camera": "medium close-up, chest-to-waist framing with hands entering frame", "motion": "slow push-in with subtle inhale", "emotion": "slight knowing smile"},
    {"line": "That weight of choices, lingering.", "camera": "three-quarter medium shot, torso and forearms visible", "motion": "gentle right-to-left drift", "emotion": "thoughtful"},
    {"line": "You take a moment, pause.", "camera": "waist-up locked frame, shoulders and hands visible", "motion": "small lean back and reset", "emotion": "grounded pause"},
    {"line": "Wondering if you’ll act today.", "camera": "medium side angle with eye-line return", "motion": "micro turn then settle", "emotion": "doubt"},
    {"line": "It’s easy to let time slip.", "camera": "medium close-up with practical lamp in background depth", "motion": "soft focus breathing and tiny push-in", "emotion": "reflective"},
    {"line": "Just keep waiting, hoping.", "camera": "waist-up front frame with one restrained hand gesture", "motion": "slow exhale and slight shoulder drop", "emotion": "neutral to slight disappointment"},
    {"line": "But here’s the truth:", "camera": "tight medium shot, direct eye contact", "motion": "intentional push-in beat", "emotion": "turning point"},
    {"line": "Suffer the pain of discipline or suffer the pain of regret.", "camera": "locked medium close-up with hands briefly visible at emphasis words", "motion": "minimal movement, controlled emphasis pause", "emotion": "firm intense"},
    {"line": "Those are not my words; they carry weight.", "camera": "slight zoom-out to include torso and forearm", "motion": "one deliberate open-hand gesture", "emotion": "authority"},
    {"line": "Think of Marcus, who knew action leads.", "camera": "three-quarter medium with depth-rich study background", "motion": "slow lateral drift then hold", "emotion": "reference"},
    {"line": "You are not broken. You are early.", "camera": "warm medium close-up, chest and hands in lower frame", "motion": "micro nod and soft hand settle", "emotion": "reassurance"},
    {"line": "Time will keep walking, my friend.", "camera": "waist-up with practical light and bookshelf depth", "motion": "slight pull back with parallax", "emotion": "time passage"},
    {"line": "Are you ready to walk with it?", "camera": "medium close-up ending on direct eye contact", "motion": "slow push-in then hold on stillness", "emotion": "calm challenge"},
]

ARTHUR_DEMO_PROMPT_OVERRIDES: list[str] = [
    "Arthur photoreal cinematic reel, 9:16, studio avatar. Medium waist-up framing with hands visible in lower frame. Start with calm direct eye contact and one small open-palm gesture in first 2 seconds. Subtle push-in only. Natural blink and breath motion. Burn subtitles in lower-safe area, 3-6 words per chunk, perfectly synced to speech.",
    "Arthur photoreal vertical shot, 9:16. Three-quarter medium frame, torso and forearms visible. Add gentle lateral drift and one restrained counting gesture (two fingers) at emphasis word. Keep delivery reflective, not robotic. Accurate burned subtitles, short chunks, high-contrast text, speech-synced timing.",
    "Arthur realistic studio shot, 9:16. Waist-up framing with visible hands resting then lifting slightly during pause. Motion: tiny lean-back then settle. Natural micro-expressions, subtle head tilt. Subtitle timing must match pauses exactly; do not rush caption changes.",
    "Arthur photoreal medium shot, 9:16. Slight side angle then return to camera, forearm visible during one controlled gesture. Keep shoulders and torso alive with micro sway. Realistic skin texture, no plastic smoothing. Burn subtitles with 4-7 word chunks and clean line breaks.",
    "Arthur cinematic 9:16 with depth-rich background (practical lamp/bookshelf). Medium-close frame, occasional hand-in-frame movement. Add soft focus breathing and tiny push-in. Delivery contemplative with natural silent beat. Subtitles must remain precise and readable, bottom safe zone.",
    "Arthur vertical studio shot, 9:16. Waist-up front frame; include one clear open-hand gesture then hand reset. Slight shoulder drop on emotional word. Keep expression restrained and human. Burned subtitles synchronized word-accurately to spoken rhythm.",
    "Arthur photoreal 9:16, medium close-up with hands briefly visible at emphasis. Intentional push-in during turning-point phrase, then hold. Micro nod and blink timing aligned to meaning. Subtitles short, punchy, timed to phrase stress.",
    "Arthur realistic vertical shot, 9:16. Locked medium frame with torso movement and minimal but deliberate hand gesture on key contrast words. Keep intensity firm without theatrical exaggeration. Subtitle chunks must split at semantic pauses, exact spoken text only.",
    "Arthur cinematic studio, 9:16. Slight zoom-out to reveal torso and forearm. One controlled explanatory hand motion, then neutral posture. Keep delivery warm and grounded, no robotic loops. Burn subtitles with high contrast and stable positioning.",
    "Arthur photoreal 9:16 three-quarter medium shot, rich background depth. Slow lateral drift then hold. Add subtle hand gesture near chest level while referencing historical wisdom. Natural face/eye movement, no frozen look. Subtitles synced tightly to speech cadence.",
    "Arthur warm-toned vertical frame, 9:16. Medium close-up with chest and lower-hand region visible. Soft micro nod and gentle palm-open reassurance gesture. Keep facial emotion authentic and calm. Burn readable subtitles, 3-6 words per line, exact timing.",
    "Arthur realistic studio shot, 9:16. Waist-up frame with subtle pull-back and slight parallax in background practical lights. Include one understated hand movement during time phrase. Human breathing and posture movement required. Subtitle flow must follow pauses naturally.",
    "Arthur photoreal cinematic ending, 9:16. Medium-close framing, direct eye contact, hands briefly visible then still. Slow push-in and final hold on silence beat. No robotic articulation, no static portrait freeze. Burn final subtitles with precise sync and clear end punctuation timing.",
]


def _vpreview(value: Any, limit: int = 700) -> str:
    text = str(value if value is not None else "")
    return text if len(text) <= limit else text[:limit] + "...<truncated>"


def _env_int(name: str, default: int, minimum: int | None = None) -> int:
    raw = str(os.getenv(name, str(default)) or "").strip()
    # Allow accidental annotations like "900 (default is 900)" in .env.
    digits = "".join(ch for ch in raw if ch.isdigit())
    try:
        value = int(digits or str(default))
    except ValueError:
        value = default
    if minimum is not None:
        value = max(minimum, value)
    return value


def _video_trace(stage: str, **fields: Any) -> None:
    if not VIDEO_FLOW_DEBUG:
        return
    print(f"\n[VIDEO_FLOW] stage={stage}")
    for key, value in fields.items():
        print(f"{key}={_vpreview(value)}")
    print("[/VIDEO_FLOW]\n")


HEYGEN_REEL_SECTIONS = _env_int("HEYGEN_REEL_SECTIONS", 3, minimum=2)
HEYGEN_REEL_TIMEOUT_SEC = _env_int("HEYGEN_REEL_TIMEOUT_SEC", 900, minimum=60)


def _heygen_public_audio_url(rel_path: str) -> str:
    """
    HeyGen must fetch audio over the public internet (not localhost).
    Set PUBLIC_APP_URL=https://your-tunnel.example.ngrok-free.app (no trailing slash).
    """
    base = (os.getenv("PUBLIC_APP_URL") or "").strip().rstrip("/")
    if not base:
        raise HTTPException(
            status_code=503,
            detail="Set PUBLIC_APP_URL in .env to an HTTPS base URL reachable by HeyGen "
            "(e.g. ngrok) so it can download /media/audio/... files.",
        )
    norm = rel_path.replace("\\", "/").lstrip("/")
    if ".." in norm:
        raise HTTPException(status_code=400, detail="Invalid audio_path.")
    result = f"{base}/{norm}"
    _video_trace("public_audio_url", rel_path=rel_path, public_url=result)
    return result


def _resolved_media_audio_file(audio_path: str) -> Path:
    raw = (audio_path or "").strip().replace("\\", "/")
    if not raw or ".." in raw or raw.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid audio_path.")
    rel = Path(raw)
    if rel.is_absolute():
        raise HTTPException(status_code=400, detail="Invalid audio_path.")
    full = (PROJECT_ROOT / rel).resolve()
    try:
        full.relative_to(MEDIA_AUDIO_DIR)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="audio_path must point to a file under media/audio/.",
        )
    if not full.is_file():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    _video_trace("audio_path_resolved", input_audio_path=audio_path, resolved_file=str(full))
    return full


def _split_script_into_sections(script_text: str, n_sections: int) -> list[str]:
    lines = [ln.strip() for ln in (script_text or "").splitlines() if ln.strip()]
    if not lines:
        return []
    n = max(1, min(n_sections, len(lines)))
    chunk_size = max(1, (len(lines) + n - 1) // n)
    sections = []
    for i in range(0, len(lines), chunk_size):
        part = "\n".join(lines[i : i + chunk_size]).strip()
        if part:
            sections.append(part)
    out = sections[:n] if len(sections) > n else sections
    _video_trace(
        "split_script",
        requested_sections=n_sections,
        total_lines=len(lines),
        produced_sections=len(out),
        section_1=(out[0] if out else ""),
        section_last=(out[-1] if out else ""),
    )
    return out


def _probe_audio_duration_sec(audio_file: Path) -> float:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise HTTPException(status_code=503, detail="ffprobe not found. Install ffmpeg/ffprobe to build reel output.")
    cmd = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(audio_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise HTTPException(status_code=503, detail=f"ffprobe failed: {proc.stderr.strip() or proc.stdout.strip()}")
    try:
        duration = float((proc.stdout or "0").strip())
        _video_trace("probe_audio_duration", file=str(audio_file), duration_sec=duration)
        return duration
    except ValueError:
        raise HTTPException(status_code=503, detail="Could not parse audio duration from ffprobe output.")


def _split_audio_for_reel(audio_file: Path, n_sections: int) -> list[Path]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(status_code=503, detail="ffmpeg not found. Install ffmpeg to split audio/reel clips.")
    total = _probe_audio_duration_sec(audio_file)
    if total <= 0.1:
        raise HTTPException(status_code=400, detail="Audio duration too short.")
    n = max(1, n_sections)
    span = total / n
    stem = audio_file.stem
    out_dir = MEDIA_AUDIO_DIR / "reel_chunks"
    out_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    for i in range(n):
        start = i * span
        duration = total - start if i == n - 1 else span
        out = out_dir / f"{stem}_part{i+1:02d}_{uuid.uuid4().hex[:8]}.mp3"
        cmd = [
            ffmpeg,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{max(0.25, duration):.3f}",
            "-i",
            str(audio_file),
            "-vn",
            "-acodec",
            "libmp3lame",
            "-q:a",
            "2",
            str(out),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if proc.returncode != 0 or not out.exists():
            raise HTTPException(status_code=503, detail=f"ffmpeg split failed: {proc.stderr.strip() or proc.stdout.strip()}")
        parts.append(out)
    _video_trace(
        "split_audio",
        source_file=str(audio_file),
        sections=n,
        part_files=" | ".join(str(p) for p in parts),
    )
    return parts


def _download_file(url: str, target: Path) -> None:
    _video_trace("download_clip.start", url=url, target=str(target))
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with target.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    _video_trace("download_clip.done", target=str(target), size_bytes=target.stat().st_size if target.exists() else 0)


def _concat_videos_ffmpeg(input_files: list[Path], output_file: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(status_code=503, detail="ffmpeg not found. Install ffmpeg to compose final reel.")
    list_file = output_file.with_suffix(".txt")
    lines = "\n".join(f"file '{p.as_posix()}'" for p in input_files)
    list_file.write_text(lines, encoding="utf-8")
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c:v",
        "libx264",
        "-preset",
        "slow",
        "-crf",
        "18",
        "-maxrate",
        "8M",
        "-bufsize",
        "16M",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_file),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    try:
        list_file.unlink(missing_ok=True)
    except Exception:
        pass
    if proc.returncode != 0 or not output_file.exists():
        raise HTTPException(status_code=503, detail=f"ffmpeg concat failed: {proc.stderr.strip() or proc.stdout.strip()}")
    _video_trace(
        "concat_done",
        inputs=" | ".join(str(p) for p in input_files),
        output=str(output_file),
        output_size_bytes=output_file.stat().st_size if output_file.exists() else 0,
    )


def _wait_heygen_done(video_id: str, timeout_sec: int) -> dict:
    started = time.time()
    while True:
        st = get_heygen_video_status(video_id=video_id)
        state = str(st.get("status") or "").lower()
        _video_trace("heygen_poll_tick", video_id=video_id, status=state, video_url=st.get("video_url", ""))
        if state in ("completed", "success") and str(st.get("video_url") or "").strip():
            return st
        if state in ("failed", "error"):
            raise HTTPException(
                status_code=503,
                detail=f"HeyGen clip failed (video_id={video_id}): {st.get('error_message') or st.get('error_detail') or state}",
            )
        if time.time() - started > timeout_sec:
            raise HTTPException(status_code=504, detail=f"Timed out waiting for HeyGen clip {video_id}.")
        time.sleep(4)


def _arthur_demo_scene_prompt(scene: dict[str, str]) -> str:
    scene_idx = int(scene.get("index", 1))
    total = int(scene.get("total", 1))
    if 1 <= scene_idx <= len(ARTHUR_DEMO_PROMPT_OVERRIDES):
        return ARTHUR_DEMO_PROMPT_OVERRIDES[scene_idx - 1]
    phase = "opening tension" if scene_idx <= max(2, total // 4) else "middle reflection" if scene_idx < total - 2 else "closing resolve"
    schedule = (
        "Shot schedule must not be static: vary composition and movement between clips. "
        "Across sequence use this cadence: establish medium framing, then add drift, then restrained push-ins, "
        "then a calmer lock-off for the final beat."
    )
    return (
        "Arthur photoreal cinematic reel shot. Warm key light 3200-4000K, shallow depth of field, "
        "50mm/85mm look, realistic skin texture, natural micro facial motion, no robotic movement, "
        "no aggressive cuts. Enforce 9:16 vertical composition. "
        f"Sequence phase: {phase}. Scene position: {scene_idx}/{total}. "
        f"{schedule} "
        "Keep gestures visible in frame with occasional forearm/hand presence, never fully static shoulders-only framing. "
        f"Camera framing: {scene['camera']}. "
        f"Motion direction: {scene['motion']}. "
        f"Emotional tone: {scene['emotion']}. "
        "Delivery calm philosophical with a clean pause after each sentence."
    )

FALLBACK_TOPICS = [
    "Discipline on the hard days",
    "Stop waiting for confidence",
    "What you can control today",
    "When motivation disappears",
    "The cost of staying comfortable",
    "Doing the right thing quietly",
    "How to face criticism calmly",
    "The difference between pain and suffering",
]


def _generate_topics_with_timeout(timeout_s: float = 8.0) -> list[str]:
    """
    Try LLM-based topic generation, but never block the UI.
    Falls back to a curated topic list on timeout/error.
    """
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(
                generate_topics,
                theme="Winning Wisdom: discipline, meaning, resilience, self-mastery",
                n=8,
                audience="general_self_improver",
            )
            result = fut.result(timeout=timeout_s)
        topics = getattr(result, "topics", None)
        if isinstance(topics, list) and topics:
            cleaned = [t.strip() for t in topics if isinstance(t, str) and t.strip()]
            if cleaned:
                return cleaned
    except Exception:
        pass

    fallback = FALLBACK_TOPICS.copy()
    random.shuffle(fallback)
    return fallback[:8]



def _load_pipeline_runs() -> list[dict[str, Any]]:
    if not PIPELINE_RUNS_FILE.exists():
        return []
    try:
        with PIPELINE_RUNS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def _save_pipeline_runs(runs: list[dict[str, Any]]) -> None:
    PIPELINE_RUNS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with PIPELINE_RUNS_FILE.open("w", encoding="utf-8") as f:
        json.dump(runs, f, indent=2, ensure_ascii=False)


class RunApprovalPatch(BaseModel):
    topic_approved: Optional[bool] = None
    script_approved: Optional[bool] = None
    final_approved: Optional[bool] = None


class StudioLoginRequest(BaseModel):
    username: str
    password: str


app = FastAPI(title="Winning Wisdom Frontend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MEDIA_DIR = PROJECT_ROOT / "media"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

SESSION_COOKIE = "ww_session"
SESSION_TTL_SEC = int(os.getenv("WW_SESSION_TTL_SEC", "86400"))
SESSION_SECRET = os.getenv("WW_SESSION_SECRET", "winning-wisdom-dev-secret")
STUDIO_USERNAME = os.getenv("WW_STUDIO_USERNAME", "studio")
STUDIO_PASSWORD = os.getenv("WW_STUDIO_PASSWORD", "wisdom")


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _unb64(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _create_session_token(username: str) -> str:
    payload = json.dumps({"u": username, "exp": int(time.time()) + SESSION_TTL_SEC}, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64(payload)
    sig = hmac.new(SESSION_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def _verify_session_token(token: Optional[str]) -> Optional[str]:
    if not token or "." not in token:
        return None
    payload_b64, sig = token.rsplit(".", 1)
    expected = hmac.new(SESSION_SECRET.encode("utf-8"), payload_b64.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        payload = json.loads(_unb64(payload_b64).decode("utf-8"))
    except Exception:
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return str(payload.get("u") or "")


@app.middleware("http")
async def require_studio_session_for_api(request: Request, call_next):
    path = request.url.path
    if request.method == "OPTIONS":
        return await call_next(request)
    if path.startswith("/api/auth/login") or path.startswith("/api/auth/logout"):
        return await call_next(request)
    if path.startswith("/api/"):
        user = _verify_session_token(request.cookies.get(SESSION_COOKIE))
        if not user:
            return JSONResponse({"detail": "Not authenticated"}, status_code=401)
    return await call_next(request)


@app.post("/api/auth/login")
def studio_login(payload: StudioLoginRequest, response: Response):
    if payload.username != STUDIO_USERNAME or payload.password != STUDIO_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = _create_session_token(STUDIO_USERNAME)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_TTL_SEC,
        path="/",
    )
    return {"ok": True, "username": STUDIO_USERNAME}


@app.post("/api/auth/logout")
def studio_logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def studio_auth_me(request: Request):
    user = _verify_session_token(request.cookies.get(SESSION_COOKIE))
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"username": user}


@app.get("/api/topics")
def list_curated_topics(persona: str = "arthur"):
    """All hardcoded topics for the persona (for client topic picker)."""
    result = get_curated_topics(persona=persona, n=None, shuffle=False)
    return {"persona": persona, "topics": result.topics}


@app.get("/api/topic")
def get_topic(persona: str = "arthur"):
    """
    Step 1: Pick a random curated topic and a quote from the hardcoded bank.
    """
    try:
        topics_result = get_curated_topics(persona=persona, n=8, shuffle=True)
        topic = (
            random.choice(topics_result.topics)
            if topics_result.topics
            else "Discipline on the hard days"
        )
        quote_data = fetch_winning_wisdom_quote_for_topic(topic=topic, persona=persona)
        return {
            "topic": topic,
            "quote": quote_data["quote"],
            "source": quote_data["source"],
            "persona": persona,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Topic/quote selection failed: {e}")


@app.post("/api/topic/quote")
def get_quote_for_topic(payload: TopicQuoteRequest) -> TopicProposal:
    """
    Given a topic, fetch a quote aligned to that topic.
    """
    topic = (payload.topic or "").strip()
    try:
        quote_data = fetch_winning_wisdom_quote_for_topic(
            topic=topic,
            persona=payload.persona,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Quote selection failed: {e}")
    return TopicProposal(topic=topic, quote=quote_data["quote"], source=quote_data["source"], persona=payload.persona)


@app.post("/api/topic/approve")
def approve_topic(payload: TopicApproval):
    """
    Step 1b: Approve or override the topic/quote, then preview script.
    """
    try:
        script = generate_daily_wisdom_script(
            quote_override=payload.quote,
            source_override=payload.source,
            persona=payload.persona,
            theme=payload.topic or payload.quote,
        )
        return script
    except (RateLimitError, APIError) as e:
        _raise_http_for_llm_error(e)


@app.get("/api/daily-flow")
def daily_flow(persona: str = "arthur") -> DailyFullFlowResponse:
    """
    End-to-end flow:
    topic -> quote -> script -> SEO
    """
    try:
        topics_result = get_curated_topics(persona=persona, n=8, shuffle=True)
        topic = (
            random.choice(topics_result.topics)
            if topics_result.topics
            else "Discipline on the hard days"
        )
        quote_data = fetch_winning_wisdom_quote_for_topic(topic=topic, persona=persona)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Daily flow topic/quote failed: {e}")

    script = generate_daily_wisdom_script(
        quote_override=quote_data["quote"],
        source_override=quote_data["source"],
        persona=persona,
        theme=topic,
    )

    seo = generate_seo_metadata(
        topic=topic,
        script_text=script.spoken_script.full_script,
        audience="general_self_improver",
        persona=persona,
    )

    return DailyFullFlowResponse(
        topic=topic,
        quote=quote_data["quote"],
        source=quote_data["source"],
        script=script,
        seo=seo,
    )


@app.post("/api/script/approve")
def approve_script(payload: ScriptApproval):
    """
    Step 2: Approve the final script text, then score and generate SEO.
    """
    try:
        # Build a DailyWisdomScript shell (LLM call), then inject the approved text.
        base_script = generate_daily_wisdom_script(
            quote_override=payload.quote,
            source_override=payload.source,
            persona=payload.persona,
            theme=payload.topic or payload.quote,
        )
        base_script.spoken_script.full_script = payload.approved_script
        persist_spoken_script_snapshot(
            payload.persona,
            payload.approved_script,
            quote=payload.quote,
            source=payload.source,
        )

        score = score_reel_script(base_script)
        seo = generate_seo_metadata(
            topic=payload.topic or payload.quote,
            script_text=payload.approved_script,
            audience="general_self_improver",
            persona=payload.persona,
        )

        # If Supabase is configured, persist the approved/scored run so the
        # media generation pipeline can consume it from the DB queue.
        if is_supabase_configured():
            try:
                chosen_topic = (payload.topic or payload.quote or "").strip()
                quality_passed = bool(getattr(score, "overall_score", 0) >= 7)
                priority_fix = getattr(score, "priority_fix", None)
                quality_report = (
                    f"Overall {getattr(score, 'overall_score', '')}/10 - {getattr(score, 'verdict', '')}"
                )
                if priority_fix:
                    quality_report += f" | Priority fix: {priority_fix}"

                insert_pipeline_run(
                    {
                        "chosen_topic": chosen_topic,
                        "script": payload.approved_script,
                        "quality_report": quality_report,
                        "quality_passed": quality_passed,
                        "topic_approved": True,
                        "script_approved": True,
                        "final_approved": True,
                        "seo_result": _seo_for_storage(seo),
                    }
                )
            except Exception:
                # Don't block the UI flow if Supabase write fails; backend will still return script/score/SEO.
                pass

        return {
            "script": base_script,
            "score": score.dict(),
            "seo": seo,
        }
    except (RateLimitError, APIError) as e:
        _raise_http_for_llm_error(e)


@app.post("/api/script/from-keyword")
def script_from_keyword(payload: KeywordRequest) -> DailyWisdomScript:
    """
    Generate a fresh script starting from a client-provided keyword.

    The keyword is treated as the core idea or "quote seed" for the day.
    We plug it into the existing daily wisdom generator so the rest of the
    flow (scoring + SEO) can run unchanged.
    """
    # Use the keyword as the quote text so the rest of the pipeline
    # (Arthur persona, scoring, SEO) continues to work without changes.
    script = generate_daily_wisdom_script(
        quote_override=payload.keyword,
        source_override="Client keyword",
        persona=payload.persona,
        theme=payload.keyword,
    )
    return script


@app.post("/api/script/revise")
def revise_script(payload: ScriptRevision) -> DailyWisdomScript:
    """
    Regenerate the script based on client suggestions.

    The quote and source stay the same, but the spoken script is rewritten
    in Arthur's voice, applying the requested edits.
    """
    script = revise_wisdom_script(
        quote=payload.quote,
        source=payload.source,
        current_script=payload.current_script,
        suggestions=payload.suggestions,
        persona=payload.persona,
        theme=payload.topic or payload.quote,
    )
    return script


@app.post("/api/script/voice")
def generate_script_voice(payload: ScriptVoiceRequest):
    """
    Generate ElevenLabs audio from the current script text.
    """
    text = (payload.script_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="script_text is required.")

    script_id = payload.script_id or f"{payload.persona}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
    try:
        audio_path = generate_voice_for_script(
            script_text=text,
            script_id=script_id,
            persona=payload.persona,
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Voice generation failed: {e}")

    normalized = audio_path.replace("\\", "/")
    if normalized.startswith("media/"):
        audio_url = f"/{normalized}"
    else:
        audio_url = f"/media/audio/{Path(normalized).name}"
    return {
        "ok": True,
        "persona": payload.persona,
        "audio_path": audio_path,
        "audio_url": audio_url,
        "script_fingerprint": script_fingerprint(text),
    }


@app.post("/api/script/video-bound")
def generate_script_video_bound(payload: ScriptVideoBoundRequest):
    """
    Generate HeyGen video using only a script_agent ledger match (fingerprint),
    optional client visual prompt, and a previously generated ElevenLabs file under media/audio/.
    Does not accept raw script text for this step.
    """
    persona = (payload.persona or "arthur").strip()
    fp = (payload.script_fingerprint or "").strip()
    _video_trace(
        "video_bound.input",
        persona=persona,
        script_fingerprint=fp,
        audio_path=payload.audio_path,
        aspect_ratio=payload.aspect_ratio,
        script_id=payload.script_id or "",
        generation_prompt=(payload.generation_prompt or ""),
    )
    resolved = resolve_script_text_by_fingerprint(persona, fp)
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail="No matching script_agent entry for this fingerprint. "
            "Generate script from the app, then voice, without replacing the spoken text "
            "with ad-hoc edits, or run Script approve again so the text is saved.",
        )
    _video_trace("fingerprint_resolved", persona=persona, script_preview=resolved[:500], script_len=len(resolved))
    audio_file = _resolved_media_audio_file(payload.audio_path)
    norm_audio = payload.audio_path.replace("\\", "/").lstrip("/")
    public_audio = _heygen_public_audio_url(norm_audio)

    sections = _split_script_into_sections(resolved, HEYGEN_REEL_SECTIONS)
    if len(sections) < 2:
        sections = [resolved]
    try:
        if len(sections) == 1:
            _video_trace("video_mode", mode="single_clip")
            result = create_heygen_video(
                script_text=resolved,
                script_id=payload.script_id,
                persona=persona,
                aspect_ratio="9:16",
                external_audio_url=public_audio,
                generation_prompt_override=(payload.generation_prompt or "").strip() or None,
            )
            _video_trace("single_clip.submit_result", result=result)
            return {"ok": True, **result, "script_fingerprint": fp, "audio_path": norm_audio}

        _video_trace("video_mode", mode="multi_clip_reel", sections=len(sections))
        chunk_files = _split_audio_for_reel(audio_file, len(sections))
        chunk_rel_paths = [str(cf.relative_to(PROJECT_ROOT)).replace("\\", "/") for cf in chunk_files]
        clip_results = []
        for idx, section in enumerate(sections):
            chunk_url = _heygen_public_audio_url(chunk_rel_paths[idx])
            prompt_override = (payload.generation_prompt or "").strip() or None
            result = create_heygen_video(
                script_text=section,
                script_id=f"{payload.script_id or persona}_clip_{idx+1}",
                persona=persona,
                aspect_ratio="9:16",
                external_audio_url=chunk_url,
                generation_prompt_override=prompt_override,
            )
            clip_results.append(result)
            _video_trace("clip_submitted", index=idx + 1, section_preview=section[:280], submit_result=result)

        completed = []
        for clip in clip_results:
            st = _wait_heygen_done(clip["video_id"], HEYGEN_REEL_TIMEOUT_SEC)
            completed.append(st)
            _video_trace("clip_completed", video_id=clip["video_id"], video_url=st.get("video_url", ""))

        dl_dir = MEDIA_REELS_DIR / f"tmp_{uuid.uuid4().hex[:10]}"
        dl_dir.mkdir(parents=True, exist_ok=True)
        local_clips = []
        try:
            for i, st in enumerate(completed):
                src_url = str(st.get("video_url") or "").strip()
                if not src_url:
                    raise HTTPException(status_code=503, detail="HeyGen clip completed without video_url.")
                target = dl_dir / f"clip_{i+1:02d}.mp4"
                _download_file(src_url, target)
                local_clips.append(target)

            final_name = f"reel_{persona}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.mp4"
            final_file = MEDIA_REELS_DIR / final_name
            _concat_videos_ffmpeg(local_clips, final_file)
        finally:
            for p in local_clips:
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                dl_dir.rmdir()
            except Exception:
                pass

        response_payload = {
            "ok": True,
            "status": "completed",
            "video_id": f"local_reel_{uuid.uuid4().hex[:10]}",
            "video_url": f"/media/reels/{final_name}",
            "persona": persona,
            "script_fingerprint": fp,
            "audio_path": norm_audio,
            "clip_video_ids": [c.get("video_id", "") for c in clip_results],
            "sections_count": len(sections),
        }
        _video_trace("video_bound.output", response=response_payload)
        return response_payload
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"HeyGen video submit failed: {e}")


@app.post("/api/demo/arthur/reel")
def generate_demo_arthur_reel(payload: DemoArthurReelRequest):
    """
    Demo-only pipeline:
    Generate a single client-review Arthur reel from fixed 13 scene lines,
    render one HeyGen clip per scene, then stitch to one local reel file.
    """
    aspect_ratio = "9:16"
    _video_trace(
        "demo_reel.input",
        aspect_ratio=aspect_ratio,
        scenes=len(ARTHUR_DEMO_SCENES),
        approved=payload.approved,
        approved_prompts_count=len(payload.approved_prompts or []),
    )
    try:
        total_scenes = len(ARTHUR_DEMO_SCENES)
        prompt_plan: list[dict[str, str]] = []
        chosen_prompts: list[str] = []

        custom_prompts = payload.approved_prompts or []
        has_full_custom_set = len(custom_prompts) == total_scenes and all((p or "").strip() for p in custom_prompts)

        for idx, raw_scene in enumerate(ARTHUR_DEMO_SCENES, start=1):
            scene = {**raw_scene, "index": idx, "total": total_scenes}
            scene_prompt = (custom_prompts[idx - 1].strip() if has_full_custom_set else _arthur_demo_scene_prompt(scene))
            chosen_prompts.append(scene_prompt)
            prompt_plan.append(
                {
                    "scene_index": str(idx),
                    "line": scene["line"],
                    "generation_prompt": scene_prompt,
                }
            )

        # Step 1: preview prompts and wait for explicit client approval.
        if not payload.approved:
            out_preview = {
                "ok": True,
                "status": "awaiting_prompt_approval",
                "persona": "arthur",
                "aspect_ratio": aspect_ratio,
                "sections_count": total_scenes,
                "prompt_plan": prompt_plan,
                "next_step": "Resend the same request with approved=true to generate the reel. Optionally provide approved_prompts to edit prompts before generation.",
            }
            _video_trace("demo_reel.prompt_preview", response=out_preview)
            return out_preview

        clip_results = []
        clip_prompts: list[dict[str, str]] = []
        for idx, raw_scene in enumerate(ARTHUR_DEMO_SCENES, start=1):
            scene = {**raw_scene, "index": idx, "total": total_scenes}
            scene_prompt = chosen_prompts[idx - 1]
            result = create_heygen_video(
                script_text=scene["line"],
                script_id=f"arthur_demo_scene_{idx:02d}",
                persona="arthur",
                aspect_ratio=aspect_ratio,
                generation_prompt_override=scene_prompt,
            )
            clip_prompts.append(
                {
                    "scene_index": str(idx),
                    "line": scene["line"],
                    "generation_prompt": scene_prompt,
                }
            )
            clip_results.append(result)
            _video_trace("demo_reel.clip_submitted", scene_index=idx, line=scene["line"], video_id=result.get("video_id", ""))

        completed = []
        for clip in clip_results:
            st = _wait_heygen_done(clip["video_id"], HEYGEN_REEL_TIMEOUT_SEC)
            completed.append(st)
            _video_trace("demo_reel.clip_completed", video_id=clip["video_id"], video_url=st.get("video_url", ""))

        dl_dir = MEDIA_REELS_DIR / f"demo_tmp_{uuid.uuid4().hex[:10]}"
        dl_dir.mkdir(parents=True, exist_ok=True)
        local_clips = []
        try:
            for i, st in enumerate(completed):
                src_url = str(st.get("video_url") or "").strip()
                if not src_url:
                    raise HTTPException(status_code=503, detail="HeyGen scene completed without video_url.")
                target = dl_dir / f"scene_{i+1:02d}.mp4"
                _download_file(src_url, target)
                local_clips.append(target)

            final_name = f"arthur_demo_reel_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.mp4"
            final_file = MEDIA_REELS_DIR / final_name
            _concat_videos_ffmpeg(local_clips, final_file)
        finally:
            for p in local_clips:
                try:
                    p.unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                dl_dir.rmdir()
            except Exception:
                pass

        out = {
            "ok": True,
            "status": "completed",
            "persona": "arthur",
            "video_id": f"demo_reel_{uuid.uuid4().hex[:10]}",
            "video_url": f"/media/reels/{final_name}",
            "sections_count": len(ARTHUR_DEMO_SCENES),
            "clip_video_ids": [c.get("video_id", "") for c in clip_results],
            "clip_prompts": clip_prompts,
        }
        _video_trace("demo_reel.output", response=out)
        return out
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Arthur demo reel generation failed: {e}")


@app.post("/api/script/video")
def generate_script_video(payload: ScriptVideoRequest):
    """
    Legacy: HeyGen video from client-supplied script text + HeyGen TTS.
    Prefer POST /api/script/video-bound with ledger fingerprint + ElevenLabs audio.
    """
    text = (payload.script_text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="script_text is required.")
    try:
        result = create_heygen_video(
            script_text=text,
            script_id=payload.script_id,
            persona=payload.persona,
            aspect_ratio="9:16",
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"HeyGen video submit failed: {e}")
    return {"ok": True, **result}


@app.get("/api/script/video/{video_id}")
def get_script_video_status(video_id: str):
    """
    Poll HeyGen video job status.
    """
    try:
        result = get_heygen_video_status(video_id=video_id)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"HeyGen video status failed: {e}")

    # Omit bulky nested payload from polling responses.
    result = {k: v for k, v in result.items() if k != "raw"}

    # Helpful for debugging repeated failures (credits/quota vs invalid payload).
    state = str(result.get("status") or "").lower()
    if state in ("failed", "error"):
        print(
            f"HeyGen job failed: video_id={video_id} "
            f"code={result.get('error_code','')} message={result.get('error_message','')} "
            f"detail={result.get('error_detail','')}"
        )
    return {"ok": True, **result}


@app.get("/api/pipeline-runs")
def list_pipeline_runs(limit: int = 50):
    """
    List the most recent stored pipeline runs (text-only pipeline).
    """
    if is_supabase_configured():
        items = sb_list_pipeline_runs(limit=limit)
        return {"source": "supabase", "count": len(items), "items": items}

    runs = _load_pipeline_runs()
    runs = list(reversed(runs))  # newest first
    return {"source": "local_json", "file": str(PIPELINE_RUNS_FILE), "count": len(runs), "items": runs[:limit]}


@app.get("/api/pipeline-runs/approved")
def list_approved_pipeline_runs(limit: int = 50):
    """
    Return runs that are ready for production (final_approved == true).
    """
    if is_supabase_configured():
        items = sb_list_approved_pipeline_runs(limit=limit)
        return {"source": "supabase", "count": len(items), "items": items}

    runs = _load_pipeline_runs()
    approved = [r for r in runs if bool(r.get("final_approved"))]
    approved = list(reversed(approved))
    return {"source": "local_json", "file": str(PIPELINE_RUNS_FILE), "count": len(approved), "items": approved[:limit]}


@app.patch("/api/pipeline-runs/{run_id}/approve")
def approve_pipeline_run(run_id: str, patch: RunApprovalPatch):
    """
    Patch approval booleans on a stored pipeline run by ID.
    """
    if is_supabase_configured():
        item = sb_patch_pipeline_run_approvals(
            run_id,
            topic_approved=patch.topic_approved,
            script_approved=patch.script_approved,
            final_approved=patch.final_approved,
        )
        return {"ok": True, "source": "supabase", "item": item}

    runs = _load_pipeline_runs()
    for r in runs:
        if str(r.get("id")) == run_id:
            if patch.topic_approved is not None:
                r["topic_approved"] = bool(patch.topic_approved)
            if patch.script_approved is not None:
                r["script_approved"] = bool(patch.script_approved)
            if patch.final_approved is not None:
                r["final_approved"] = bool(patch.final_approved)
            _save_pipeline_runs(runs)
            return {"ok": True, "source": "local_json", "item": r}

    raise HTTPException(status_code=404, detail=f"Run id not found: {run_id}")


FRONTEND_DIR = PROJECT_ROOT / "frontend"
if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


