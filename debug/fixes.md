# Fix Reports

Documentation of bug fixes with re-test procedures.

---

### FIX-001 — BUG-001 [MEDIUM] — 2026-04-07

**No string length limit on name/task fields**

Fixed by adding `Field(max_length=500)` to `name` and `task` in both `DeadlineCreate` and `DeadlineUpdate` Pydantic models. Also added `[:500]` truncation in `deadline_extractor.py` and `add_deadline.py` which insert directly into DB bypassing Pydantic.

**Files changed:**
- `backend/models/deadline.py` — added `max_length=500` to name/task Fields
- `backend/services/deadline_extractor.py` — added `[:500]` truncation
- `backend/telegram_bot/handlers/add_deadline.py` — added `[:500]` truncation

**Re-test:** POST a deadline with 10000 char name → should get 422 validation error.

**Verified:** YES (EXP-003 — returned 422 for 10000 char name)

### FIX-002 — BUG-002 [HIGH] [security] — 2026-04-07

**XSS stored verbatim in name/task fields**

Fixed by adding `strip_html_tags()` function that removes all HTML tags via regex. Applied as `field_validator` on `DeadlineCreate` and `DeadlineUpdate` Pydantic models. Also applied in `deadline_extractor.py` and `add_deadline.py` which bypass Pydantic.

**Files changed:**
- `backend/models/deadline.py` — added `strip_html_tags()` + `field_validator` on name/task
- `backend/services/deadline_extractor.py` — imported and applied `strip_html_tags()`
- `backend/telegram_bot/handlers/add_deadline.py` — imported and applied `strip_html_tags()`

**Re-test:** POST deadline with `<img src=x onerror=alert(1)>` in name → should store without HTML tags.

**Verified:** YES (EXP-003 — XSS sanitized, stored clean)

