---
id: AUTH
title: Auth & Security
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 6 — Auth & Security

Companion to [`0-business-logic.md`](0-business-logic.md) §9.3 (the `User` entity) and
[`5-deployment.md`](5-deployment.md) (secrets).

The goal is the smallest auth that is genuinely correct. Not the most featured, and not a toy. Every
decision below is written with its reasoning, because the reasoning is what gets asked about.

## 1. Decisions

### 1.1 JWT in an httpOnly cookie

**AUTH-001.** Three options were on the table.

| Option | Problem |
|---|---|
| JWT in `localStorage` | Readable by any script on the page. One XSS and the session is gone. This is the default an agent will reach for, and it is the wrong one. |
| Server-side session | Requires server state. Workable now that we have a volume, but it adds a store and an expiry sweep for no benefit at this scope. |
| **JWT in an httpOnly cookie** | Chosen. Unreadable by JavaScript, sent automatically, no server state. |

The cost of the cookie approach is CSRF exposure, and that is handled below.

### 1.2 No refresh token

**AUTH-002.** One access token, 24-hour lifetime, no refresh, no rotation.

Refresh tokens exist to keep access tokens short-lived when the access token is a bearer token
handled by JavaScript. With an httpOnly cookie and a session that is expected to last one sitting,
a refresh pair adds a second token, a second endpoint, rotation logic and a revocation story, and
buys nothing here.

**AUTH-003.** Flagged in the README as the first thing to add for a real deployment, alongside a
token denylist for logout-everywhere.

### 1.3 SameSite=Lax instead of a CSRF token

**AUTH-004.** The application is a single origin: the API and the SPA are served from the same
container and the same domain (`5-deployment.md` DEP-001). `SameSite=Lax` stops the cookie being sent
on cross-site POST, PUT and DELETE, which covers every state-changing request in this application.

**AUTH-005.** A separate CSRF token would be correct if the API were consumed cross-origin. It is
not, so the token would be ceremony. Say this out loud rather than leaving it looking like an
oversight.

### 1.4 argon2id for passwords

**AUTH-006.** `argon2-cffi` directly, not through a wrapper library. argon2id is the current
recommendation and the library is small and maintained.

**AUTH-007.** Never `sha256`, never `md5`, never plaintext, not even with obviously fake test data.
This is fintech, and it is the first thing anyone looks at.

## 2. Not built

**AUTH-008.**

| Not built | Why |
|---|---|
| Email verification | The brief explicitly allows stubbing email. A verification flow with no mail transport is theatre. |
| Password reset | Same reason: it needs email to be meaningful. |
| Refresh tokens and rotation | See AUTH-002. |
| Account lockout after N failures | Rate limiting covers the demo. Lockout needs persistent counters and an unlock path. |
| 2FA, OAuth, SSO | Out of scope for a four-screen portal. |
| Roles and permissions | One role: a borrower who owns their own data. No advisor or analyst persona in this build. |

## 3. Password handling

