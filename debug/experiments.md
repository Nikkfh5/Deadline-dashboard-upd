# Experiments Log

Append-only log of QA experiments.

---


---

## EXP-001 — 2026-04-07 10:59 UTC

**Strategy:** auto

**Status:** IN PROGRESS


### EXP-001 Results — 2026-04-07 11:01 UTC

- **Passed:** 17/19
- **Failed:** 2/19
- **Bugs found:** BUG-001, BUG-002

**Notes:**
Full API surface test. Auth works correctly (no_token, bad_token, injection all rejected).
CRUD OK. Recurring deadlines repeat correctly via PUT. Validation works (days_needed=0/-5 rejected, garbage date rejected, missing fields rejected).
Two issues: XSS stored verbatim in name field (BUG-002), no string length limit (BUG-001).

**Status:** DONE

---

## EXP-002 — 2026-04-07 11:07 UTC

**Strategy:** auto

**Status:** IN PROGRESS


### EXP-002 Results — 2026-04-07 11:08 UTC

- **Passed:** 17/19
- **Failed:** 2/19

**Status:** DONE

---

## EXP-003 — 2026-04-07 11:09 UTC

**Strategy:** focus=security

**Status:** IN PROGRESS


### EXP-003 Results — 2026-04-07 11:10 UTC

- **Passed:** 3/3
- **Failed:** 0/3

**Notes:**
Re-test after deploying FIX-001/FIX-002. XSS sanitized (BUG-002 verified), 10000 char name rejected 422 (BUG-001 verified), injection token rejected. Both fixes confirmed.

**Status:** DONE

---

## EXP-004 — 2026-04-07 11:10 UTC

**Strategy:** focus=edge_cases

**Status:** IN PROGRESS


### EXP-004 Results — 2026-04-07 11:11 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-005 — 2026-04-07 11:11 UTC

**Strategy:** focus=validation

**Status:** IN PROGRESS


### EXP-005 Results — 2026-04-07 11:11 UTC

- **Passed:** 3/3
- **Failed:** 0/3

**Status:** DONE

---

## EXP-006 — 2026-04-07 11:11 UTC

**Strategy:** focus=recurring

**Status:** IN PROGRESS


### EXP-006 Results — 2026-04-07 11:11 UTC

- **Passed:** 2/2
- **Failed:** 0/2

**Status:** DONE

---

## EXP-007 — 2026-04-07 11:16 UTC

**Strategy:** focus=health_stats

**Status:** IN PROGRESS


### EXP-007 Results — 2026-04-07 11:16 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-008 — 2026-04-07 11:17 UTC

**Strategy:** focus=sources

**Status:** IN PROGRESS


### EXP-008 Results — 2026-04-07 11:17 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-009 — 2026-04-07 11:17 UTC

**Strategy:** focus=completion

**Status:** IN PROGRESS


### EXP-009 Results — 2026-04-07 11:17 UTC

- **Passed:** 2/2
- **Failed:** 0/2

**Status:** DONE

---

## EXP-010 — 2026-04-07 11:17 UTC

**Strategy:** focus=pagination

**Status:** IN PROGRESS


### EXP-010 Results — 2026-04-07 11:17 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-011 — 2026-04-07 11:17 UTC

**Strategy:** focus=days_needed

**Status:** IN PROGRESS


### EXP-011 Results — 2026-04-07 11:17 UTC

- **Passed:** 3/3
- **Failed:** 0/3

**Status:** DONE
