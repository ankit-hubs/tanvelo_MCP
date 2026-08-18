# Tanvelo Security & Tenant Isolation Policy

Security, user privacy, and complete tenant isolation are core architectural requirements in Tanvelo.

---

## 1. Authentication & API Key Security

- **Cryptographic Hashing**: Raw API keys (`tv_live_<random_hex>`) are displayed once upon generation and are **never** stored in plaintext. Only SHA-256 hashes are persisted in `api_keys.key_hash`.
- **Timing Attack Resistance**: Database queries compare precomputed SHA-256 hashes with constant-time equality comparisons.
- **Revocation**: Keys can be immediately revoked via `revoked_at` timestamp. Revoked keys are rejected with HTTP 401.

---

## 2. Mandatory Tenant Data Isolation

Every memory query, retrieval, search, context assembly, and deletion operation is strictly scoped to the authenticated `user_id` resolved from the API key:

```python
# Guaranteed isolation in SQL:
stmt = select(Memory).where(
    Memory.user_id == authenticated_user.id,
    ...
)
```

- **Zero Cross-Tenant Leakage**: A client authenticated as User A cannot read, query, search, update, or delete memories belonging to User B under any circumstances.
- **Client User ID Ignored**: The backend never accepts a `user_id` parameter from the client as the authority for data access. The user identity is solely derived from the verified API key hash.

---

## 3. Safe LLM Execution & Sanitization

- **No Raw Model Execution**: Output from NVIDIA Nemotron Nano 8B is strictly parsed as JSON, sanitized against malformed markdown fences, and validated with Pydantic schemas before being processed.
- **Privacy Filtering**: When users instruct the system with `"Don't remember this"` or `"Off the record"`, persistent memory creation is unconditionally bypassed.
- **No Stack Trace Leaks**: All unexpected internal errors are caught by global exception handlers and return sanitized JSON error envelopes with structured error codes.
