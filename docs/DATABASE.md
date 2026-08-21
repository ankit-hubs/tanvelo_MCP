# Tanvelo Database & pgvector Specification

Tanvelo uses PostgreSQL with the **`pgvector`** extension for scalable vector storage and semantic retrieval. It is natively compatible with **Supabase PostgreSQL**, **Neon**, **AWS RDS/Aurora**, and self-hosted PostgreSQL 15+.

---

## 1. Schema Tables & Indexes

### `users`
Stores user accounts and timestamps.
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `api_keys`
Stores cryptographically hashed API keys (`tv_live_...`). Raw keys are never stored.
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
CREATE INDEX idx_api_keys_user_active ON api_keys(user_id, revoked_at);
```

### `memories`
Stores extracted facts, user preferences, 1536-dimensional embeddings, and expiration dates.
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

-- Fast tenant filtering & composite indexes
CREATE INDEX idx_memories_user_id ON memories(user_id);
CREATE INDEX idx_memories_expires_at ON memories(expires_at);
CREATE INDEX idx_memories_type ON memories(type);
CREATE INDEX idx_memories_created_at ON memories(created_at);
CREATE INDEX idx_memories_user_expires ON memories(user_id, expires_at);
CREATE INDEX idx_memories_user_project ON memories(user_id, project_id);

-- High-Performance HNSW Vector Index (Cosine Similarity)
CREATE INDEX idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

---

## 2. Connection Pooling & Tuning

Tanvelo utilizes SQLAlchemy AsyncSession with asyncpg connection pooling:
- `DB_POOL_SIZE`: Default `10` persistent connections.
- `DB_MAX_OVERFLOW`: Default `20` burst connections.
- `DB_POOL_TIMEOUT`: `30.0` seconds timeout.
- `DB_POOL_RECYCLE`: `1800` seconds (30 min) to prevent stale connections.
- `DB_POOL_PRE_PING`: True (verifies connection liveness before checkout).

---

## 3. Supported Cloud Database Providers

1. **Supabase PostgreSQL**:
   - Enable `vector` extension under Database -> Extensions.
   - Run `migrations/001_initial_schema.sql` in SQL Editor.
   - Connection URL: `postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres`

2. **Neon Serverless Postgres**:
   - Connection URL: `postgresql+asyncpg://[USER]:[PASSWORD]@[ENDPOINT].neon.tech/[DB]?ssl=require`

3. **AWS RDS / Aurora PostgreSQL**:
   - Ensure PostgreSQL 15.3+ or 16+ with `pgvector` enabled.
