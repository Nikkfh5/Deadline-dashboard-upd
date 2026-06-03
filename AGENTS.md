# Deadline Dashboard Agent Notes

## Scope

This is a deadline dashboard for HSE coursework deadlines.

- Backend: FastAPI, Motor/MongoDB, Pydantic v2.
- Frontend: React CRA via CRACO, Tailwind, shadcn/Radix, lucide-react.
- Main frontend flow is `frontend/src/components/DeadlineTracker.jsx`.
- Deadline card UI is `frontend/src/components/DeadlineCard.jsx`.
- Deadline API/model files are `backend/routers/deadlines.py` and `backend/models/deadline.py`.

Keep `CLAUDE.md` as legacy context. Use this file as the Codex entrypoint.

## Commands

Run backend tests from repo root:

```powershell
python -m pytest -p no:pytest_ethereum backend\tests -q
```

The `-p no:pytest_ethereum` flag avoids an unrelated globally installed `web3` pytest plugin that can break collection. Do not use `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` for the full suite because it also disables `pytest-asyncio`.

Run frontend tests from `frontend/`:

```powershell
$env:CI='true'; npm test -- src/lib/deadline-normalization.test.js
```

Build frontend from `frontend/`:

```powershell
npm run build
```

Local dev:

```powershell
cd backend; python -m uvicorn server:app --host 0.0.0.0 --port 8001
cd frontend; npm start
```

## Deadline Data Contract

Deadline timestamps are stored in UTC. The UI displays and edits them as Europe/Moscow.

Core deadline fields use snake_case on the backend and camelCase on the frontend:

- `due_date` <-> `dueDate`
- `is_recurring` <-> `isRecurring`
- `days_needed` <-> `daysNeeded`
- `is_marked` <-> `isMarked`

`is_marked` means "work appears done, but the deadline must remain visible because submission/upload details or external info are still pending." It must not call the delete endpoint and must not insert a completion record.

`Done` still means delete the deadline with `complete=true` and record completion. `Delete` means delete without completion.

## Frontend Notes

- Keep deadline normalization in `frontend/src/lib/deadline-normalization.js`.
- Old localStorage deadlines must migrate with safe defaults; missing `isMarked` is false.
- List and canvas views should both preserve key deadline actions.
- Operational UI should stay dense and scannable. Avoid decorative redesigns unless explicitly requested.
- After meaningful frontend or UI changes, verify rendered behavior with the
  Browser plugin or Playwright when feasible: open the local app, inspect the
  visible state, check console errors, and capture screenshots for layout-sensitive
  changes.

## Backend Notes

- New deadline fields should be represented in `DeadlineCreate`, `DeadlineUpdate`, `Deadline`, and `_deadline_from_doc`.
- Auto-import and Telegram bot code may insert raw Mongo documents; backend response mapping must default missing optional fields safely.
- `days_needed` must stay `ge=1` when present.

## Debug Protocol

`debug/CLAUDE.md` is a QA-boss protocol. Use it only when the user asks for autonomous debug/testing/verification. Normal feature work should not modify debug logs unless a bug/fix workflow explicitly needs it.
