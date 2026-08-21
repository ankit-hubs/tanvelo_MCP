# Tanvelo Model Context Protocol (MCP) Integration Guide

Tanvelo communicates with AI developer tools through the standard **Model Context Protocol (MCP)**. Compatible AI clients connect to Tanvelo to persist facts, retrieve context, modify memories, and manage project knowledge across all development tools.

---

## 1. Complete Suite of 9 MCP Tools

### 1. `save_memory`
- **Purpose**: Evaluates, extracts, categorizes, and persists facts, preferences, and architecture decisions.
- **Parameters**:
  - `content` (*string*, required): The text statement or context to store.
  - `type` (*string*, optional): Category (`project_fact`, `preference`, `decision`, `temporary`, etc.).
  - `importance` (*number*, optional, `0.0` - `1.0`): Explicit importance override.
  - `project_id` (*string*, optional): Project namespace for multi-repository scoping.
  - `force_store` (*boolean*, optional, default: `false`): Direct persistence bypassing LLM evaluation.

---

### 2. `search_memory`
- **Purpose**: Executes semantic vector search with hybrid ranking ($0.60 \times \text{Sim} + 0.25 \times \text{Imp} + 0.15 \times \text{Rec}$).
- **Parameters**:
  - `query` (*string*, required): Search question or statement.
  - `limit` (*integer*, optional, default: `5`): Maximum results.
  - `project_id` (*string*, optional): Filter to specific project namespace.
  - `type` (*string*, optional): Filter by category.

---

### 3. `get_context`
- **Purpose**: Assembles top relevant memories into a clean Markdown block formatted for direct LLM prompt injection.
- **Parameters**:
  - `query` (*string*, required): Current user task or question.
  - `limit` (*integer*, optional, default: `5`): Maximum memories to include.
  - `project_id` (*string*, optional): Scope context to project.
  - `max_characters` (*integer*, optional, default: `4000`): Maximum token/character budget.

---

### 4. `update_memory`
- **Purpose**: Directly modifies an existing memory without creating duplicates.
- **Parameters**:
  - `memory_id` (*string*, required): ID of target memory.
  - `content` (*string*, optional): Updated fact statement.
  - `type` (*string*, optional): Updated category.
  - `importance` (*number*, optional): Updated importance score.

---

### 5. `forget_memory`
- **Purpose**: Deletes or invalidates a memory by exact ID or semantic query.
- **Parameters**:
  - `memory_id` (*string*, optional): Exact memory ID (e.g. `mem_a83f9104b2c1`).
  - `query` (*string*, optional): Natural language instruction (e.g. `Forget that Tanvelo uses Supabase`).

---

### 6. `list_memories`
- **Purpose**: Lists active unexpired memories with pagination and metadata.
- **Parameters**:
  - `limit` (*integer*, optional, default: `20`): Page size.
  - `offset` (*integer*, optional, default: `0`): Pagination offset.
  - `project_id` (*string*, optional): Filter by project.
  - `type` (*string*, optional): Filter by category.

---

### 7. `get_memory_stats`
- **Purpose**: Retrieves analytical summary of memory counts, active vs expired breakdown, and project distribution.

---

### 8. `cleanup_expired_memories`
- **Purpose**: Purges all expired temporary tasks and notes from the database.

---

### 9. `export_memories`
- **Purpose**: Exports user memories formatted as structured Markdown or JSON.
- **Parameters**:
  - `format` (*string*, optional, default: `'markdown'`): `'markdown'` or `'json'`.
  - `project_id` (*string*, optional): Scope export to specific project.

---

## 2. Client Configurations

### A. Cursor (`~/.cursor/mcp.json`)
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

### B. Claude Code (`claude.json` or CLI)
```bash
claude mcp add tanvelo python -m app.mcp.runner --transport stdio
```

### C. Windsurf (`~/.codeium/windsurf/mcp_config.json`)
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

### D. Remote Cloud MCP (SSE Transport)
```bash
python -m app.mcp.runner --transport sse --port 8001
```
Configure your remote client to point to `http://your-server:8001/sse`.
