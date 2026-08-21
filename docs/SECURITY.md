# Tanvelo Security & Tenant Isolation Policy

Security, user privacy, and complete tenant isolation are core architectural requirements in Tanvelo.

---

## 1. Authentication & API Key Security

- **Cryptographic Hashing**: Raw API keys (`tv_live_<random_hex>`) are displayed once upon creation and are **never** stored in plaintext. Only SHA-256 hashes are persisted in the database.
- **Timing Attack Resistance**: API key lookup uses indexed SHA-256 hashes.
- **Instant Revocation**: Keys can be immediately revoked via `DELETE /v1/auth/keys/{key_id}` or `tanvelo keys revoke`. Revoked keys are rejected with HTTP 401.
- **Multi-Key Support**: Users can issue separate API keys for individual AI tools (Cursor, Claude Code, Windsurf) with distinct names and usage tracking.

---

## 2. Mandatory Multi-Tenant Data Isolation

Every memory query, retrieval, search, context assembly, and deletion operation is strictly scoped to the authenticated `user_id` resolved from the API key:

```python
# Guaranteed isolation in SQL:
stmt = select(Memory).where(
    Memory.user_id == authenticated_user.id,
    ...
)
```

- **Zero Cross-Tenant Leakage**: A client authenticated as User A cannot read, query, search, update, or delete memories belonging to User B under any circumstances.
- **Client User ID Ignored**: The backend never accepts a `user_id` parameter from the client as the authority for data access. The user identity is derived exclusively from the verified API key hash.

---

## 3. Defense-in-Depth & Operational Protections

- **Sliding-Window Rate Limiter**: Automatically throttles excessive requests per API key / IP (configurable via `RATE_LIMIT_PER_MINUTE`), mitigating DoS attempts and API key brute-forcing.
- **Prompt Injection Defense**: Input text is evaluated against adversarial jailbreak signatures and control-character anomalies before reaching LLMs.
- **Input Sanitization**: Control characters, null bytes, and malicious escape sequences are stripped on arrival.
- **Request Body Size Limits**: Enforces a strict 2MB maximum payload limit to prevent memory exhaustion attacks.
- **Security Headers**: Injects `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `X-XSS-Protection`, `Referrer-Policy`, and `Strict-Transport-Security` (HSTS).
- **Correlation ID Tracking**: Generates or propagates `X-Request-ID` across every request for end-to-end auditability and log correlation.
- **Safe JSON Validation**: All LLM outputs are parsed in safe isolation and strictly validated via Pydantic schemas.
