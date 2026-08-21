-- Tanvelo Database Schema for PostgreSQL with pgvector (Supabase / Self-Hosted / AWS RDS / Neon)
-- Version: 1.0 Enterprise Production

-- 1. Enable vector and UUID extensions
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Users Table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 3. API Keys Table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL DEFAULT 'Default Key',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMPTZ NULL,
    revoked_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_active ON api_keys(user_id, revoked_at);

-- 4. Memories Table
CREATE TABLE IF NOT EXISTS memories (
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

-- 5. Indexes for fast retrieval, user isolation, and multi-tenancy
CREATE INDEX IF NOT EXISTS idx_memories_user_id ON memories(user_id);
CREATE INDEX IF NOT EXISTS idx_memories_expires_at ON memories(expires_at);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
CREATE INDEX IF NOT EXISTS idx_memories_user_expires ON memories(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_memories_user_project ON memories(user_id, project_id);

-- 6. Vector Index (HNSW for high-performance sub-millisecond cosine similarity search)
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops);
