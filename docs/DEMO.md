# Tanvelo 2-Minute Hackathon Demo Script

This script walks through the live presentation flow demonstrating the core concept:
> **"Tell one AI once. Tanvelo remembers. Another AI knows."**

---

## 1. Demo Narrative

1. **Problem Statement**: Every AI tool (Cursor, Claude Code, Codex CLI) has isolated context. Developers waste time repeating the same architectural decisions, database choices, and preferences.
2. **Solution**: Tanvelo provides an independent, user-controlled memory layer accessible over MCP.
3. **Live Demonstration**:

### Step 1: Save Memory in AI Tool A (Cursor)
- User tells Cursor:
  > *"Remember that Tanvelo uses FastAPI, Supabase and pgvector."*
- Cursor invokes `save_memory`.
- Tanvelo analyzes the fact with **NVIDIA Nemotron Nano 8B**, generates vector embeddings, and stores it in PostgreSQL with pgvector.

### Step 2: Switch to AI Tool B (Claude Code)
- Open Claude Code in a clean terminal / fresh chat session.
- User asks Claude Code:
  > *"What backend and database am I using for Tanvelo?"*
- Claude Code retrieves context from Tanvelo via `get_context`.
- Claude Code answers:
  > *"You're using FastAPI for the backend and Supabase with pgvector for the database."*
- **Outcome**: The user never explained the stack to Claude Code!

### Step 3: Forget Memory
- User says:
  > *"Forget that Tanvelo uses Supabase."*
- Claude Code invokes `forget_memory`.
- Tanvelo deletes the fact.
- Subsequent searches confirm the memory is no longer returned.

---

## 2. Interactive Terminal Simulator

To run the complete automated 7-step presentation in your terminal:

```bash
source .venv/bin/activate
python scripts/run_demo.py
```
