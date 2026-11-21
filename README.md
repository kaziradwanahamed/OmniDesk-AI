# OmniDesk AI

Personal, project-based multi-LLM workspace with a canonical shared conversation,
seamless model switching, and backend-managed persistent context.

> **Status:** Phase 1 - Project Setup & Application Foundation (Implementation
> Blueprint, Chapter 30). Authentication, chat, provider adapters, and context
> assembly arrive in later phases.

## Stack

- **Frontend:** Next.js (App Router) + React + TypeScript + Tailwind CSS (runs locally)
- **Backend:** FastAPI (Python 3.13, Dockerized) + SQLAlchemy 2 async + Alembic
- **Database:** PostgreSQL 16 (Docker)

## Prerequisites

- Docker + Docker Compose v2
- Node.js 20+ (for the local frontend)

## Setup

```bash
cp .env.example .env     # adjust POSTGRES_PASSWORD etc. if desired
```

### Backend + database (Docker)

```bash
docker compose up --build        # starts PostgreSQL + FastAPI on :8000
# Liveness:  curl http://localhost:8000/health  ->  {"status":"ok"}
# Readiness: curl http://localhost:8000/ready   ->  {"status":"ready","database":"connected"}
```

### Database migrations (Alembic)

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade base
```

### Backend tests

```bash
docker compose exec backend pytest
```

### Frontend (local)

```bash
cd frontend
npm install
npm run dev            # http://localhost:3000
npx tsc --noEmit      # type-check
```
