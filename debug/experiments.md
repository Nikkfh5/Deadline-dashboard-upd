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

**Notes:** channel_post_deadline failed via Bot API (403 — bot not admin). BUT the Telethon userbot post DID create a deadline (id=7e552054, name=QA, source=telegram) — pipeline confirmed working with >25s delay. The boss.py test needs to use SSH+Telethon instead of Bot API for posting.

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

---

## EXP-023 — 2026-04-07 11:50 UTC

**Strategy:** Playwright MCP E2E — remaining tests (complete, recurring repeat, planning, snapshots)

### EXP-023 Results — 2026-04-07 12:00 UTC

- **Passed:** 5/5
- **Failed:** 0/5

**Tests:**
- E2E-05 Complete: PASS (created "E2E Complete Test", clicked Done, card removed, completed_this_week 4→5)
- E2E-06 Recurring repeat: PASS (created recurring with past date, clicked Repeat, moved to Temporary with +7d date, waited 12s — did NOT revert)
- E2E-08 Planning auto: PASS (entered days_needed=3, calendar showed 3-day work period with red coloring)
- E2E-09 Planning manual: PASS (selected "стажка", clicked 2 calendar days, tooltip showed "2d manual" + overlap)
- E2E-10 Snapshot save/load: PASS (saved "E2E Snapshot Test", cleared manual plan, loaded snapshot — 2 manual days restored)
- Console: 0 errors, 2 warnings (non-critical)

**Notes:**
All 5 remaining E2E tests passed. Recurring repeat fix confirmed in real browser — date persisted through sync cycle. Planning mode (auto+manual) and snapshot save/load fully functional. Complete flow properly increments stats.

**Status:** DONE

---

## EXP-024 — 2026-04-07 12:00 UTC

**Strategy:** Full system coverage — bot commands via Telethon, wiki, reminders, data isolation

### EXP-024 Results — 2026-04-07 12:10 UTC

- **Passed:** 18/18
- **Failed:** 0/18

**Bot commands (via Telethon → @deadline_fcs_bot):**
- /start: PASS — /help: PASS — /my_deadlines: PASS — /dashboard: PASS
- /settings: PASS — /list_channels: PASS — /list_wikis: PASS
- /share: PASS (code 7FLAK7) — /join XXXXXX: PASS (rejected invalid)
- /snapshot: PASS — /add conversation: PASS (full flow)
- /add_wiki + /remove_wiki: PASS

**System verification:**
- Reminders: PASS (5 records in DB, scheduler active)
- Channel monitoring: PASS (18 parsed_posts, last 30min ago)
- Data isolation: PASS (6 users, 0 deadline overlap)
- Share codes: PASS

**Status:** DONE

---

## EXP-025 — 2026-09-13 — Bot recovery and full verification

User request: restore channel deadline import, then check all bot functions; do not stop after a restart.

- [x] Compare deployed code with GitHub: both a7a1e92.
- [x] Establish incident: userbot disconnected, repeated channel join failures; API health does not check userbot. Separate read-only Telegram connection confirms session remains authorized.
- [x] Baseline backend suite: 51 passed.
- [x] Restore channel monitoring and verify channel read -> parse -> save.
- [x] Verify configured LLM providers and failure handling.
- [x] Check bot commands, add/cancel flow, deadlines, completion/delete, settings, sources, sharing, snapshot and reminders.
- [x] Check API isolation/CRUD, dashboard rendering and frontend tests/build.
- [x] Record proven results, remaining failures and any required user action.

Use isolated test data for writes. Do not send messages to real users or post in coursework channels during tests.

Results:
- Production @deadline_fcs_bot: restored Telethon connection; all 26 active channel subscriptions joined, zero pending. Last stored parsed post before recovery was 2026-06-24; retained logs do not establish the original disconnect time/cause.
- Fixed recovery in the existing 5-minute channel job and health reporting for the userbot and polling bot. A separate real Telegram connection was disconnected deliberately and successfully restored through the job; production connections were not interrupted for this test.
- Fixed imported MSK dates being stored as UTC without conversion, and API timestamps missing UTC offsets. Real OMV channel post for 16 September 10:30 MSK now saves 07:30 UTC in isolated QA MongoDB and the browser shows Moscow time correctly.
- Fixed cross-user completion callbacks and synchronous /cancel callbacks in channel/wiki conversations. Regression tests failed before the fixes and passed after them.
- Backend: 62 passed using `.venv/Scripts/python.exe -m pytest -p no:pytest_ethereum backend/tests -q`. Local venv supplies Telethon 1.42.0 and Starlette 0.37.2; the shared Python installation had no Telethon and an incompatible Starlette 1.0.0.
- Isolated MongoDB integration: 37 passed; commands/settings/manual add/source sharing and removal/API CRUD and isolation/completion/reminder dedup/real-post analysis and save/cached history snapshot checked. Telegram output was mocked for isolated handler checks. QA databases were dropped and absence verified.
- Live Telegram: start/help/dashboard/deadlines/settings/source lists/add/cancel and source-conversation cancellation responded; a reminder was sent only to the automation account and its receipt verified. Natural-language date parsing returned the expected UTC value.
- Gemini and Haiku parsed a synthetic deadline successfully. Cerebras returned HTTP 402 (payment required); billing was not changed.
- Wiki auto-import is disabled by existing commit 014a553. Adding/removing wiki sources works, but no hourly wiki job is scheduled; this existing feature choice was preserved.
- Frontend: 6 tests passed and production build compiled. Current local frontend includes pre-existing uncommitted work; it was not deployed. Existing deployed UI checked with Playwright: create/persistence/MSK display/edit/mark/important/list/canvas/calendar/planning/complete+stats/recurring repeat/delete; mobile screenshot inspected. Completed browser scenarios had no console errors. Immediate reload during optimistic creation can briefly show both local and server cards; a fresh load has one database record.
- No bulk history replay or migration of historical user deadlines was performed. Actual historical posts were tested in isolated DB; receipt of a newly published coursework post remains a natural-traffic check.
