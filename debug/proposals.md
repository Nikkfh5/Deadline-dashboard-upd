# Improvement Proposals

Suggestions for improvements.

---

### PROP-001 [MEDIUM] — 2026-04-07 11:01 UTC

**Add max_length validation to string fields**

Backend accepts arbitrary length strings for `name`, `task`, `details`.
Add `Field(max_length=500)` to DeadlineCreate/DeadlineUpdate Pydantic models.

Related: BUG-001

### PROP-002 [LOW] — 2026-04-07 11:01 UTC

**Consider HTML sanitization on backend**

XSS is stored verbatim (BUG-002). React escapes by default so it's low-risk,
but if any future rendering path uses innerHTML it becomes exploitable.
Minimal fix: strip HTML tags from `name` and `task` on input.

Related: BUG-002

