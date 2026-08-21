# TANVELO — Universal AI Memory Layer

> **Connect Once. Remember Everywhere.**  
> *Production-Ready Model Context Protocol (MCP) Memory Engine for AI Developer Tools*

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![MCP](https://img.shields.io/badge/MCP-Standard%202.0-8A2BE2)](https://modelcontextprotocol.io)
[![NVIDIA Nemotron](https://img.shields.io/badge/NVIDIA-Nemotron%20Nano%208B-76B900?logo=nvidia)](https://build.nvidia.com)
[![PostgreSQL + pgvector](https://img.shields.io/badge/PostgreSQL-pgvector-336791?logo=postgresql)](https://supabase.com)
[![Tests](https://img.shields.io/badge/Tests-Passing%20(25/25)-brightgreen)]()
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)]()

---

## 1. Executive Summary

Modern software engineers work across multiple AI programming assistants — including **Cursor**, **Claude Code**, **Windsurf**, **Codex CLI**, and **Agy CLI**. Because each AI tool maintains isolated context, developers are forced to constantly re-explain their architecture decisions, database configurations, coding preferences, and workflow rules.

**Tanvelo** eliminates context silos by providing a high-performance, user-controlled long-term memory engine accessible over the **Model Context Protocol (MCP)** and **REST API**.

### The Core Value:
> **"Tell one AI once. Tanvelo remembers. Every AI tool knows."**

---

## 2. Production Architecture

```
                       MCP-Compatible AI Clients
        ┌───────────┬─────────────┬─────────────┬─────────────┐
        │  Cursor   │ Claude Code │  Windsurf   │  Codex/Agy  │
        └─────┬─────┴──────┬──────┴──────┬──────┴──────┬──────┘
              │            │             │             │
              └────────────┼─────────────┴─────────────┘
                           │ Model Context Protocol (MCP stdio / SSE)
                           ▼
               ┌────────────────────────┐
               │   Tanvelo MCP Server   │
               │   (9 Enterprise Tools) │
               └───────────┬────────────┘
                           │ Service Layer
                           ▼
               ┌────────────────────────┐
               │    FastAPI Backend     │
               │  (Security Middlewares │
               │   & Rate Limiting)     │
               └───────────┬────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
 ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
 │ Memory Decision  │ │ LRU In-Memory    │ │ Embedding Engine │
 │      Engine      │ │ Embedding Cache  │ │ (NVIDIA / OpenAI │
 │ (Nemotron Nano / │ │   (<1ms hit)     │ │  / Ollama / NIM) │
 │  OpenAI/Anthropic│ └────────┬─────────┘ └────────┬─────────┘
 └────────┬─────────┘          │                    │
          │                    └──────────┬─────────┘
          └────────────────┬──────────────┘
                           ▼
             PostgreSQL 16 + pgvector (HNSW)
       (Tenants, API Keys, Semantic Vectors, Cascades)
```

---

## 3. Real-World Enterprise Features

- **9 Production MCP Tools**:
  - `save_memory`: Intelligent extraction, categorization, project scoping, and storage.
  - `search_memory`: Semantic vector search with hybrid ranking and project filters.
  - `get_context`: Formats top relevant memories into a concise markdown context block for prompt injection.
  - `update_memory`: Direct in-place modification of memory content, category, or importance.
  - `forget_memory`: ID-based or natural language semantic memory invalidation.
  - `list_memories`: Paginated memory retrieval with project and category filtering.
  - `get_memory_stats`: Real-time analytics on memory volume, active tasks, categories, and projects.
  - `cleanup_expired_memories`: Automatic & on-demand purging of transient tasks.
  - `export_memories`: Instant export in Markdown or JSON format for backup and migration.
- **Multi-Provider Decision Engine**: Powered by NVIDIA Nemotron Nano 8B, OpenAI (GPT-4o-mini), Anthropic Claude 3.5 Haiku, Ollama local models, and zero-dependency deterministic fallback.
- **Database-Level Vector Acceleration**: PostgreSQL + `pgvector` with **HNSW** indexing for sub-millisecond similarity queries across hundreds of thousands of memories.
- **LRU In-Memory Embedding Cache**: Caches vector embeddings to deliver sub-millisecond response times and eliminate redundant API calls.
- **Hybrid Ranking Algorithm**: Combines $0.60 \times \text{Similarity} + 0.25 \times \text{Importance} + 0.15 \times \text{Recency}$.
- **Duplicate Memory Detection**: In-place updates for semantically identical statements ($\ge 0.85$ similarity) to prevent context fragmentation.
- **Security & Hardening**:
  - Secure SHA-256 API key hashing (`tv_live_...`) with instant revocation support.
  - Strict tenant isolation and multi-project namespace scoping.
  - Sliding-window rate limiting middleware.
  - Prompt injection pattern defense and control-character sanitization.
  - Security headers (`HSTS`, `X-Content-Type-Options`, `X-Frame-Options`, `CSP`).
  - Correlation ID tracking (`X-Request-ID`) on all requests and structured logs.
  - Kubernetes / Cloud liveness (`/health/live`) and readiness (`/health/ready`) probes.

---

## 4. Quickstart

### Prerequisites
- Python 3.11+
- PostgreSQL 16 with `pgvector` (or local SQLite for embedded testing)
- Docker & Docker Compose (optional for containerized deployments)

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

# 5. Initialize database schema
python -m app.cli db init
```

### Running Tests
```bash
source .venv/bin/activate
pytest tests/ -v
```

---

## 5. Unified CLI Tool (`tanvelo`)

Tanvelo comes with a CLI tool for server management, key generation, and memory administration:

```bash
# Start backend API server
python -m app.cli serve --port 8000

# Start MCP Server for desktop AI clients
python -m app.cli mcp --transport stdio

# Generate API key
python -m app.cli keys create --email dev@example.com --name "Cursor Key"

# List API keys
python -m app.cli keys list --email dev@example.com

# Revoke API key
python -m app.cli keys revoke <key_id> --email dev@example.com

# Save memory from terminal
python -m app.cli memory save "Tanvelo uses pgvector for semantic search" --email dev@example.com --project core

# Search memory
python -m app.cli memory search "vector database" --email dev@example.com

# View memory analytics
python -m app.cli memory stats --email dev@example.com
```

---

## 6. Connecting AI Clients (MCP)

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

### Windsurf (`~/.codeium/windsurf/mcp_config.json`)
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

---

## 7. Docker & Production Deployment

### Docker Compose (Full Stack with PostgreSQL + pgvector)
```bash
# Build and start all services
docker-compose up -d

# Check health status
docker-compose ps
curl http://localhost:8000/health/ready
```

### Kubernetes Readiness & Liveness
- **Liveness Probe**: `GET /health/live` (200 OK)
- **Readiness Probe**: `GET /health/ready` (200 OK when DB and embedding caches are operational)

---

## 8. Documentation Index

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — System components, pgvector indexing, and ranking algorithms.
- [MCP.md](docs/MCP.md) — Complete 9 MCP tool specifications and client configurations.
- [DATABASE.md](docs/DATABASE.md) — PostgreSQL pgvector schema and index tuning.
- [SECURITY.md](docs/SECURITY.md) — API key hashing, prompt injection defenses, and rate limiting.
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) — Local development, test suites, and CI workflows.
- [DEMO.md](docs/DEMO.md) — Live cross-AI demonstration scenario.

---

## 9. License

Apache 2.0. Built for production-grade universal AI memory.
