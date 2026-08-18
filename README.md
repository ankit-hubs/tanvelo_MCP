# TANVELO — Universal AI Memory Layer

> **Connect Once. Remember Everywhere.**  
> *Phase 1 Hackathon MVP — Model Context Protocol (MCP) Memory Integration*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-Standard%202.0-8A2BE2)](https://modelcontextprotocol.io)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron%20Nano%208B-76B900?logo=nvidia)](https://build.nvidia.com)
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql)](https://supabase.com)
[![Tests](https://img.shields.io/badge/Tests-Passing%20(16/16)-brightgreen)]()

---

## 1. Executive Summary

Modern developers work across multiple AI tools such as **Cursor**, **Claude Code**, **Codex CLI**, and **Agy CLI**. Because each AI tool maintains isolated context, developers repeatedly re-explain their preferences, architecture decisions, database configurations, and workflows.

**Tanvelo** solves this fragmentation by providing an independent, user-controlled memory layer accessible over the **Model Context Protocol (MCP)**.

### The Core Promise:
> **"Tell one AI once. Tanvelo remembers. Another AI knows."**

---

## 2. Architecture

```
                 MCP-Compatible AI Tools
       ┌───────────┬─────────────┬─────────────┐
       │  Cursor   │ Claude Code │  Codex CLI  │
       └─────┬─────┴──────┬──────┴──────┬──────┘
             │            │             │
             └────────────┼─────────────┘
                          │ Model Context Protocol (MCP)
                          ▼
              ┌────────────────────────┐
              │   Tanvelo MCP Server   │
              │  (save, search, ctx,   │
              │   forget, list)        │
              └───────────┬────────────┘
                          │ Service Layer
                          ▼
              ┌────────────────────────┐
              │    FastAPI Backend     │
              └───────────┬────────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
┌──────────────────┐             ┌───────────────────┐
│ Memory Decision  │             │ Embedding Service │
│      Engine      │             │  (Vector Norm)    │
│ (Nemotron Nano)  │             └─────────┬─────────┘
└────────┬─────────┘                       │
         │                                 │
         └────────────────┬────────────────┘
                          ▼
             Supabase PostgreSQL + pgvector
        (users, api_keys, memories with HNSW)
```

---

## 3. Core Features

- **MCP Server**: 5 core tools (`save_memory`, `search_memory`, `get_context`, `forget_memory`, `list_memories`).
- **NVIDIA Nemotron Nano 8B Decision Engine**: Evaluates content, extracts atomic facts, estimates importance (0.0 to 1.0), detects temporary tasks, and rejects low-value chit-chat.
- **Supabase PostgreSQL + pgvector**: Scalable semantic vector search with HNSW indexing.
- **Hybrid Ranking Algorithm**: Combines $0.60 \times \text{Similarity} + 0.25 \times \text{Importance} + 0.15 \times \text{Recency}$.
- **Duplicate Memory Detection**: In-place memory updates for semantically identical facts ($\text{similarity} \ge 0.90$) to eliminate context bloat.
- **Automatic Expiration**: Short-term tasks expire cleanly and are never returned in search results.
- **Tenant Isolation**: Secure SHA-256 API key hashing (`tv_live_...`) with strict per-user database scoping.

---

## 4. Quickstart

### Prerequisites
- Python 3.11+
- Virtual environment (`venv`)

### Installation
```bash
# 1. Clone repository
git clone https://github.com/your-org/tanvelo.git
cd tanvelo

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment configuration
cp .env.example .env

# 5. Initialize database and generate test API key
python scripts/setup_db.py
```

### Running Tests
```bash
source .venv/bin/activate
pytest tests/ -v
```

### Starting the Servers
```bash
# Start FastAPI backend (HTTP/REST endpoints & Swagger docs at http://localhost:8000/docs)
uvicorn app.main:app --reload --port 8000

# Start Tanvelo MCP Server (stdio transport for Cursor / Claude Code)
python -m app.mcp.runner --transport stdio
```

---

## 5. Connecting AI Clients (MCP)

### Cursor (`~/.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "tanvelo": {
      "command": "python",
      "args": ["-m", "app.mcp.runner", "--transport", "stdio"],
      "cwd": "/path/to/tanvelo",
      "env": {
        "TANVELO_API_KEY": "tv_live_your_key_here"
      }
    }
  }
}
```

### Claude Code (`claude.json` or CLI)
```bash
claude mcp add tanvelo python -m app.mcp.runner --transport stdio
```

---

## 6. Live Hackathon Demo (2-Minute Script)

Run the interactive cross-AI demo simulation directly in your terminal:
```bash
source .venv/bin/activate
python scripts/run_demo.py
```

### Flow Walkthrough:
1. **AI Tool A (Cursor)**: User says *"Remember that Tanvelo uses FastAPI, Supabase and pgvector."* $\rightarrow$ Tanvelo stores memory.
2. **AI Tool B (Claude Code)**: User asks *"What backend and database am I using for Tanvelo?"* $\rightarrow$ Tanvelo retrieves context via `get_context`.
3. **AI Tool B answers accurately** without the user repeating themselves!
4. **Forget Memory**: User says *"Forget that Tanvelo uses Supabase."* $\rightarrow$ Tanvelo deletes the fact and verifies it is no longer returned.

---

## 7. Project Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System components, lifecycle, and ranking formula.
- [MCP.md](docs/MCP.md) — Tool specifications and client configuration guides.
- [DATABASE.md](docs/DATABASE.md) — Supabase PostgreSQL schema and pgvector indexes.
- [SECURITY.md](docs/SECURITY.md) — API key hashing, tenant isolation, and prompt defense.
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) — Local development and Docker setup.
- [DEMO.md](docs/DEMO.md) — Hackathon demo presentation script.

---

## 8. License

Apache 2.0. Built for the Hackathon MVP.
