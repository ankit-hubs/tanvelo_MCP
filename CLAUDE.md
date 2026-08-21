# Tanvelo AI Memory Integration Instructions for Claude Code

## Autonomous Long-Term Memory Workflow

You have access to the **Tanvelo MCP Server** tools (`get_context`, `save_memory`, `search_memory`, `update_memory`, `forget_memory`, `list_memories`).

### 1. Pre-flight Context Retrieval (First Action on Every Request)
- When the user gives you a task or asks a question, ALWAYS start by querying Tanvelo memory using `get_context(query="<task or topic>")`.
- Integrate the retrieved context (technologies, database setups, coding conventions, project constraints) directly into your plan and solution.

### 2. Autonomous Implicit Memory Extraction
- Whenever the conversation establishes or modifies:
  - Technical architecture & framework choices
  - Database schema, indexing, and migration rules
  - Developer preferences and style guidelines
  - Critical bug fixes or lessons learned
- Automatically invoke `save_memory(content="...")` to persist the fact.
- You do NOT require the user to explicitly say "remember this" or "save to memory". Extract and store valuable long-term knowledge proactively.
