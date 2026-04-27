# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

IBM Z Xplore AI Assistant — a RAG-based chatbot that answers questions about IBM Z Xplore learning badges using 17 badge PDFs as a knowledge base. Backend is complete; frontend (Next.js) is not yet built.

## Commands

### Backend

```bash
# Install dependencies
cd backend && pip install -r requirements.txt

# Run the API server
cd backend && uvicorn main:app --reload --port 8000

# Re-ingest PDFs into ChromaDB (only needed if PDFs change)
cd backend && python ingest.py

# Both ingest.py and rag.py use relative paths — always run from the backend/ directory
```

### Frontend (not yet created — will be Next.js)

```bash
cd frontend && npm install
cd frontend && npm run dev        # localhost:3000
cd frontend && npm run build
cd frontend && npm run lint
```

## Architecture

```
POST /chat
  → main.py (FastAPI)
  → rag.query()
      → retrieve() — sentence-transformers embed → ChromaDB cosine search
      → format_context() — renders chunks for prompt
      → llm.get_llm_response() — Gemini (primary) or Groq (fallback)
  → suggest_next_badge() — rule-based next badge recommendation
  → ChatResponse (answer, sources, provider, suggestion)
```

### Key files

| File | Role |
|---|---|
| `backend/main.py` | FastAPI app, 5 endpoints, in-memory progress store |
| `backend/rag.py` | Full RAG pipeline — retrieve, format context, query |
| `backend/llm.py` | LLM abstraction — Gemini + Groq with mutual failover |
| `backend/badge_config.py` | Badge catalog (17 badges), unlock rules, next-badge suggestions |
| `backend/ingest.py` | One-time PDF → ChromaDB ingestion script |

### Data model

- **17 badges** across 4 tiers: Fundamentals (7), Concepts (2), Advanced (5), AllStar (3)
- **ChromaDB collection** `zxplore_knowledge`: each badge → overview chunk + per-step chunks (or paragraph fallback). Embedding model: `all-MiniLM-L6-v2`.
- **User progress**: currently in-memory dict `{user_id: {badge_id: status}}`. Status values: `not_started | in_progress | completed`. Supabase is in requirements.txt but not yet wired up.

### Badge unlock rules (badge_config.py)

- `check_concepts_badge`: all 7 Fundamentals completed AND ≥ 2 Concepts badges done
- `check_advanced_badge`: ≥ 5 badges from the combined Advanced + AllStar pool done

### Environment variables

```
GEMINI_API_KEY=...
GROQ_API_KEY=...
LLM_PROVIDER=gemini   # or "groq"
```

Copy `backend/.env.example` → `backend/.env` before running.

### CORS / deployment targets

Backend allows `http://localhost:3000` and `*.vercel.app`. Frontend deploys to Vercel.

## Known gaps / what needs to be built

1. **Frontend** — Next.js app in `frontend/` (empty directory). Needs: chat UI, badge progress tracker, badge catalog view.
2. **Supabase persistence** — replace in-memory `_user_progress` in `main.py` with Supabase rows so progress survives server restarts.
3. **Authentication** — currently any client can read/write any `user_id`; needs auth layer.
4. **Tests** — no test suite exists yet.
