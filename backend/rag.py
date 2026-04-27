"""
RAG query pipeline for IBM Z Xplore AI assistant (ZBot).

Singleton pattern: the embedding model and ChromaDB collection are loaded
once at first use and reused for the lifetime of the process.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import chromadb
from sentence_transformers import SentenceTransformer

from llm import get_llm_response
from badge_config import BADGES, FUNDAMENTALS, CONCEPTS_IDS, ADVANCED_IDS, ALLSTAR_IDS

logger = logging.getLogger(__name__)

# ── Paths & constants ────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "zxplore_knowledge"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
SOURCE_SCORE_THRESHOLD = 0.3   # minimum similarity score to include in sources

# ── Badge catalog (injected into every prompt) ───────────────────────────────

def _build_badge_catalog() -> str:
    """Build a human-readable badge catalog string for the system prompt."""
    tiers = [
        ("Fundamentals", FUNDAMENTALS),
        ("Concepts",     CONCEPTS_IDS),
        ("Advanced",     ADVANCED_IDS),
        ("AllStar",      ALLSTAR_IDS),
    ]
    lines = []
    for tier_name, ids in tiers:
        entries = []
        for bid in ids:
            meta = BADGES[bid]
            entries.append(f"  - {bid} ({meta['title']}, {meta['points']} pts)")
        lines.append(f"{tier_name} tier:\n" + "\n".join(entries))
    return "\n\n".join(lines)


BADGE_CATALOG = _build_badge_catalog()

# ── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are ZBot, an AI assistant specialised in the IBM Z Xplore learning platform.

Your role:
- Help learners understand IBM Z concepts and complete badge challenges.
- Answer questions **only** using the documentation excerpts provided below.
- If the answer cannot be found in the provided context, say so honestly and suggest the learner consult the official IBM Z Xplore portal.

--- IBM Z Xplore Badge Structure ---
The platform has 17 badges organised into 4 tiers. When a learner mentions a tier name
(e.g. "Concepts badge" or "Advanced badge"), they are referring to the ENTIRE tier below.

{badge_catalog}

Unlock rules:
- "Concepts completion" requires: ALL 7 Fundamentals badges + at least 2 Concepts badges.
- "Advanced completion" requires: at least 5 badges from the Advanced + AllStar pool.

Citation rules:
- Always cite your sources inline using the format: "per [BADGE_ID] Step [N]"
  (e.g. "per JCL1 Step 3").
- For overview excerpts use: "per [BADGE_ID] Overview".

End every response with TWO sections (in this exact order):

1. **## Next steps** — a short paragraph suggesting what the learner should try or explore next, based on their current progress.

2. **## Follow-up questions** — exactly 3 numbered questions the learner could ask to deepen their conceptual understanding. These should go *beyond* step-by-step tasks: ask about underlying mechanisms, design trade-offs, comparisons with other technologies, or real-world use cases.

Example format for the second section:
## Follow-up questions
1. Why does z/OS use EBCDIC encoding instead of ASCII?
2. How does JES2 differ from JES3 in job scheduling?
3. What happens internally when a JCL job is submitted to the input queue?

--- Current context ---
Badge the learner is working on: {current_badge}
Progress summary: {progress_summary}

--- Relevant documentation ---
{context}
"""


# ── Follow-up question parser ────────────────────────────────────────────────

_FOLLOW_UP_RE = re.compile(
    r'\n*##\s*Follow-up questions?\s*\n((?:\d+\..+\n?)+)',
    re.IGNORECASE,
)


def _extract_follow_up(text: str) -> tuple[str, list[str]]:
    """Strip the Follow-up questions section from *text* and return it separately."""
    match = _FOLLOW_UP_RE.search(text)
    if not match:
        return text, []
    questions = [q.strip() for q in re.findall(r'\d+\.\s*(.+)', match.group(1))]
    clean = text[: match.start()].rstrip()
    return clean, questions


# ── Singleton state ──────────────────────────────────────────────────────────

@dataclass
class _RAGState:
    embed_model: Optional[SentenceTransformer] = field(default=None)
    collection: Optional[chromadb.Collection] = field(default=None)


_state = _RAGState()


def _get_embed_model() -> SentenceTransformer:
    if _state.embed_model is None:
        logger.info("Loading embedding model '%s'…", EMBED_MODEL_NAME)
        _state.embed_model = SentenceTransformer(EMBED_MODEL_NAME)
    return _state.embed_model


