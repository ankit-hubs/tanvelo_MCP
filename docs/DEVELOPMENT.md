# Tanvelo Local Development Guide

## 1. Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

---

## 2. Quickstart

### Step 1: Clone and Set Up Virtual Environment
```bash
git clone <repo_url> tanvelo
cd tanvelo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Configure Environment
```bash
cp .env.example .env
# Edit .env with your NVIDIA_API_KEY if testing live Nemotron LLM
```

### Step 3: Run Tests
```bash
source .venv/bin/activate
pytest tests/ -v
```

### Step 4: Provision Credentials & Seed Data
```bash
source .venv/bin/activate
python scripts/setup_db.py
```

### Step 5: Start FastAPI Backend
```bash
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000
```
Open [http://localhost:8000/docs](http://localhost:8000/docs) to view Swagger UI.

### Step 6: Start MCP Server
```bash
source .venv/bin/activate
python -m app.mcp.runner --transport stdio
```

---

## 3. Running with Docker Compose (PostgreSQL + pgvector)

```bash
docker-compose up --build
```
This automatically boots:
- PostgreSQL 16 container with `pgvector` pre-configured on port 5432
- Tanvelo FastAPI backend container on port 8000 with auto-reload
