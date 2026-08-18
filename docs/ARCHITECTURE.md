# Tanvelo Architecture Deep Dive

Tanvelo is a universal, user-controlled long-term memory layer for AI developer tools. It provides shared contextual persistence across independent AI clients using the **Model Context Protocol (MCP)**, **FastAPI**, **NVIDIA Nemotron Nano 8B**, and **Supabase PostgreSQL with pgvector**.

---

## 1. System Architecture Diagram

```
                 MCP-Compatible AI Tools
       ┌───────────┬─────────────┬─────────────┐
       │  Cursor   │ Claude Code │  Codex CLI  │
       └─────┬─────┴──────┬──────┴──────┬──────┘
             │            │             │
             └────────────┼─────────────┘
                          │ MCP (stdio / SSE)
                          ▼
              ┌────────────────────────┐
              │   Tanvelo MCP Server   │
              └───────────┬────────────┘
                          │ Internal Service Layer
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
            ┌─────────────────────────────┐
            │   Duplicate Detection &     │
            │   Hybrid Ranking Service    │
            └─────────────┬───────────────┘
                          │
                          ▼
             Supabase PostgreSQL + pgvector
        (users, api_keys, memories with HNSW)
```

---

## 2. Core Operational Lifecycle

Every piece of context in Tanvelo goes through the 6-stage memory lifecycle:

```
Input Context
    ↓
1. Candidate Extraction & Evaluation (NVIDIA Nemotron Nano 8B)
    ↓
2. Vector Embedding Generation (1536-dim Normalized Vectors)
    ↓
3. Duplicate Detection (Cosine Similarity >= 0.90)
    ↓
4. Persistence & Scoping (Supabase PostgreSQL + pgvector, User Scoped)
    ↓
5. Hybrid Semantic Retrieval (0.60 Sim + 0.25 Imp + 0.15 Rec)
    ↓
6. Context Delivery & Deletion (MCP Context Block / Forget)
```

---

## 3. Memory Decision Engine (NVIDIA Nemotron Nano 8B)

The memory decision engine does not blindly save every message. It evaluates input against a strict 3-tier hybrid rule system:

1. **Explicit Directives**:
   - `"Remember that..."` $\rightarrow$ Always stored (`should_store: true`), high importance ($\ge 0.90$).
   - `"Don't remember this..."` $\rightarrow$ Always rejected (`should_store: false`).
2. **High-Value Technical Context**:
   - Technology stack choices, architectural rules, coding preferences, persistent project facts.
3. **Low-Value Filtering**:
   - Greetings, small talk, chit-chat, transitory commands $\rightarrow$ Rejected (`should_store: false`).
4. **Temporary Task Expiration**:
   - Information tied to short-term work (e.g. `"I'm fixing auth today"`) is tagged with `type: "temporary"` and an automatic 24-hour expiration timestamp.

---

## 4. Hybrid Ranking Algorithm

Retrieved memories are not ranked purely by cosine distance. Tanvelo uses a multi-factor hybrid scoring function:

$$\text{Recency Score} = \exp\left(-\frac{\Delta t \text{ (in days)}}{30.0}\right)$$

$$\text{Final Score} = w_{\text{sim}} \cdot \text{Similarity} + w_{\text{imp}} \cdot \text{Importance} + w_{\text{rec}} \cdot \text{Recency}$$

### Default Configured Weights
- $w_{\text{sim}} = 0.60$ (Semantic relevance)
- $w_{\text{imp}} = 0.25$ (Long-term architectural value)
- $w_{\text{rec}} = 0.15$ (Temporal freshness)

---

## 5. Duplicate Detection & In-Place Resolution

When a new memory candidate is extracted:
1. An embedding $\vec{v}_{\text{cand}}$ is generated.
2. An active vector search queries existing memories for the authenticated user.
3. If $\max(\text{similarity}) \ge 0.90$:
   - The existing memory record is updated in-place with the refreshed content, timestamps, and combined importance.
   - Action returned: `updated`.
4. If no existing memory meets the threshold:
   - A new record is inserted.
   - Action returned: `created`.