def _get_collection() -> chromadb.Collection:
    if _state.collection is None:
        logger.info("Connecting to ChromaDB at %s", CHROMA_DIR)
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        _state.collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _state.collection


# ── Core pipeline ────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    badge_filter: Optional[str] = None,
    top_k: int = 5,
) -> list[dict]:
    """
    Embed *query* and run a similarity search against the ChromaDB collection.

    Args:
        query:        Natural-language question from the user.
        badge_filter: Optional badge_id to restrict results to one badge.
        top_k:        Maximum number of chunks to return.

    Returns:
        List of dicts, each with keys:
            document, badge_id, badge_type, step_number, step_title, points,
            chunk_id, score
        Sorted by score descending.
    """
    model = _get_embed_model()
    collection = _get_collection()

    query_embedding = model.encode(query).tolist()

    where_filter = {"badge_id": badge_filter} if badge_filter else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    chunks: list[dict] = []
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for doc, meta, dist in zip(documents, metadatas, distances):
        # ChromaDB cosine distance → similarity score (0–1, higher = better)
        score = 1.0 - dist
        chunks.append(
            {
                "document":   doc,
                "badge_id":   meta.get("badge_id", ""),
                "badge_type": meta.get("badge_type", ""),
                "step_number": meta.get("step_number", 0),
                "step_title":  meta.get("step_title", ""),
                "points":      meta.get("points", 0),
                "chunk_id":    meta.get("chunk_id", ""),
                "score":       round(score, 4),
            }
        )

    chunks.sort(key=lambda c: c["score"], reverse=True)
    return chunks


def format_context(chunks: list[dict]) -> str:
    """
    Convert retrieved chunks into a clearly headed string for the system prompt.

    Format per chunk:
        [BADGE_ID | Step N – Step Title]  (score: 0.87)
        <document text>
    """
    if not chunks:
        return "No relevant documentation found."

    lines: list[str] = []
    for chunk in chunks:
        badge_id    = chunk["badge_id"]
        step_number = chunk["step_number"]
        step_title  = chunk["step_title"]
        score       = chunk["score"]

        if step_number == 0 and step_title == "Overview":
            header = f"[{badge_id} | Overview]  (score: {score})"
        else:
            header = f"[{badge_id} | Step {step_number} – {step_title}]  (score: {score})"

        lines.append(header)
        lines.append(chunk["document"])
        lines.append("")   # blank line between chunks

    return "\n".join(lines).strip()


def query(
    user_message: str,
    badge_filter: Optional[str] = None,
    current_badge: str = "N/A",
    progress_summary: str = "No progress data available.",
) -> dict:
    """
    Full RAG pipeline: retrieve → format context → call LLM.

    Args:
        user_message:     The learner's question.
        badge_filter:     Optional badge_id to scope the retrieval.
        current_badge:    Human-readable name of the badge being worked on.
        progress_summary: Short text describing the learner's overall progress.

    Returns:
        {
            "answer":              str        — ZBot's response (follow-up section stripped),
            "follow_up_questions": list[str]  — 3 suggested deeper questions,
            "sources":             list[dict] — chunks with score > SOURCE_SCORE_THRESHOLD,
            "provider":            str        — LLM provider that responded,
            "error":               str | None — error message, or None on success,
        }
    """
    # 1. Retrieve relevant chunks
    chunks = retrieve(user_message, badge_filter=badge_filter, top_k=5)

    # 2. Build context string
    context_str = format_context(chunks)

    # 3. Render system prompt
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
        badge_catalog=BADGE_CATALOG,
        context=context_str,
        current_badge=current_badge,
        progress_summary=progress_summary,
    )

    # 4. Call LLM
    llm_result = get_llm_response(
        system_prompt=system_prompt,
        user_message=user_message,
    )

    # 5. Parse and strip follow-up questions from the answer
    answer, follow_up_questions = _extract_follow_up(llm_result["text"])

    # 6. Filter sources by relevance threshold
    sources = [c for c in chunks if c["score"] > SOURCE_SCORE_THRESHOLD]

    return {
        "answer":              answer,
        "follow_up_questions": follow_up_questions,
        "sources":             sources,
        "provider":            llm_result["provider"],
        "error":               llm_result["error"],
    }
