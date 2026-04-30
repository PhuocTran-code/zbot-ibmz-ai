"""
FastAPI server for IBM Z Xplore AI assistant (ZBot).

Run:
    uvicorn main:app --reload --port 8000
"""

import logging
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

load_dotenv()

import rag
import supabase_db
from badge_config import (
    BADGES,
    check_concepts_badge,
    check_advanced_badge,
    suggest_next_badge,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── App setup ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="IBM Z Xplore AI Assistant",
    description="ZBot — RAG-powered learning assistant for IBM Z Xplore",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^(https?://localhost(:\d+)?|https://.*\.vercel\.app)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Progress store ───────────────────────────────────────────────────────────
# Uses Supabase when SUPABASE_URL + SUPABASE_KEY are set; falls back to an
# in-memory dict for local development without a database.

_mem_progress: dict[str, dict[str, str]] = {}

VALID_STATUSES = {"not_started", "in_progress", "completed"}


def _get_user_progress(user_id: str) -> dict[str, str]:
    if supabase_db.is_configured():
        return supabase_db.get_user_progress(user_id)
    return _mem_progress.setdefault(user_id, {})


def _completed_badges(user_id: str) -> list[str]:
    return [
        badge_id
        for badge_id, status in _get_user_progress(user_id).items()
        if status == "completed"
    ]


def _build_progress_summary(user_id: str) -> str:
    progress = _get_user_progress(user_id)
    if not progress:
        return "No badges started yet."
    completed = [b for b, s in progress.items() if s == "completed"]
    in_progress = [b for b, s in progress.items() if s == "in_progress"]
    parts = []
    if completed:
        parts.append(f"Completed: {', '.join(completed)}")
    if in_progress:
        parts.append(f"In progress: {', '.join(in_progress)}")
    total_points = sum(BADGES[b]["points"] for b in completed if b in BADGES)
    parts.append(f"Total points: {total_points}")
    return " | ".join(parts)


# ── Request / Response models ────────────────────────────────────────────────

class ChatRequest(BaseModel):
    user_id: str
    message: str
    badge_filter: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[dict]
    provider: str
    suggestion: list[str]
    follow_up_questions: list[str] = []
    error: Optional[str] = None


class ProgressUpdateRequest(BaseModel):
    user_id: str
    badge_id: str
    status: str


class ProgressUpdateResponse(BaseModel):
    user_id: str
    badge_id: str
    status: str
    concepts_unlocked: bool
    advanced_unlocked: bool


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Health check — confirms the server is running."""
    return {"status": "ok", "service": "IBM Z Xplore AI Assistant"}


@app.get("/health", tags=["Health"])
def health():
    """Detailed health status."""
    return {"status": "ok", "version": app.version}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(req: ChatRequest):
    """
    Send a question to ZBot.

    ZBot retrieves relevant documentation chunks from ChromaDB and generates
    an answer using the configured LLM provider (Gemini / Groq).
    """
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    if req.badge_filter and req.badge_filter not in BADGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown badge_filter '{req.badge_filter}'. "
                   f"Valid IDs: {list(BADGES.keys())}",
        )

    completed = _completed_badges(req.user_id)
    progress_summary = _build_progress_summary(req.user_id)
    current_badge = (
        BADGES[req.badge_filter]["title"] if req.badge_filter else "Not specified"
    )

    result = rag.query(
        user_message=req.message,
        badge_filter=req.badge_filter,
        current_badge=current_badge,
        progress_summary=progress_summary,
    )

    suggestion = suggest_next_badge(completed)

    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        provider=result["provider"],
        suggestion=suggestion,
        follow_up_questions=result["follow_up_questions"],
        error=result["error"],
    )


@app.get("/badges", tags=["Badges"])
def list_badges():
    """Return metadata for all 17 badges, grouped by type."""
    grouped: dict[str, list[dict]] = {}
    for badge_id, meta in BADGES.items():
        badge_type = meta["type"]
        grouped.setdefault(badge_type, []).append(
            {
                "id":     badge_id,
                "title":  meta["title"],
                "type":   badge_type,
                "points": meta["points"],
                "pdf":    meta["pdf"],
            }
        )
    return {"badges": grouped}


@app.get("/progress/{user_id}", tags=["Progress"])
def get_progress(user_id: str):
    """
    Return a user's learning progress together with badge unlock status.
    """
    progress = _get_user_progress(user_id)
    completed = _completed_badges(user_id)

    badge_details = []
    total_points = 0
    for badge_id, status in progress.items():
        if badge_id not in BADGES:
            continue
        meta = BADGES[badge_id]
        pts = meta["points"] if status == "completed" else 0
        total_points += pts
        badge_details.append(
            {
                "id":     badge_id,
                "title":  meta["title"],
                "type":   meta["type"],
                "points": meta["points"],
                "status": status,
            }
        )

    return {
        "user_id":           user_id,
        "badges":            badge_details,
        "total_points":      total_points,
        "concepts_unlocked": check_concepts_badge(completed),
        "advanced_unlocked": check_advanced_badge(completed),
        "next_suggestions":  suggest_next_badge(completed),
    }


@app.post("/progress", response_model=ProgressUpdateResponse, tags=["Progress"])
def update_progress(req: ProgressUpdateRequest):
    """
    Create or update the status of a badge for a user.

    Valid status values: ``not_started``, ``in_progress``, ``completed``.
    """
    if req.badge_id not in BADGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown badge_id '{req.badge_id}'. "
                   f"Valid IDs: {list(BADGES.keys())}",
        )
    if req.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{req.status}'. "
                   f"Must be one of: {sorted(VALID_STATUSES)}",
        )

    if supabase_db.is_configured():
        supabase_db.upsert_progress(req.user_id, req.badge_id, req.status)
    else:
        _get_user_progress(req.user_id)[req.badge_id] = req.status
    completed = _completed_badges(req.user_id)

    logger.info(
        "Progress update — user=%s badge=%s status=%s",
        req.user_id, req.badge_id, req.status,
    )

    return ProgressUpdateResponse(
        user_id=req.user_id,
        badge_id=req.badge_id,
        status=req.status,
        concepts_unlocked=check_concepts_badge(completed),
        advanced_unlocked=check_advanced_badge(completed),
    )
