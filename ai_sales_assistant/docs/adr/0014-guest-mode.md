# 0014. Guest mode and usernames

- Status: Accepted
- Date: 2026-10-08

## Context

People should be able to try the generator without creating an account ("Entrar sin iniciar sesión"), without making the API public and without weakening the isolation between users ([ADR 0013](0013-authentication.md)). The login form should also accept a username, but accounts only had an email.

## Decision

**A guest is a user.** `POST /api/v1/auth/guest` creates a `User` with `is_guest = true`, no email and no password, and a normal server-side session (HttpOnly cookie, CSRF origin check). Nothing in the generation endpoints changes: they still require a session, and every query is still filtered by the owner's `user_id`, so a guest only reaches its own generations and gets 404 for anybody else's.

- Guest sessions are shorter: `GUEST_SESSION_TTL_HOURS` (24) instead of 7 days.
- `RegisteredUserDep` rejects guests (403 `guest_not_allowed`) where an account is required (change password); `/account` redirects guests to `/app`.
- Guests cannot log in with credentials: login lookups only match registered users.
- Cost protection: each user counts its AI calls (`ai_generation_count`, generate + regenerate). Guests are limited to `GUEST_MAX_GENERATIONS` (10) and get 403 `guest_quota_exceeded` before any AI call; deleting generations does not give calls back. `GUEST_MODE_ENABLED=false` turns the feature off (403 `guest_mode_disabled`).

**Guest data is temporary.**
- Logout deletes the guest, its sessions and all its generations in one transaction (explicit deletes, not relying on `ON DELETE CASCADE`, which SQLite does not enforce by default).
- Guests whose sessions have all expired are purged with their generations whenever a new guest starts, and with `python -m app.cli purge-expired-guests`.
- Registering or logging in from a guest session moves the guest's generations to that account and deletes the guest. Only the browser holding the guest's HttpOnly cookie can do this.

**Usernames.** `users.username` is optional, unique and stored lowercased (3–30 characters: letters, digits, `.`, `_`, `-`; no `@`). Login takes an `identifier`: with `@` it is an email, otherwise a username. The former `email` key is still accepted.

**Schema** (migration `0003`): `users.username`, `users.is_guest`, `users.ai_generation_count`; `email` and `password_hash` become nullable, and a CHECK constraint (`ck_users_registered_has_credentials`) keeps them mandatory for registered accounts.

**Demo credentials.** The login page shows public demo credentials (`DEMO_USERNAME` / `DEMO_PASSWORD`, default `demo` / `demo123`) pre-filled. They are not an account: nothing is stored for them, and a login with them opens a guest session (same limits, isolation and deletion on logout). Each visitor gets a separate guest. The demo username is reserved and cannot be registered. `DEMO_LOGIN_ENABLED=false` (or disabling guest mode) turns them off.

**Works without JavaScript.** Both entry points are real HTML forms: `POST /login` and `POST /guest` (web routes, same origin check as the API) create the session, set the HttpOnly cookie and redirect with 303. `auth.js` only enhances them (spinner, inline errors). Our own `/static` files are served with `Cache-Control: no-cache`, so a browser never runs an outdated script against newer HTML or API. Browser end-to-end tests (`tests/e2e`) drive a real headless Chrome against a real server, with and without JavaScript.

## Consequences

- Anyone who can reach the server can generate content as a guest, within the per-guest limit. A global rate limit per IP (not implemented yet) is still recommended, especially with OpenAI.
- Guest rows are short-lived; the purge runs opportunistically, so expired guests may remain until the next guest starts or the command is run.

## Alternatives considered

- **Removing authentication from the endpoints**: rejected; data would no longer have an owner.
- **A single shared "guest" account**: every visitor would see everybody else's generations.
- **Keeping guest data after logout**: nobody could ever reach it again; it would only accumulate customer data.
