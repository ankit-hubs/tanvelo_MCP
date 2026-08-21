# Universal AI Agent & Tool Memory Instructions (AGENTS.md)
> *Standardized directive for all AI IDEs, Autonomous Coding Agents, and Terminal CLIs.*

## Tanvelo Universal Memory Layer Protocol

This repository is integrated with **Tanvelo** via the **Model Context Protocol (MCP)**.
All AI agents, coding assistants, IDE extensions, and CLI tools interacting with this codebase MUST adhere to the following protocol:

---

### 1. Mandatory Pre-Flight Memory Check
**Before answering any user question, planning architecture, modifying files, or generating code:**
- **Action**: You MUST first query Tanvelo memory using the MCP tool:
  ```json
  get_context(query="<user query or task summary>")
  ```
- **Goal**: Retrieve existing architectural decisions, technical conventions, database setups, and developer preferences.
- **Rule**: Do NOT make assumptions or ask the user to repeat information already present in Tanvelo memory.

---

### 2. Autonomous Implicit Memory Ingestion
**Whenever the conversation establishes, modifies, or confirms durable knowledge:**
- Technical architecture, framework choices, and library versions
- Database configurations, schemas, and indexing strategies
- API contracts, endpoint structures, and serialization formats
- Coding standards, naming conventions, and developer preferences
- Critical bug resolutions and project-specific caveats

- **Action**: You MUST automatically persist the fact in the background using the MCP tool:
  ```json
  save_memory(content="<concise factual statement>", type="<project_fact|preference|decision>")
  ```
- **Rule**: Do NOT wait for explicit user instructions like *"remember this"* or *"save to memory"*. Persist valuable knowledge proactively.

---

### 3. Noise & Transient Data Exclusion
- Do NOT store transient debugging output, temporary file paths, or casual greetings.
- If the user explicitly states *"Don't remember this"* or *"Off the record"*, bypass storage completely.

---

### 4. Seamless In-Place Updates
- If a prior architectural decision or configuration changes (e.g. database migration or library upgrade), invoke `save_memory` or `update_memory` with the updated fact. Tanvelo's semantic duplicate engine will update the existing memory in-place.
