"""
PDF ingestion pipeline for IBM Z Xplore.

Reads each badge PDF, chunks the content, embeds with sentence-transformers,
and upserts into a ChromaDB persistent collection.

Usage:
    python ingest.py
"""

import re
import sys
from pathlib import Path

import fitz  # PyMuPDF
import chromadb
from sentence_transformers import SentenceTransformer

from badge_config import BADGES

# ── Paths & constants ────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
PDFS_DIR = BASE_DIR / "pdfs"
CHROMA_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "zxplore_knowledge"

OVERVIEW_MAX = 800    # characters for the overview chunk
CHUNK_MAX = 1500      # max characters per content chunk
BATCH_SIZE = 50       # ChromaDB upsert batch size

# Matches step headings like "3 SUBMIT THE JOB" or "12 OPEN THE TERMINAL"
STEP_PATTERN = re.compile(r"(?m)^(\d+)\s{1,4}([A-Z][A-Z0-9 \-\/]{2,})\s*$")


# ── Text extraction ──────────────────────────────────────────────────────────

def extract_text(pdf_path: Path) -> str:
    """Return the full plain text of a PDF, page-joined with newlines."""
    doc = fitz.open(str(pdf_path))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


# ── Chunking helpers ─────────────────────────────────────────────────────────

def find_steps(text: str) -> list[tuple[str, str, str]]:
    """
    Detect step headings and split text accordingly.

    Returns a list of (step_number, step_title, step_body) tuples.
    step_body is truncated to CHUNK_MAX characters.
    """
    matches = list(STEP_PATTERN.finditer(text))
    if not matches:
        return []

    steps = []
    for i, match in enumerate(matches):
        step_num = match.group(1)
        step_title = match.group(2).strip()
        body_start = match.end()
        body_end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[body_start:body_end].strip()[:CHUNK_MAX]
        steps.append((step_num, step_title, body))

    return steps


def split_by_paragraphs(text: str) -> list[str]:
    """
    Fallback chunker: group paragraphs into chunks of at most CHUNK_MAX chars.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current_parts: list[str] = []
    current_len = 0

    for para in paragraphs:
        if current_len + len(para) > CHUNK_MAX and current_parts:
            chunks.append("\n\n".join(current_parts))
            current_parts = [para]
            current_len = len(para)
        else:
            current_parts.append(para)
            current_len += len(para)

    if current_parts:
        chunks.append("\n\n".join(current_parts))

    return chunks


# ── Chunk builder ────────────────────────────────────────────────────────────

def build_chunks(badge_id: str, text: str) -> list[dict]:
    """
    Produce all chunks for one badge.

    Each chunk dict contains:
        id, document, badge_id, badge_type, step_number, step_title, points, chunk_id
    """
    badge = BADGES[badge_id]
    base_meta = {
        "badge_id": badge_id,
        "badge_type": badge["type"],
        "points": badge["points"],
    }
    chunks: list[dict] = []

    # 1. Overview chunk ─ first OVERVIEW_MAX characters of the document
    overview_text = text[:OVERVIEW_MAX].strip()
    if overview_text:
        chunk_id = f"{badge_id}_overview"
        chunks.append({
            "id": chunk_id,
            "document": overview_text,
            **base_meta,
            "step_number": 0,
            "step_title": "Overview",
            "chunk_id": chunk_id,
        })

    # 2. Step-based chunks
    steps = find_steps(text)

    if steps:
        seen_step_ids: set[str] = set()
        for step_num, step_title, body in steps:
            if not body:
                continue
            base_chunk_id = f"{badge_id}_step_{step_num}"
            # Deduplicate: same step heading may repeat (e.g. page headers)
            # — merge body into the first occurrence instead of creating a dupe
            if base_chunk_id in seen_step_ids:
                for existing in chunks:
                    if existing["id"] == base_chunk_id:
                        existing["document"] = (
                            existing["document"] + "\n" + body
                        )[:CHUNK_MAX]
                        break
                continue
            seen_step_ids.add(base_chunk_id)
            chunks.append({
                "id": base_chunk_id,
                "document": f"{step_num} {step_title}\n{body}",
                **base_meta,
                "step_number": int(step_num),
                "step_title": step_title,
                "chunk_id": base_chunk_id,
            })
    else:
        # Fallback: paragraph-based chunks (skip the overview region)
        remaining = text[OVERVIEW_MAX:].strip()
        para_chunks = split_by_paragraphs(remaining)
        for i, para_text in enumerate(para_chunks):
            if not para_text:
                continue
            chunk_id = f"{badge_id}_para_{i}"
            chunks.append({
                "id": chunk_id,
                "document": para_text,
                **base_meta,
                "step_number": i,
                "step_title": f"Section {i + 1}",
                "chunk_id": chunk_id,
            })

    return chunks


# ── ChromaDB upsert ──────────────────────────────────────────────────────────

def upsert_batches(
    collection: chromadb.Collection,
    model: SentenceTransformer,
    all_chunks: list[dict],
) -> None:
    """Embed and upsert all chunks in BATCH_SIZE batches."""
    total = len(all_chunks)
    for start in range(0, total, BATCH_SIZE):
        batch = all_chunks[start : start + BATCH_SIZE]
        documents = [c["document"] for c in batch]
        embeddings = model.encode(documents, show_progress_bar=False).tolist()
        metadatas = [
            {
                "badge_id":   c["badge_id"],
                "badge_type": c["badge_type"],
                "step_number": c["step_number"],
                "step_title":  c["step_title"],
                "points":      c["points"],
                "chunk_id":    c["chunk_id"],
            }
            for c in batch
        ]
        ids = [c["id"] for c in batch]

        collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        end = min(start + BATCH_SIZE, total)
        print(f"  Upserted chunks {start + 1}–{end} / {total}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("Loading embedding model…")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    print(f"Connecting to ChromaDB at {CHROMA_DIR}")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    all_chunks: list[dict] = []
    skipped: list[str] = []

    for badge_id, badge in BADGES.items():
        pdf_name = badge.get("pdf")
        if not pdf_name:
            print(f"[SKIP] {badge_id} — no PDF configured")
            skipped.append(badge_id)
            continue

        pdf_path = PDFS_DIR / pdf_name
        if not pdf_path.exists():
            print(f"[SKIP] {badge_id} — file not found: {pdf_path.name}")
            skipped.append(badge_id)
            continue

        print(f"[READ] {badge_id} ← {pdf_path.name}")
        try:
            text = extract_text(pdf_path)
        except Exception as exc:
            print(f"[ERROR] {badge_id}: could not read PDF — {exc}", file=sys.stderr)
            skipped.append(badge_id)
            continue

        chunks = build_chunks(badge_id, text)
        print(f"       {len(chunks)} chunks (steps={len(find_steps(text))})")
        all_chunks.extend(chunks)

    # Global dedup safety-net: keep last occurrence per ID
    seen: dict[str, dict] = {}
    for chunk in all_chunks:
        seen[chunk["id"]] = chunk
    all_chunks = list(seen.values())

    print(f"\nEmbedding & upserting {len(all_chunks)} total chunks…")
    upsert_batches(collection, model, all_chunks)

    print(f"\nDone. Collection '{COLLECTION_NAME}' now has "
          f"{collection.count()} documents.")

    if skipped:
        print(f"\nSkipped badges ({len(skipped)}): {', '.join(skipped)}")


if __name__ == "__main__":
    main()
