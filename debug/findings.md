# Findings

Auto-generated bug reports and observations.

---


### BUG-001 [MEDIUM] — 2026-04-07 10:59 UTC

[huge_name] POST deadline with 10000 char name: Accepted 10000 char name — no length limit

### BUG-002 [HIGH] [security] — 2026-04-07 11:00 UTC

[xss_name] POST deadline with XSS in name: XSS stored verbatim: `<img src=x onerror=alert(1)>`

Backend stores raw HTML in `name` and `task` fields without sanitization.
If frontend renders via innerHTML/dangerouslySetInnerHTML this is exploitable XSS.
NOTE: React's JSX escapes by default via `{}` interpolation, so this is only dangerous
if the frontend uses `dangerouslySetInnerHTML` anywhere for deadline fields.

### [OK] 2026-04-07 11:00 UTC — Auth

Token validation works correctly: empty token → 401, fake token → 401,
SQL-injection-like token → rejected. No data leakage.

### BUG-003 [MEDIUM] — 2026-04-07 11:07 UTC

[xss_name] POST deadline with XSS in name: XSS stored verbatim: <img src=x onerror=alert(1)>

### BUG-004 [MEDIUM] — 2026-04-07 11:08 UTC

[huge_name] POST deadline with 10000 char name: Accepted 10000 char name — no length limit
