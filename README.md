# ZBot — IBM Z Xplore AI Assistant

A RAG-based chatbot that answers questions about **IBM Z Xplore** learning badges, tracks your progress through 17 badges across 4 tiers, and suggests what to study next.

## Live Demo

| Service | URL |
|---|---|
| **Chatbot (Frontend)** | https://zbot-ibmz-ai.vercel.app |
| **Backend API** | https://zbot-ibmz-ai.onrender.com |
| **API Docs (Swagger)** | https://zbot-ibmz-ai.onrender.com/docs |
| **GitHub Repository** | https://github.com/PhuocTran-code/zbot-ibmz-ai |

> **Note:** The backend runs on Render's free tier — the first request after a period of inactivity may take 30–60 seconds to cold-start.

---

## Features

- **AI-powered Q&A** — Ask anything about IBM Z Xplore badge content. Answers are grounded in the official badge PDFs via RAG (Retrieval-Augmented Generation).
- **Badge progress tracker** — Mark each of the 17 badges as Not Started / In Progress / Completed directly in the sidebar.
- **Smart badge filter** — Focus the chatbot on a specific badge for targeted answers.
- **Next-badge suggestions** — The system recommends which badge to tackle next based on your current progress.
- **Follow-up questions** — Each answer includes suggested follow-up questions to deepen understanding.
- **Persistent progress** — Progress is stored in Supabase and survives page refreshes and browser sessions.
- **Dual LLM** — Gemini (primary) with Groq as automatic fallback; zero downtime when one provider is unavailable.

---

## Badge System

17 badges across 4 tiers:

| Tier | Count | Unlock Condition |
|---|---|---|
| **Fundamentals** | 7 | Available from the start |
| **Concepts** | 2 | Complete all 7 Fundamentals |
| **Advanced** | 5 | Complete ≥ 5 badges from Advanced + AllStar pool |
| **AllStar** | 3 | Complete ≥ 5 badges from Advanced + AllStar pool |

---

## Architecture

```
Browser (Next.js)
  │
  ├── BadgeSidebar   — badge list, tier grouping, progress controls
  └── ChatPanel      — chat UI, filter chip, follow-up questions
        │
        ▼
  POST /chat  (FastAPI — Render)
        │
        ├── rag.retrieve()     — Gemini embeddings → ChromaDB cosine search
        ├── rag.format_context() — render chunks into prompt
        ├── llm.get_llm_response() — Gemini / Groq
        └── suggest_next_badge()  — rule-based next-badge logic
              │
              ▼
        ChatResponse { answer, sources, provider, suggestion, follow_up_questions }
```

### Key files

| Path | Role |
|---|---|
| `backend/main.py` | FastAPI app — 5 endpoints, Supabase + in-memory progress store |
| `backend/rag.py` | Full RAG pipeline — retrieve, format context, query |
| `backend/llm.py` | LLM abstraction — Gemini + Groq with mutual failover |
| `backend/badge_config.py` | 17-badge catalog, unlock rules, next-badge suggestions |
| `backend/ingest.py` | One-time PDF → ChromaDB ingestion script |
| `frontend/components/BadgeSidebar.tsx` | Badge list UI with progress controls |
| `frontend/components/ChatPanel.tsx` | Chat interface |
| `frontend/lib/api.ts` | API client for all backend calls |

---

## Tech Stack

**Backend**
- Python 3.11, FastAPI, Uvicorn
- ChromaDB (vector store) + `gemini-embedding-001` (768-dim, via Gemini API)
- Google Gemini API (chat + embeddings) + Groq API (fallback)
- Supabase (PostgreSQL) for progress persistence
- Docker → deployed on **Render**

**Frontend**
- Next.js 15 (App Router), TypeScript, Tailwind CSS
- Deployed on **Vercel**

---

## Local Development

### Prerequisites

- Python 3.11+, Node.js 18+
- Gemini API key ([Google AI Studio](https://aistudio.google.com/))
- Groq API key ([Groq Console](https://console.groq.com/)) — optional fallback

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Fill in GEMINI_API_KEY (and optionally GROQ_API_KEY, SUPABASE_URL, SUPABASE_KEY)

# Ingest PDFs into ChromaDB (only needed once, or when PDFs change)
python ingest.py

# Start the API server
uvicorn main:app --reload --port 8000
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

### Frontend

```bash
cd frontend
npm install

# Point at local backend
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:3000
```

### Run tests

```bash
# Backend
cd backend && python -m pytest tests/ -v

# Frontend
cd frontend && npm test
```

---

## Deployment

### Backend → Render

The repo includes `render.yaml`. Connect the GitHub repo in Render, set the required environment variables, and deploy:

```
GEMINI_API_KEY=...
GROQ_API_KEY=...
LLM_PROVIDER=gemini
SUPABASE_URL=...
SUPABASE_KEY=...
```

### Frontend → Vercel

Connect the GitHub repo in Vercel, set the root directory to `frontend/`, and add:

```
NEXT_PUBLIC_API_URL=https://zbot-ibmz-ai.onrender.com
```

### Database (Supabase)

Run the migration in your Supabase SQL editor:

```sql
-- backend/migrations/001_user_progress.sql
```

---

## Environment Variables

| Variable | Where | Required | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Backend | Yes | Google Gemini API key |
| `GROQ_API_KEY` | Backend | No | Groq fallback key |
| `LLM_PROVIDER` | Backend | No | `gemini` (default) or `groq` |
| `SUPABASE_URL` | Backend | No | Supabase project URL |
| `SUPABASE_KEY` | Backend | No | Supabase anon/service-role key |
| `NEXT_PUBLIC_API_URL` | Frontend | Yes | Backend base URL |
