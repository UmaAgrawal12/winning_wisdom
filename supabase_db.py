from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv


# Ensure environment variables are loaded when running from project root.
# Your `.env` lives in `winning_wisdom_ai/.env`, not necessarily in the CWD.
_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)


def _get_env(name: str) -> Optional[str]:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def is_supabase_configured() -> bool:
    return bool(_get_env("SUPABASE_URL") and _get_env("SUPABASE_SERVICE_ROLE_KEY"))


def get_supabase_client():
    """
    Lazily create Supabase client so importing this module doesn't crash
    when env vars aren't set (useful for local dev / fallback).
    """
    supabase_url = _get_env("SUPABASE_URL")
    supabase_key = _get_env("SUPABASE_SERVICE_ROLE_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError(
            "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in your environment."
        )

    from supabase import create_client  # local import to avoid hard dependency at import time

    return create_client(supabase_url, supabase_key)


def insert_pipeline_run(row: Dict[str, Any]) -> Dict[str, Any]:
    client = get_supabase_client()
    resp = client.table("pipeline_runs").insert(row).execute()
    data = getattr(resp, "data", None)
    if isinstance(data, list) and data:
        return data[0]
    return row


def list_pipeline_runs(limit: int = 50) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = (
        client.table("pipeline_runs")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    data = getattr(resp, "data", None)
    return data if isinstance(data, list) else []


def list_approved_pipeline_runs(limit: int = 50) -> List[Dict[str, Any]]:
    client = get_supabase_client()
    resp = (
        client.table("pipeline_runs")
        .select("*")
        .eq("final_approved", True)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    data = getattr(resp, "data", None)
    return data if isinstance(data, list) else []


def patch_pipeline_run_approvals(
    run_id: str,
    *,
    topic_approved: Optional[bool] = None,
    script_approved: Optional[bool] = None,
    final_approved: Optional[bool] = None,
) -> Dict[str, Any]:
    patch: Dict[str, Any] = {}
    if topic_approved is not None:
        patch["topic_approved"] = bool(topic_approved)
    if script_approved is not None:
        patch["script_approved"] = bool(script_approved)
    if final_approved is not None:
        patch["final_approved"] = bool(final_approved)
    if not patch:
        return {"id": run_id}

    client = get_supabase_client()
    resp = client.table("pipeline_runs").update(patch).eq("id", run_id).select("*").execute()
    data = getattr(resp, "data", None)
    if isinstance(data, list) and data:
        return data[0]
    return {"id": run_id, **patch}

