# Tanvelo Model Context Protocol (MCP) Integration Guide

Tanvelo communicates with AI developer tools through the standard **Model Context Protocol (MCP)**. Compatible AI clients connect to Tanvelo to save, search, assemble context, list, and forget memories.

---

## 1. Exponentiated MCP Tools

### `save_memory`
- **Purpose**: Evaluates, extracts, and stores important project facts or developer preferences.
- **Parameters**:
  - `content` (*string*, required): The text statement or context to store.
  - `type` (*string*, optional): Category (`project_fact`, `preference`, `decision`, `temporary`, etc.).
- **Response**:
```json
{
  "success": true,
  "memory_id": "mem_a83f9104b2c1",
  "action": "created",
  "stored": [
    {
      "id": "mem_a83f9104b2c1",
      "content": "Tanvelo uses FastAPI and Supabase with pgvector",
      "type": "project_fact",
      "importance": 0.95
    }
  ]
}
```

---

### `search_memory`
- **Purpose**: Finds memories relevant to a natural language query using semantic vector search.
- **Parameters**:
  - `query` (*string*, required): Search question or query.
  - `limit` (*integer*, optional, default: 5): Maximum results.
- **Response**:
```json
{
  "memories": [
    {
      "id": "mem_a83f9104b2c1",
      "content": "Tanvelo uses FastAPI and Supabase with pgvector",
      "type": "project_fact",
      "importance": 0.95,
      "similarity": 0.92
    }
  ]
}
```

---

### `get_context`
- **Purpose**: Assembles top relevant memories into a clean Markdown block ready for LLM injection.
- **Parameters**:
  - `query` (*string*, required): Current task or prompt.
  - `limit` (*integer*, optional, default: 5): Maximum items.
- **Response**:
```markdown
### [Tanvelo Long-Term Memory Context]
- **[project_fact]**: Tanvelo uses FastAPI and Supabase with pgvector *(importance: 0.95)*
- **[preference]**: User prefers Python for backend services *(importance: 0.90)*
```

---

### `forget_memory`
- **Purpose**: Deletes or invalidates a memory by ID or by semantic query.
- **Parameters**:
  - `memory_id` (*string*, optional): Exact memory ID (e.g. `mem_a83f9104b2c1`).
  - `query` (*string*, optional): Description to forget (e.g. `Forget that Tanvelo uses Supabase`).
- **Response**:
```json
{
  "success": true,
  "message": "Successfully forgotten 1 related memory(s).",
  "forgotten_ids": ["mem_a83f9104b2c1"]
}
```

---

### `list_memories`
- **Purpose**: Lists all active memories for the authenticated user.
- **Parameters**:
  - `limit` (*integer*, optional, default: 20): Maximum items to return.
- **Response**:
```json
{
  "total": 3,
  "memories": [
    {
      "id": "mem_a83f9104b2c1",
      "content": "Tanvelo uses FastAPI and Supabase with pgvector",
      "type": "project_fact",
      "importance": 0.95,
      "created_date": "2026-08-18T08:00:00Z",
      "updated_date": "2026-08-18T08:00:00Z",
      "expiration_date": null
    }
  ]
}
```

---

## 2. Client Setup & Configuration

### A. Cursor (`~/.cursor/mcp.json` or Workspace Settings)
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

### B. Claude Code (`~/.claude/settings.json` or `claude mcp add`)
```bash
claude mcp add tanvelo python -m app.mcp.runner --transport stdio
```
Or in `settings.json`:
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

### C. Agy CLI / Antigravity
Add to your `mcp_servers` configuration in `~/.gemini/antigravity-cli/config.json`:
```json
{
  "mcp_servers": {
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
