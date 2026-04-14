from __future__ import annotations

import os
import re
import time
from openai import OpenAI

from config.personas import get_persona
from config.system_config import GEMINI_API_KEY, GEMINI_MODEL_SCRIPT, GEMINI_OPENAI_BASE_URL

client = OpenAI(api_key=GEMINI_API_KEY, base_url=GEMINI_OPENAI_BASE_URL)
PROMPT_AGENT_DEBUG = (os.getenv("PROMPT_AGENT_DEBUG") or "true").strip().lower() in {"1", "true", "yes", "on"}
PROMPT_AGENT_TIMEOUT_SEC = float((os.getenv("PROMPT_AGENT_TIMEOUT_SEC") or "25").strip())


def _print_prompt_agent_trace(stage: str, **fields: str) -> None:
    if not PROMPT_AGENT_DEBUG:
        return
    print(f"\n[PROMPT_AGENT_TRACE] stage={stage}")
    for key, value in fields.items():
        print(f"{key}={value}")
    print("[/PROMPT_AGENT_TRACE]\n")


def _clean_prompt_text(text: str) -> str:
    cleaned = (text or "").strip()
    # Remove markdown fences/headings if model adds them.
    cleaned = re.sub(r"^```[\w-]*\s*|\s*```$", "", cleaned, flags=re.MULTILINE).strip()
    cleaned = re.sub(r"^\s*(?:prompt|heygen prompt)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
    # Preserve section formatting; only normalize runaway blank lines.
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def _looks_like_pool_stitch(text: str) -> bool:
    t = (text or "").lower()
    bad_markers = (
        "persona tone:",
        "scene:",
        "camera behavior:",
        "gesture profile:",
        "energy profile:",
        "[base realism rules]",
    )
    return any(m in t for m in bad_markers)


def generate_local_heygen_prompt(
    script_text: str,
    persona: str,
    base_realism_rules: str,
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
    echo: bool | None = None,
) -> str:
    """
    Script-aware local prompt composer used when LLM is unavailable.
    Keeps output natural and production-ready without label stitching.
    """
    text = (script_text or "").strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    short_lines = sum(1 for ln in lines if len(ln.split()) <= 8)
    if len(lines) >= 2 and short_lines >= max(2, len(lines) // 2):
        pause_hint = "Respect the short-line cadence with clean pauses between lines so emphasis lands naturally."
    elif len(lines) >= 2:
        pause_hint = "Use deliberate micro-pauses at line breaks and after emotionally weighted phrases."
    else:
        pause_hint = "Use subtle pauses after key clauses to keep delivery natural."

    gesture_hint = {
        "low": "Keep gestures restrained but visible: occasional hand-in-frame emphasis, controlled nods, and natural posture shifts.",
        "medium": "Use moderate, purposeful hand gestures aligned with emphasis words, with forearms visible in medium/waist-up framing.",
        "expressive but restrained": "Use expressive but controlled hand/forearm gestures with subtle torso sway, avoiding theatrical motion.",
    }.get(gesture_profile, "Use natural conversational gestures.")

    energy_hint = {
        "reflective": "Keep a reflective, thoughtful rhythm.",
        "direct": "Keep delivery clear, direct, and confident without aggression.",
        "urgent": "Carry urgency through pacing and intent while staying composed.",
    }.get(energy_profile, "Keep emotional delivery aligned with meaning.")

    persona_name = get_persona(persona).display_name
    prompt = (
        "[ROLE AND GOAL]\n"
        "Generate a photoreal talking-head reel that feels naturally captured, not synthetic. "
        "Optimize for perceptual realism over visual perfection.\n\n"
        "[IDENTITY CONSISTENCY]\n"
        f"{identity_static}\n\n"
        "[CAMERA POSITION AND BEHAVIOR]\n"
        f"Static camera base: {camera_base}. Dynamic camera motion: {camera_behavior}. "
        "Avoid mathematically static framing and avoid aggressive movement. "
        "Prefer medium-to-waist-up framing so hands can appear naturally in frame.\n\n"
        "[LIGHTING PHYSICS]\n"
        f"Static lighting base: {lighting_base}. Keep skin highlights and reflections consistent with light direction.\n\n"
        "[ENVIRONMENT REALISM]\n"
        f"Scene should be {scene}, matched to {persona_name}'s archetype and message intent. "
        "Maintain controlled background complexity and clear subject separation.\n\n"
        "[MOTION AND MICRO-EXPRESSIONS]\n"
        f"{gesture_hint} {energy_hint} Delivery style: {delivery_style}. Micro-expression profile: {micro_expression_style}. {pause_hint} "
        "Use natural blink cadence, subtle head micro-tilts, slight posture sway, and realistic shoulder-breath movement. "
        "Avoid frozen torso posture or repetitive looped gestures.\n\n"
        "[SPEECH, LIP-SYNC, AND SEMANTIC SYNC]\n"
        "Maintain precise lip-sync, but prioritize semantic sync: gestures, facial intensity, and nod timing should match phrase emphasis.\n\n"
        "[QUALITY AND IMPERFECTION LAYER]\n"
        f"{base_realism_rules} Allow subtle real-world imperfection; avoid plastic skin, robotic articulation, and over-clean synthetic feel.\n\n"
        "[PSYCHOLOGY CHECK]\n"
        "Ensure lighting makes sense, voice-face coherence holds, body moves while talking, camera behaves like real capture, and mild imperfection remains.\n\n"
        "[PERSONA CONTEXT]\n"
        f"Persona tone: {persona_tone}. Voice identity: {get_persona(persona).voice_style}\n\n"
        "[SCRIPT - USE EXACTLY]\n"
        f"{text}"
    )
    do_print = PROMPT_AGENT_DEBUG if echo is None else bool(echo)
    if do_print:
        print("\n[PROMPT_AGENT] source=local_fallback")
        print(prompt)
        print("[/PROMPT_AGENT]\n")
    return prompt


def generate_heygen_prompt(
    script_text: str,
    persona: str,
    base_realism_rules: str,
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
    echo: bool | None = None,
) -> str:
    """
    Use LLM to author a single production-style HeyGen prompt from selected blocks.

    echo: None -> use PROMPT_AGENT_DEBUG; False -> never print (caller handles logging);
          True -> always print when a prompt is produced.
    """
    persona_cfg = get_persona(persona)
    do_print = PROMPT_AGENT_DEBUG if echo is None else bool(echo)
    _print_prompt_agent_trace(
        "input",
        persona=persona_cfg.name,
        script_preview=(script_text or "").strip()[:240],
        delivery_style=delivery_style,
        micro_expression_style=micro_expression_style,
        persona_tone=persona_tone,
        scene=scene,
        camera_behavior=camera_behavior,
        gesture_profile=gesture_profile,
        energy_profile=energy_profile,
    )
    user_prompt = f"""
Write one clean, production-ready HeyGen prompt with these EXACT sections and headers:
[ROLE AND GOAL]
[IDENTITY CONSISTENCY]
[CAMERA POSITION AND BEHAVIOR]
[LIGHTING PHYSICS]
[ENVIRONMENT REALISM]
[MOTION AND MICRO-EXPRESSIONS]
[SPEECH, LIP-SYNC, AND SEMANTIC SYNC]
[QUALITY AND IMPERFECTION LAYER]
[PSYCHOLOGY CHECK]
[PERSONA CONTEXT]
[SCRIPT - USE EXACTLY]

Hard requirements:
- Keep section structure exactly as listed above.
- Do not output markdown fences.
- Keep instructions practical and cinematic, not generic.
- Use the exact script text in the last section without rewriting.

Persona context:
- Name: {persona_cfg.display_name}
- Description: {persona_cfg.description}
- Voice style: {persona_cfg.voice_style}

Selected controls to blend naturally:
- {base_realism_rules}
- Identity anchors: {identity_static}
- Camera base: {camera_base}
- Lighting base: {lighting_base}
- Delivery style: {delivery_style}
- Micro-expression style: {micro_expression_style}
- Tone: {persona_tone}
- Scene: {scene}
- Camera motion: {camera_behavior}
- Gesture intensity: {gesture_profile}
- Delivery energy: {energy_profile}
"""
    messages = [
        {
            "role": "system",
            "content": (
                "You are a senior prompt writer for photoreal avatar video generation. "
                "Write section-wise prompts that are practical, specific, and production-ready."
            ),
        },
        {"role": "user", "content": user_prompt},
    ]

    candidate = ""
    last_err = None
    # Retry primary generation for transient overload/rate-limit issues.
    for i in range(3):
        try:
            response = client.chat.completions.create(
                model=GEMINI_MODEL_SCRIPT,
                messages=messages,
                temperature=0.45,
                timeout=PROMPT_AGENT_TIMEOUT_SEC,
            )
            candidate = _clean_prompt_text(response.choices[0].message.content or "")
            if candidate and not _looks_like_pool_stitch(candidate):
                _print_prompt_agent_trace("output", source="llm_primary", prompt_preview=candidate[:700])
                if do_print:
                    print("\n[PROMPT_AGENT] source=llm_primary")
                    print(candidate)
                    print("[/PROMPT_AGENT]\n")
                return candidate
            break
        except Exception as exc:
            last_err = exc
            _print_prompt_agent_trace("error", source="llm_primary", error=str(exc))
            msg = str(exc).lower()
            transient = any(k in msg for k in ("503", "unavailable", "high demand", "rate limit", "429"))
            if i < 2 and transient:
                time.sleep(1.5 * (2 ** i))
                continue
            return generate_local_heygen_prompt(
                script_text=script_text,
                persona=persona,
                base_realism_rules=base_realism_rules,
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
                echo=echo,
            )

    # Retry once with stronger anti-template instruction.
    retry_messages = messages + [
        {
            "role": "user",
            "content": (
                "Rewrite and keep the exact required section headers and order."
            ),
        }
    ]
    for i in range(2):
        try:
            retry = client.chat.completions.create(
                model=GEMINI_MODEL_SCRIPT,
                messages=retry_messages,
                temperature=0.35,
                timeout=PROMPT_AGENT_TIMEOUT_SEC,
            )
            cleaned = _clean_prompt_text(retry.choices[0].message.content or "")
            if cleaned:
                _print_prompt_agent_trace("output", source="llm_retry", prompt_preview=cleaned[:700])
                if do_print:
                    print("\n[PROMPT_AGENT] source=llm_retry")
                    print(cleaned)
                    print("[/PROMPT_AGENT]\n")
                return cleaned
        except Exception as exc:
            last_err = exc
            _print_prompt_agent_trace("error", source="llm_retry", error=str(exc))
            msg = str(exc).lower()
            transient = any(k in msg for k in ("503", "unavailable", "high demand", "rate limit", "429"))
            if i < 1 and transient:
                time.sleep(2.0)
                continue
            return generate_local_heygen_prompt(
                script_text=script_text,
                persona=persona,
                base_realism_rules=base_realism_rules,
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
                echo=echo,
            )
    if last_err:
        return generate_local_heygen_prompt(
            script_text=script_text,
            persona=persona,
            base_realism_rules=base_realism_rules,
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
            echo=echo,
        )
    return candidate

