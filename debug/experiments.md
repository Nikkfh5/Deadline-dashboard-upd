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

---

## EXP-012 — 2026-04-07 11:22 UTC

**Strategy:** focus=frontend

**Status:** IN PROGRESS


### EXP-012 Results — 2026-04-07 11:22 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-013 — 2026-04-07 11:22 UTC

**Strategy:** focus=bot

**Status:** IN PROGRESS


### EXP-013 Results — 2026-04-07 11:22 UTC

- **Passed:** 1/3
- **Failed:** 2/3

**Status:** DONE

---

## EXP-014 — 2026-04-07 11:22 UTC

**Strategy:** focus=bot

**Status:** IN PROGRESS


### EXP-014 Results — 2026-04-07 11:23 UTC

- **Passed:** 3/3
- **Failed:** 0/3

**Status:** DONE

---

## EXP-015 — 2026-04-07 11:23 UTC

**Strategy:** focus=sync_race

**Status:** IN PROGRESS


### EXP-015 Results — 2026-04-07 11:23 UTC

- **Passed:** 3/3
- **Failed:** 0/3

**Status:** DONE

---

## EXP-016 — 2026-04-07 11:23 UTC

**Strategy:** focus=snapshot_api

**Status:** IN PROGRESS


### EXP-016 Results — 2026-04-07 11:23 UTC

- **Passed:** 2/2
- **Failed:** 0/2

**Status:** DONE

---

## EXP-017 — 2026-04-07 11:35 UTC

**Strategy:** focus=deadline_fields

**Status:** IN PROGRESS


### EXP-017 Results — 2026-04-07 11:36 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-018 — 2026-04-07 11:36 UTC

**Strategy:** focus=stats_deep

**Status:** IN PROGRESS


### EXP-018 Results — 2026-04-07 11:36 UTC

- **Passed:** 4/4
- **Failed:** 0/4

**Status:** DONE

---

## EXP-019 — 2026-04-07 11:36 UTC

**Strategy:** focus=bot_commands_deep

**Status:** IN PROGRESS


### EXP-019 Results — 2026-04-07 11:36 UTC

- **Passed:** 3/3
- **Failed:** 0/3

**Status:** DONE

---

## EXP-020 — 2026-04-07 11:36 UTC

**Strategy:** focus=notifications

**Status:** IN PROGRESS


### EXP-020 Results — 2026-04-07 11:36 UTC

- **Passed:** 2/2
- **Failed:** 0/2

**Status:** DONE

---

## EXP-021 — 2026-04-07 11:36 UTC

**Strategy:** focus=channel_monitoring

**Status:** IN PROGRESS


### EXP-021 Results — 2026-04-07 11:37 UTC

- **Passed:** 2/3
- **Failed:** 1/3

**Notes:** channel_post_deadline failed — bot is not admin in @midvor (403 Forbidden). Telethon userbot post worked but outgoing messages are ignored by the monitor (expected behavior). channel_source_exists and channel_dedup PASS.

**Status:** DONE

---

## EXP-022 — 2026-04-07 11:40 UTC

**Strategy:** Playwright MCP E2E frontend tests

### EXP-022 Results — 2026-04-07 11:45 UTC

- **Passed:** 8/8
- **Failed:** 0/8

**Tests:**
- E2E-01 Page load: PASS (title OK, 0 console errors)
- E2E-02 Add deadline: PASS (created "E2E Test", verified on server)
- E2E-03 Edit deadline: PASS (task updated, verified on server)
- E2E-04 Delete + race fix: PASS (deleted, waited 12s, did NOT reappear)
- E2E-07 Dark mode: PASS (toggle + persistence through reload)
- E2E-11 Stats panel: PASS (15 total, 4 completed, week chart rendered)
- E2E-13 Calendar: PASS (expanded, "April 2026" grid visible)
- E2E-14 Responsive: PASS (375px=1col, 1920px=grid)
- E2E-12 Console errors: PASS (0 errors after all interactions)

**Notes:**
Channel monitoring pipeline confirmed working — QA deadline posted via Telethon appeared on desktop screenshot with delay >25s (caught by 10s polling). Delete race condition fix verified in real browser — 12 second wait, no reappearance.

**Status:** DONE