**AUTH-009.** Hashing lives in `domains/auth/security.py`.

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    """Hash a password with argon2id."""
    return _hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Check a password against its hash.

    Returns False on mismatch rather than raising, so callers do not have to
    distinguish a wrong password from an error.
    """
    try:
        return _hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
```

**AUTH-010.** Password rules, deliberately minimal: **minimum 10 characters, no other constraints.**
Composition rules (one uppercase, one digit, one symbol) reduce entropy in practice and annoy users.
Length is what matters.

**AUTH-011.** The plaintext password never appears in a log, a span attribute, an error message or a
response. It exists inside the request model and the hashing call, and nowhere else.
→ `5-deployment.md` DEP-031, DEP-035.

## 4. Token

**AUTH-012.**

```json
{
  "sub": "<user uuid>",
  "iat": 1756400000,
  "exp": 1756486400,
  "iss": "borrower-portal"
}
```

- **AUTH-013** — `HS256`, secret from the `JWT_SECRET` environment variable.
- **AUTH-014** — **The secret is fixed in the environment, never generated at startup.** A generated
  secret invalidates every token on restart, which on Fly means every redeploy logs everyone out.
  `5-deployment.md` DEP-021 sets it with `fly secrets`; DEP-023 keeps it out of `fly.toml`.
- **AUTH-015** — No email, no name, no role in the payload. The subject is a user id and nothing
  else, because JWT payloads are readable by anyone holding the token.
- **AUTH-016** — 24-hour expiry.

**AUTH-017.** Startup fails loudly if `JWT_SECRET` is missing or shorter than 32 characters. A
default secret in code is worse than no auth at all, because it looks like auth.

## 5. Cookie

**AUTH-018.**

```python
response.set_cookie(
    key="session",
    value=token,
    httponly=True,
    secure=True,          # False only when ENVIRONMENT == "development"
    samesite="lax",
    max_age=86400,
    path="/",
)
```

**AUTH-019.** `secure=True` in production is enforced by `force_https` in `fly.toml`
(`5-deployment.md` DEP-019, which also sets `ENVIRONMENT = "production"`).

**AUTH-020.** Logout clears the cookie. There is no server-side denylist, so a stolen token stays
valid until it expires. Stated in the README rather than glossed over.

## 6. Endpoints

### 6.1 `POST /api/auth/signup`

```json
{ "email": "test@example.com", "password": "...", "simulation_id": "uuid-or-null" }
```

**AUTH-021.**

1. Normalise the email to lowercase and strip whitespace.
2. If the email exists → 409 `EMAIL_ALREADY_REGISTERED`.
3. Hash the password, create the user.
4. If `simulation_id` is present, claim it (§7).
5. Issue the token, set the cookie.
6. Return the user and the claimed simulation id, if any.

**AUTH-022.** Uniqueness is enforced by a **unique index on `users.email`**, not only by the lookup in
step 2 — the rule stated generally in `1-code-quality.md` CQ-092 and given its table in CQ-085. The
lookup gives a clean error message; the constraint is what makes it correct. Two simultaneous signups
with the same address will both pass step 2, and the loser must be caught:

```python
try:
    user = await self._repository.create(email=email, password_hash=hashed)
except IntegrityError as exc:
    raise AuthError(code="EMAIL_ALREADY_REGISTERED") from exc
```

**AUTH-023.** Normalisation happens before both the lookup and the insert, so the index is doing the
work on the same value the check saw. → `0-business-logic.md` DOM-019, which already makes the email
unique and case-insensitive.

**AUTH-024.** Signing up logs the user in. Making someone log in immediately after registering is
friction with no security benefit.

### 6.2 `POST /api/auth/login`

```json
{ "email": "test@example.com", "password": "..." }
```

**AUTH-025.** Wrong email and wrong password both return 401 `INVALID_CREDENTIALS` with the same
message. Never "user not found".

**AUTH-026. Hash on every attempt, including when no user exists.** Otherwise the response time
reveals whether an email is registered:

```python
async def authenticate(self, email: str, password: str) -> User:
    """Verify credentials in constant-ish time."""
    user = await self._repository.get_by_email(email.strip().lower())
    hashed = user.password_hash if user else _DUMMY_HASH
    matched = verify_password(password, hashed)
    if user is None or not matched:
        raise AuthError(code="INVALID_CREDENTIALS")
    return user
```

**AUTH-027.** `_DUMMY_HASH` is a module-level argon2 hash of a throwaway string, computed once at
import.

### 6.3 `POST /api/auth/logout`

**AUTH-028.** Clears the cookie. Returns 204. Succeeds whether or not a valid session existed.

### 6.4 `GET /api/auth/me`

**AUTH-029.** Returns the current user, or 401. The frontend calls this on boot to decide whether it
is logged in, because it cannot read the httpOnly cookie itself.

## 7. Claiming a simulation

The one flow with a real design decision in it. It implements `0-business-logic.md` DOM-025 – DOM-027
and is the cross-domain edge declared as `2-architecture.md` ARC-017.

**AUTH-030.** A simulation is created anonymously. The frontend holds its id in memory and sends it
with the signup request. The backend attaches it:

```python
async def claim_for_user(self, simulation_id: UUID, user_id: UUID) -> Simulation | None:
    """Attach an anonymous simulation to a user.

    Only an unclaimed simulation can be attached. A simulation already owned by
    someone else is left untouched and None is returned; this is not an error,
    because a failed claim must never block registration.
    """
    simulation = await self._repository.get(simulation_id)
    if simulation is None or simulation.user_id is not None:
        return None
    return await self._repository.set_owner(simulation_id, user_id)
```

Three properties that matter:

- **AUTH-031. Claiming never fails the signup.** A missing or already-claimed simulation is ignored
  silently. Losing a free calculation must not cost a registration. → `4-ux.md` UX-028.
- **AUTH-032. An owned simulation is never reassigned.** The check is `user_id is None`, not
  "overwrite". → DOM-027.
- **AUTH-033. Known limitation, documented rather than over-engineered:** anyone who knows a
  simulation's UUID could claim it before its creator signs up. The ids are unguessable UUID4s and the
  payload is a calculation with no personal data, so the impact is nil. A real system would bind the
  simulation to a browser session on creation. Flagged as a next step.

## 8. Authorisation

**AUTH-034.** One rule, and it covers the whole application: **a user can only see their own data.**

```python
async def get_application(self, application_id: UUID, user_id: UUID) -> Application:
    """Fetch an application owned by this user."""
    application = await self._repository.get(application_id)
    if application is None or application.user_id != user_id:
        raise NotFoundError(code="APPLICATION_NOT_FOUND")
    return application
```

**AUTH-035. A resource owned by someone else returns 404, not 403.** A 403 confirms the resource
exists, which leaks information. The two cases are indistinguishable from the outside, by design.
→ `0-business-logic.md` ERR-005, which states the same rule for the domain.

**AUTH-036.** The ownership check lives in the service, not in the router. Per the controller rule
(`1-code-quality.md` CQ-017) the router has one line, so the check cannot live there. The `user_id`
arrives as a FastAPI dependency — `CQ-019` routes authorisation to a dependency by design:

```python
async def current_user(request: Request, service: AuthService = Depends(get_auth_service)) -> User:
    """Resolve the authenticated user from the session cookie."""
    token = request.cookies.get("session")
    if token is None:
        raise AuthError(code="NOT_AUTHENTICATED")
    return await service.user_from_token(token)
```

**AUTH-037.** `current_user` lives in `domains/auth/dependencies.py`, which is a **declared public
surface of the auth domain** alongside `service.py` — `2-architecture.md` ARC-042. It may read the
request and delegate to `auth.service`, and nothing else; it never touches a repository.

**AUTH-038.** Every protected route takes `user: User = Depends(current_user)` and passes `user.id`
into the service. There is no global auth middleware: explicit dependencies make it visible in each
signature which routes are protected.

**AUTH-039.** Public routes: `POST /api/simulations`, `GET /api/simulations/{id}`, signup, login,
**logout** (AUTH-028 makes it succeed with or without a session), `/health`, `/ready`, and the static
files. Everything else requires a session. The simulator is public
because DOM-008 makes a simulation anonymous by default and UX-009 opens it computed on first paint.

## 9. Rate limiting

**AUTH-040.** In-memory, per IP, on the two auth endpoints only: **10 attempts per 5 minutes**, then
429 `TOO_MANY_ATTEMPTS`. Implementation lives in `core/rate_limit.py`, which is generic and imports no
domain (ARC-012).

**AUTH-041.** A dictionary of IP to timestamps, swept on write. Roughly fifteen lines. It resets on
restart and it does not work across multiple machines, both of which are fine for one machine and
worth one line in the README.

**AUTH-042.** Not applied to the simulator: it is anonymous, cheap and the whole point is that people
use it freely. → UX-054.

## 10. Email enumeration

**AUTH-043.** Login does not leak which emails are registered. Signup necessarily does, because a
user has to be told their email is already taken.

This is the standard trade-off and the standard resolution: usability wins on signup, secrecy wins on
login. Worth being able to say, because it is a question that gets asked.

## 11. Frontend integration

- **AUTH-044** — **The token is never touched by JavaScript.** The cookie is httpOnly; there is no
  code path that reads it. Nothing goes into `localStorage`.
- **AUTH-045** — `withCredentials: true` on the HTTP client so the cookie travels.
- **AUTH-046** — Auth state comes from `GET /api/auth/me` on application boot, held in a signal.
- **AUTH-047** — An HTTP interceptor catches 401, clears local auth state and redirects to login. It
  does not retry. Lives in `core/auth.interceptor.ts` (`2-architecture.md` ARC-020).
- **AUTH-048** — A route guard protects the wizard and document routes, and preserves the intended
  URL so the user lands where they were going after logging in. Lives in `domains/auth/auth.guard.ts`.
- **AUTH-049** — The signup form sends the simulation id from the simulator, if one exists.
  → UX-027.

## 12. Definition of done

- **AUTH-050** — Passwords are argon2id hashed; no plaintext appears anywhere, including logs.
- **AUTH-051** — `users.email` carries a unique index, and a duplicate insert is caught and mapped to
  409.
- **AUTH-052** — The session cookie is httpOnly, `SameSite=Lax`, and secure in production.
- **AUTH-053** — Nothing auth-related is stored in `localStorage`.
- **AUTH-054** — Startup fails if `JWT_SECRET` is absent or too short.
- **AUTH-055** — Wrong email and wrong password are indistinguishable in both message and timing.
- **AUTH-056** — Another user's application returns 404, not 403.
- **AUTH-057** — Signing up with a simulation id lands on a prefilled application; signing up with a
  stale one still succeeds.
- **AUTH-058** — A redeploy does not log anyone out.

---

# Appendix A — Traceability

Source: `08-auth.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| AUTH-001 | JWT in an httpOnly cookie; the three options | Decisions | §1.1 |
| AUTH-002 | No refresh token; one 24-hour access token | Decisions | §1.2 |
| AUTH-003 | Refresh and a denylist are the first additions for production | Decisions | §1.2 |
| AUTH-004 | `SameSite=Lax` covers CSRF for a single origin | Decisions | §1.3 |
| AUTH-005 | A CSRF token would be ceremony here; say so | Decisions | §1.3 |
| AUTH-006 | `argon2-cffi` directly, argon2id | Decisions | §1.4 |
| AUTH-007 | Never sha256, md5 or plaintext | Decisions | §1.4 |
| AUTH-008 | Six things not built, with reasons | Not built | §2 |
| AUTH-009 | `hash_password` / `verify_password` | Password handling | §3 |
| AUTH-010 | Minimum 10 characters, no composition rules | Password handling | §3 |
| AUTH-011 | The plaintext password never leaves the hashing call | Password handling | §3 |
| AUTH-012 | The token payload | Token | §4 |
| AUTH-013 | `HS256`, secret from `JWT_SECRET` | Token | §4 |
| AUTH-014 | The secret is fixed in the environment | Token | §4 |
| AUTH-015 | No email, name or role in the payload | Token | §4 |
| AUTH-016 | 24-hour expiry | Token | §4 |
| AUTH-017 | Startup fails without a ≥32-character secret | Token | §4 |
| AUTH-018 | The `set_cookie` call | Cookie | §5 |
| AUTH-019 | `secure=True` in production, enforced by `force_https` | Cookie | §5 |
| AUTH-020 | Logout clears the cookie; no denylist | Cookie | §5 |
| AUTH-021 | The six-step signup flow | Endpoints | §6.1 |
| AUTH-022 | Uniqueness by index, `IntegrityError` caught | Endpoints | §6.1 |
| AUTH-023 | Normalisation before both lookup and insert | Endpoints | §6.1 |
| AUTH-024 | Signing up logs the user in | Endpoints | §6.1 |
| AUTH-025 | Wrong email and wrong password are the same 401 | Endpoints | §6.2 |
| AUTH-026 | Hash on every attempt, even with no user | Endpoints | §6.2 |
| AUTH-027 | `_DUMMY_HASH` computed once at import | Endpoints | §6.2 |
| AUTH-028 | Logout returns 204 either way | Endpoints | §6.3 |
| AUTH-029 | `GET /api/auth/me` for boot-time auth state | Endpoints | §6.4 |
| AUTH-030 | `claim_for_user` | Claiming a simulation | §7 |
| AUTH-031 | Claiming never fails the signup | Claiming a simulation | §7 |
| AUTH-032 | An owned simulation is never reassigned | Claiming a simulation | §7 |
| AUTH-033 | Known limitation: a known UUID can be claimed | Claiming a simulation | §7 |
| AUTH-034 | A user can only see their own data | Authorisation | §8 |
| AUTH-035 | Someone else's resource returns 404, not 403 | Authorisation | §8 |
| AUTH-036 | The ownership check lives in the service | Authorisation | §8 |
| AUTH-037 | `current_user` is a declared public surface of auth | added — resolves the ARC-011/012 conflict | §8 |
| AUTH-038 | Explicit dependencies, no global middleware | Authorisation | §8 |
| AUTH-039 | The public route list | Authorisation | §8 |
| AUTH-040 | 10 attempts per 5 minutes on the auth endpoints | Rate limiting | §9 |
| AUTH-041 | In-memory, resets on restart, single machine | Rate limiting | §9 |
| AUTH-042 | Not applied to the simulator | Rate limiting | §9 |
| AUTH-043 | Login hides enumeration, signup cannot | Email enumeration | §10 |
| AUTH-044 | The token is never touched by JavaScript | Frontend integration | §11 |
| AUTH-045 | `withCredentials: true` | Frontend integration | §11 |
| AUTH-046 | Auth state from `/me` on boot, in a signal | Frontend integration | §11 |
| AUTH-047 | A 401 interceptor that does not retry | Frontend integration | §11 |
| AUTH-048 | A route guard that preserves the intended URL | Frontend integration | §11 |
| AUTH-049 | The signup form sends the simulation id | Frontend integration | §11 |
| AUTH-050 | Done: argon2id, no plaintext anywhere | Definition of done | §12 |
| AUTH-051 | Done: unique index, duplicate mapped to 409 | Definition of done | §12 |
| AUTH-052 | Done: httpOnly, Lax, secure in production | Definition of done | §12 |
| AUTH-053 | Done: nothing auth-related in `localStorage` | Definition of done | §12 |
| AUTH-054 | Done: startup fails on a bad `JWT_SECRET` | Definition of done | §12 |
| AUTH-055 | Done: indistinguishable in message and timing | Definition of done | §12 |
| AUTH-056 | Done: another user's application returns 404 | Definition of done | §12 |
| AUTH-057 | Done: signup with a stale simulation id still succeeds | Definition of done | §12 |
| AUTH-058 | Done: a redeploy does not log anyone out | Definition of done | §12 |

# Appendix B — Error codes introduced here

All four are registered in the single registry, `1-code-quality.md` CQ-063. None existed before this
spec.

| Code | HTTP | Raised by |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | AUTH-025, AUTH-026 |
| `NOT_AUTHENTICATED` | 401 | AUTH-036 — no session cookie |
| `TOO_MANY_ATTEMPTS` | 429 | AUTH-040 |
| `APPLICATION_NOT_FOUND` | 404 | AUTH-034, AUTH-035 — also returned when the resource belongs to someone else |

`EMAIL_ALREADY_REGISTERED` already existed (CQ-063) and is mapped to 409 here for the first time.
