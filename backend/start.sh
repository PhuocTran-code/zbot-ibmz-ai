#!/usr/bin/env bash
set -e

# Re-ingest only if the ChromaDB index is missing (first deploy or volume reset)
if [ ! -f "chroma_db/chroma.sqlite3" ]; then
  echo "ChromaDB not found — running ingestion (this takes ~2 min)..."
  python3 ingest.py
fi

exec python3 -m uvicorn main:app \
  --host 0.0.0.0 \
  --port "${PORT:-8000}"
