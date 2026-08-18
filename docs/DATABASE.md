# Tanvelo Database & pgvector Specification

Tanvelo uses PostgreSQL with the **`pgvector`** extension for persistent storage and semantic vector retrieval. It is natively compatible with **Supabase PostgreSQL** and self-hosted PostgreSQL 15+.

---

## 1. Schema Tables

### `users`
Stores user identities and account creation timestamps.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `api_keys`
Stores hashed API keys (`tv_live_...`). Raw keys are never stored.
```sql
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL DEFAULT 'Default Key',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
```

### `memories`
Stores extracted facts, user preferences, embeddings, and expiration dates.
```sql
CREATE TABLE memories (
    id VARCHAR(64) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    type VARCHAR(64) NOT NULL DEFAULT 'project_fact',
    importance FLOAT NOT NULL DEFAULT 0.5,
    confidence FLOAT NOT NULL DEFAULT 1.0,
    source VARCHAR(64) NOT NULL DEFAULT 'mcp',
    project_id VARCHAR(128) NULL,
    embedding vector(1536) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NULL
);

CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_expires_at ON memories(expires_at);
CREATE INDEX idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);
```

---

## 2. Setting Up Supabase

1. Create a project in [Supabase](https://supabase.com/).
2. Navigate to **Database** $\rightarrow$ **Extensions** and enable `vector`.
3. Open the **SQL Editor** and execute the migration file `migrations/001_initial_schema.sql`.
4. Copy the connection string into your `.env`:
   ```bash
   DATABASE_URL=postgresql+asyncpg://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-REF].supabase.co:5432/postgres
   ```
