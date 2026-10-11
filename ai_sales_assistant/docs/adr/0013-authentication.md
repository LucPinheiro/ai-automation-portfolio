# 0013. User authentication with server-side sessions

- Status: Accepted
- Date: 2026-10-07

## Context

The API and the web UI were public: anyone reaching the server could generate content (consuming the AI provider) and read every stored generation. Generations contain customer data, so each one must belong to the user who created it and be invisible to everybody else. The web UI is a same-origin, server-rendered app; Swagger must keep working.

## Decision

**Server-side sessions in an HttpOnly cookie.** Login creates a random 256-bit token (`secrets.token_urlsafe(32)`); the browser receives it in the `ai_sales_session` cookie (`HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` in production) and the database stores only its SHA-256 hash (`user_sessions`), with an expiry (`SESSION_TTL_HOURS`, default 7 days). JavaScript never sees or stores a token.

- Logout deletes the session row, so the old cookie stops working immediately.
- Changing or resetting the password deletes every session of the account; change-password then issues a fresh session to the current client (no session fixation).
- Passwords are hashed with **Argon2id** (`argon2-cffi`, library defaults) and rehashed on login when the parameters change. Length 8–128, no composition rules (NIST SP 800-63B). Hashes are never returned.
- Login answers unknown email and wrong password identically, and spends the same hashing work for unknown emails (no enumeration by message or timing). Registration answers 409 for a taken email — an accepted trade-off for a usable sign-up form without email verification.

**Ownership.** `generations.user_id` references `users.id`. Every repository query takes the owner's id and filters by it; another user's generation is answered with 404, exactly like a missing one. `user_id` is nullable only for generations created before accounts existed: they are invisible to everybody until assigned with `python -m app.cli assign-orphan-generations --email <owner>`.

**CSRF.** Cookie authentication needs CSRF protection. Three layers:
1. `SameSite=Lax`: browsers do not send the cookie on cross-site POST/PUT/DELETE.
2. An origin check middleware rejects (403 `csrf_failed`) any state-changing request whose `Origin`/`Referer` is not the app itself (the request host or `APP_BASE_URL`).
3. Request bodies are JSON only, which plain cross-site HTML forms cannot send.

**Password recovery.** `POST /auth/forgot-password` always answers 202 with the same message, and sends the email in a background task so timing does not reveal whether the account exists. The token is random (256 bits), stored only as a SHA-256 hash, expires after `PASSWORD_RESET_TTL_MINUTES` (30), is single-use (`used_at`) and is superseded by any newer request. The reset page removes the token from the address bar and is served with `Referrer-Policy: no-referrer`.

**Email delivery** is behind the `EmailSender` protocol: `console` (development: logs the message, refused in production) or `smtp` (standard library, STARTTLS).

**Web pages** `/app` and `/account` redirect to `/login?next=…` without a session; `next` only accepts same-site paths.

## Consequences

- Every generation endpoint requires a session; unauthenticated calls get 401 `not_authenticated`.
- Sessions live in the database: one indexed lookup per request, and expired rows are pruned at login.
- Tests use real registration and login through the API (with low-cost Argon2 parameters); a second client verifies isolation between users.
- Not included yet: rate limiting of login and recovery, email verification, account deletion. Rate limiting is the next recommended step.

## Alternatives considered

- **JWT in a cookie or in `localStorage`**: stateless, but logout and "log out everywhere" need a deny-list, and `localStorage` exposes the token to any XSS. Rejected.
- **CSRF token header (double submit)**: stronger in old browsers, but adds state to every page and breaks plain Swagger usage; the origin check plus SameSite covers modern browsers.
- **Assigning old generations to the first registered user**: whoever registered first would get the data. Rejected in favour of the explicit CLI command.
- **bcrypt**: acceptable, but Argon2id is the current OWASP recommendation and has no 72-byte input limit.
