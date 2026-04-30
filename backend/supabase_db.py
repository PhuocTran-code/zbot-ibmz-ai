"""
Supabase persistence layer for user progress.

Requires environment variables:
    SUPABASE_URL  — project URL (https://xxx.supabase.co)
    SUPABASE_KEY  — anon/service-role key

If either is missing, is_configured() returns False and callers fall back
to the in-memory store so the server still runs during local development.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_client = None


def is_configured() -> bool:
    return bool(os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_KEY"))


def _get_client():
    global _client
    if _client is None:
        from supabase import create_client
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_KEY"]
        _client = create_client(url, key)
    return _client


def get_user_progress(user_id: str) -> dict[str, str]:
    """Return {badge_id: status} for a user (empty dict if none recorded)."""
    try:
        result = (
            _get_client()
            .table("user_progress")
            .select("badge_id, status")
            .eq("user_id", user_id)
            .execute()
        )
        return {row["badge_id"]: row["status"] for row in result.data}
    except Exception:
        logger.exception("Supabase get_user_progress failed for user=%s", user_id)
        return {}


def upsert_progress(user_id: str, badge_id: str, status: str) -> None:
    """Insert or update a single badge status row."""
    try:
        _get_client().table("user_progress").upsert(
            {"user_id": user_id, "badge_id": badge_id, "status": status},
            on_conflict="user_id,badge_id",
        ).execute()
    except Exception:
        logger.exception(
            "Supabase upsert_progress failed — user=%s badge=%s status=%s",
            user_id, badge_id, status,
        )
        raise
