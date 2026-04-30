"""
Backend API tests for ZBot — IBM Z Xplore AI Assistant.

Run from backend/ directory:
    pytest tests/ -v

Uses FastAPI TestClient (synchronous) + unittest.mock to avoid real LLM calls
and Supabase connections.
"""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Ensure backend/ is on path when running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Patch rag.query before importing main so ChromaDB/sentence-transformers
# are never initialised during tests.
_mock_rag_result = {
    "answer": "Test answer.",
    "sources": [{"badge_id": "VSC1", "title": "Visual Studio Code", "chunk": "intro"}],
    "provider": "mock",
    "follow_up_questions": ["What is VSC1?"],
    "error": None,
}

with patch("rag.query", return_value=_mock_rag_result):
    from main import app  # noqa: E402 — intentional late import

client = TestClient(app)


# ── Health endpoints ──────────────────────────────────────────────────────────

class TestHealth:
    def test_root_returns_ok(self):
        res = client.get("/")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"

    def test_health_returns_ok(self):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "ok"
        assert "version" in data


# ── Badges endpoint ───────────────────────────────────────────────────────────

class TestBadges:
    def test_list_badges_returns_grouped_dict(self):
        res = client.get("/badges")
        assert res.status_code == 200
        data = res.json()
        assert "badges" in data
        assert isinstance(data["badges"], dict)

    def test_all_17_badges_present(self):
        res = client.get("/badges")
        all_badges = [b for group in res.json()["badges"].values() for b in group]
        assert len(all_badges) == 17

    def test_badge_has_required_fields(self):
        res = client.get("/badges")
        first_group = next(iter(res.json()["badges"].values()))
        badge = first_group[0]
        assert {"id", "title", "type", "points", "pdf"} <= badge.keys()


# ── Progress endpoints ────────────────────────────────────────────────────────

class TestProgress:
    USER = "test_user_pytest"

    def test_get_progress_empty_user(self):
        res = client.get(f"/progress/{self.USER}_empty")
        assert res.status_code == 200
        data = res.json()
        assert data["total_points"] == 0
        assert data["badges"] == []

    def test_update_progress_valid(self):
        res = client.post(
            "/progress",
            json={"user_id": self.USER, "badge_id": "VSC1", "status": "in_progress"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["badge_id"] == "VSC1"
        assert data["status"] == "in_progress"

    def test_update_progress_invalid_badge(self):
        res = client.post(
            "/progress",
            json={"user_id": self.USER, "badge_id": "FAKE_ID", "status": "completed"},
        )
        assert res.status_code == 400

    def test_update_progress_invalid_status(self):
        res = client.post(
            "/progress",
            json={"user_id": self.USER, "badge_id": "VSC1", "status": "done"},
        )
        assert res.status_code == 400

    def test_completed_badge_adds_points(self):
        uid = f"{self.USER}_points"
        client.post(
            "/progress",
            json={"user_id": uid, "badge_id": "VSC1", "status": "completed"},
        )
        res = client.get(f"/progress/{uid}")
        assert res.json()["total_points"] > 0

    def test_concepts_unlocked_after_all_fundamentals(self):
        uid = f"{self.USER}_concepts"
        fundamentals = ["VSC1", "FILES1", "JCL1", "USS1", "CODE1", "REXX1", "WRAPUP"]
        for fid in fundamentals:
            client.post(
                "/progress",
                json={"user_id": uid, "badge_id": fid, "status": "completed"},
            )
        # Also need ≥ 2 Concepts badges per badge_config rules
        for cid in ["IBM_Z_PRACTITIONERS", "ENTERPRISE_SYSTEMS"]:
            client.post(
                "/progress",
                json={"user_id": uid, "badge_id": cid, "status": "completed"},
            )
        res = client.get(f"/progress/{uid}")
        assert res.json()["concepts_unlocked"] is True


# ── Chat endpoint ─────────────────────────────────────────────────────────────

class TestChat:
    def test_chat_returns_answer(self):
        with patch("rag.query", return_value=_mock_rag_result):
            res = client.post(
                "/chat",
                json={"user_id": "test_user", "message": "What is VSC1?"},
            )
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert data["answer"] == "Test answer."

    def test_chat_empty_message_rejected(self):
        res = client.post(
            "/chat",
            json={"user_id": "test_user", "message": "   "},
        )
        assert res.status_code == 400

    def test_chat_invalid_badge_filter_rejected(self):
        with patch("rag.query", return_value=_mock_rag_result):
            res = client.post(
                "/chat",
                json={
                    "user_id": "test_user",
                    "message": "Tell me about this badge",
                    "badge_filter": "NONEXISTENT_BADGE",
                },
            )
        assert res.status_code == 400

    def test_chat_with_valid_badge_filter(self):
        with patch("rag.query", return_value=_mock_rag_result):
            res = client.post(
                "/chat",
                json={
                    "user_id": "test_user",
                    "message": "How do I start?",
                    "badge_filter": "VSC1",
                },
            )
        assert res.status_code == 200

    def test_chat_response_has_sources(self):
        with patch("rag.query", return_value=_mock_rag_result):
            res = client.post(
                "/chat",
                json={"user_id": "test_user", "message": "Explain JCL"},
            )
        data = res.json()
        assert isinstance(data["sources"], list)

    def test_chat_response_has_suggestion(self):
        with patch("rag.query", return_value=_mock_rag_result):
            res = client.post(
                "/chat",
                json={"user_id": "test_user", "message": "What badge next?"},
            )
        data = res.json()
        assert isinstance(data["suggestion"], list)
