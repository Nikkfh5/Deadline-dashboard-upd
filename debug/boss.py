"""
debug/boss.py — QA boss for Deadline Dashboard.

Tests the API on VPS via HTTP requests.
All tests are synchronous (request → response → verdict).

Usage:
  python debug/boss.py run                   # full cycle
  python debug/boss.py run --batch 5         # run 5 tasks
  python debug/boss.py run --focus security  # focus on specific area
  python debug/boss.py analyze               # analyze without injection
  python debug/boss.py coverage              # feature coverage report
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEBUG_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DEBUG_DIR))

from qa_core import QALoop

qa = QALoop(DEBUG_DIR)

BASE_URL = "http://176.124.205.198:8001"

# ── Helpers ──────────────────────────────────────────────────────────

def api(method: str, path: str, token: str = "", body: dict | None = None,
        timeout: int = 15) -> dict:
    """Make an API request. Returns {"status": int, "body": ..., "error": str}."""
    url = f"{BASE_URL}{path}"
    if token:
        sep = "&" if "?" in url else "?"
        url += f"{sep}token={token}"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = raw
            return {"status": resp.status, "body": parsed, "error": ""}
    except urllib.error.HTTPError as e:
        raw = ""
        try:
            raw = e.read().decode("utf-8")
        except Exception:
            pass
        return {"status": e.code, "body": raw, "error": str(e)}
    except Exception as e:
        return {"status": 0, "body": "", "error": str(e)}


def get_test_token() -> str:
    """Get a valid test user token by reading from DB via API or env."""
    # Try to fetch any user's token — we use the first user found
    # Since we can't query the DB directly, we'll create a known test token
    # by using the /api/deadlines endpoint to probe
    import os
    token = os.environ.get("QA_TEST_TOKEN", "")
    if token:
        return token

    # Fallback: read from config file
    token_file = DEBUG_DIR / ".test_token"
    if token_file.exists():
        return token_file.read_text().strip()

    print("  WARNING: No test token configured!")
    print("  Set QA_TEST_TOKEN env var or create debug/.test_token file")
    print("  Get token from MongoDB: db.users.findOne().dashboard_token")
    return ""


# ── Task Palettes ────────────────────────────────────────────────────

def _future_date(days: int = 7) -> str:
    return (datetime.utcnow() + timedelta(days=days)).isoformat()

def _past_date(days: int = 3) -> str:
    return (datetime.utcnow() - timedelta(days=days)).isoformat()


PALETTES = {
    "deadlines_crud": {
        "description": "CRUD operations on deadlines",
        "tasks": [
            ("create_basic", "POST deadline with valid data"),
            ("list_deadlines", "GET all deadlines"),
            ("update_deadline", "PUT deadline with new data"),
            ("delete_deadline", "DELETE deadline"),
        ],
    },
    "auth": {
        "description": "Authentication and authorization",
        "tasks": [
            ("no_token", "GET /api/deadlines without token"),
            ("bad_token", "GET /api/deadlines with invalid token"),
            ("valid_token", "GET /api/deadlines with valid token"),
        ],
    },
    "recurring": {
        "description": "Recurring deadline features",
        "tasks": [
            ("create_recurring", "Create recurring deadline"),
            ("repeat_recurring", "Simulate repeat by updating due_date"),
        ],
    },
    "edge_cases": {
        "description": "Edge cases and error handling",
        "tasks": [
            ("empty_name", "POST deadline with empty name"),
            ("missing_fields", "POST deadline with missing required fields"),
            ("update_nonexistent", "PUT nonexistent deadline"),
            ("delete_nonexistent", "DELETE nonexistent deadline"),
        ],
    },
    "validation": {
        "description": "Input validation",
        "tasks": [
            ("days_needed_zero", "POST with days_needed=0"),
            ("days_needed_negative", "POST with days_needed=-5"),
            ("garbage_date", "PUT with garbage due_date string"),
        ],
    },
    "security": {
        "description": "Security tests",
        "tasks": [
            ("xss_name", "POST deadline with XSS in name"),
            ("huge_name", "POST deadline with 10000 char name"),
            ("injection_token", "GET with SQL-injection-like token"),
        ],
    },
    "health_stats": {
        "description": "Health check and stats endpoints",
        "tasks": [
            ("health_endpoint", "GET /api/health"),
            ("stats_valid", "GET /api/stats with valid token"),
            ("stats_no_token", "GET /api/stats without token"),
            ("root_endpoint", "GET /api/"),
        ],
    },
    "sources": {
        "description": "Sources CRUD (channels/wikis)",
        "tasks": [
            ("list_sources", "GET /api/sources"),
            ("create_source", "POST /api/sources — create test source"),
            ("delete_source", "DELETE /api/sources/{id} — full lifecycle"),
            ("sources_no_token", "GET /api/sources without token"),
        ],
    },
    "completion": {
        "description": "Deadline completion flow",
        "tasks": [
            ("complete_deadline", "DELETE with complete=true — completion tracking"),
            ("complete_nonexistent", "DELETE nonexistent with complete=true"),
        ],
    },
    "pagination": {
        "description": "Pagination and limits",
        "tasks": [
            ("list_skip", "GET deadlines with skip=999"),
            ("list_limit_1", "GET deadlines with limit=1"),
            ("list_limit_huge", "GET deadlines with limit=9999"),
            ("list_limit_negative", "GET deadlines with limit=-1"),
        ],
    },
    "days_needed": {
        "description": "Days needed feature",
        "tasks": [
            ("create_with_days", "POST deadline with days_needed=5"),
            ("update_days_needed", "PUT deadline days_needed=3"),
            ("days_needed_large", "POST with days_needed=999"),
        ],
    },
}


# ── Test Implementations ─────────────────────────────────────────────

def run_test(test_id: str, token: str) -> dict:
    """Run a specific test. Returns {"pass": bool, "detail": str}."""

    # === CRUD ===
    if test_id == "create_basic":
        r = api("POST", "/api/deadlines", token, {
            "name": "QA Test Subject",
            "task": f"QA test task {uuid.uuid4().hex[:8]}",
            "due_date": _future_date(7),
        })
        if r["status"] == 200:
            return {"pass": True, "detail": f"Created: id={r['body'].get('id', '?')}", "cleanup_id": r["body"].get("id")}
        return {"pass": False, "detail": f"Expected 200, got {r['status']}: {r['error']}"}

    if test_id == "list_deadlines":
        r = api("GET", "/api/deadlines", token)
        if r["status"] == 200 and isinstance(r["body"], list):
            return {"pass": True, "detail": f"Got {len(r['body'])} deadlines"}
        return {"pass": False, "detail": f"Expected 200+list, got {r['status']}: {r['body']}"}

    if test_id == "update_deadline":
        # Create, then update
        cr = api("POST", "/api/deadlines", token, {
            "name": "QA Update Test", "task": "Before update", "due_date": _future_date(5),
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup failed: create returned {cr['status']}"}
        did = cr["body"]["id"]
        r = api("PUT", f"/api/deadlines/{did}", token, {"task": "After update"})
        # Cleanup
        api("DELETE", f"/api/deadlines/{did}?complete=false", token)
        if r["status"] == 200 and r["body"].get("task") == "After update":
            return {"pass": True, "detail": "Updated successfully"}
        return {"pass": False, "detail": f"Expected updated task, got {r['status']}: {r['body']}"}

    if test_id == "delete_deadline":
        cr = api("POST", "/api/deadlines", token, {
            "name": "QA Delete Test", "task": "To be deleted", "due_date": _future_date(3),
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup failed: {cr['status']}"}
        did = cr["body"]["id"]
        r = api("DELETE", f"/api/deadlines/{did}?complete=false", token)
        if r["status"] == 200:
            return {"pass": True, "detail": "Deleted successfully"}
        return {"pass": False, "detail": f"Expected 200, got {r['status']}"}

    # === AUTH ===
    if test_id == "no_token":
        r = api("GET", "/api/deadlines?token=")
        # Should fail — 422 (missing) or 401/403
        if r["status"] in (401, 403, 422):
            return {"pass": True, "detail": f"Correctly rejected with {r['status']}"}
        if r["status"] == 200:
            return {"pass": False, "detail": "SECURITY: returned 200 without token!"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "bad_token":
        r = api("GET", "/api/deadlines", token="fake-token-that-doesnt-exist")
        if r["status"] in (401, 403, 404):
            return {"pass": True, "detail": f"Correctly rejected with {r['status']}"}
        if r["status"] == 200:
            return {"pass": False, "detail": "SECURITY: accepted fake token!"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "valid_token":
        r = api("GET", "/api/deadlines", token)
        if r["status"] == 200:
            return {"pass": True, "detail": "Authenticated OK"}
        return {"pass": False, "detail": f"Valid token rejected: {r['status']}"}

    # === RECURRING ===
    if test_id == "create_recurring":
        r = api("POST", "/api/deadlines", token, {
            "name": "QA Recurring", "task": "Recurring task",
            "due_date": _future_date(3), "is_recurring": True, "interval_days": 7,
        })
        cleanup_id = r["body"].get("id") if r["status"] == 200 else None
        if r["status"] == 200 and r["body"].get("is_recurring") is True:
            if cleanup_id:
                api("DELETE", f"/api/deadlines/{cleanup_id}?complete=false", token)
            return {"pass": True, "detail": "Recurring deadline created"}
        return {"pass": False, "detail": f"Got {r['status']}: {r['body']}"}

    if test_id == "repeat_recurring":
        # Create recurring, then simulate repeat via PUT
        cr = api("POST", "/api/deadlines", token, {
            "name": "QA Repeat", "task": "Repeat test",
            "due_date": _past_date(1), "is_recurring": True, "interval_days": 7,
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup failed: {cr['status']}"}
        did = cr["body"]["id"]
        new_due = _future_date(7)
        r = api("PUT", f"/api/deadlines/{did}", token, {
            "due_date": new_due, "last_started_at": datetime.utcnow().isoformat(),
        })
        api("DELETE", f"/api/deadlines/{did}?complete=false", token)
        if r["status"] == 200:
            returned_due = r["body"].get("due_date", "")
            if new_due[:10] in returned_due:
                return {"pass": True, "detail": "Repeat updated due_date correctly"}
            return {"pass": False, "detail": f"due_date mismatch: sent {new_due[:10]}, got {returned_due}"}
        return {"pass": False, "detail": f"PUT returned {r['status']}: {r['error']}"}

    # === EDGE CASES ===
    if test_id == "empty_name":
        r = api("POST", "/api/deadlines", token, {
            "name": "", "task": "test", "due_date": _future_date(3),
        })
        # Empty name might be accepted or rejected — document behavior
        return {"pass": True, "detail": f"Status {r['status']} for empty name (behavior documented)"}

    if test_id == "missing_fields":
        r = api("POST", "/api/deadlines", token, {"name": "only name"})
        if r["status"] == 422:
            return {"pass": True, "detail": "Correctly rejected missing fields"}
        if r["status"] == 200:
            # Cleanup
            did = r["body"].get("id")
            if did:
                api("DELETE", f"/api/deadlines/{did}?complete=false", token)
            return {"pass": False, "detail": "Accepted deadline with missing task+due_date!"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "update_nonexistent":
        r = api("PUT", f"/api/deadlines/{uuid.uuid4()}", token, {"task": "ghost"})
        if r["status"] == 404:
            return {"pass": True, "detail": "Correctly 404"}
        return {"pass": False, "detail": f"Expected 404, got {r['status']}"}

    if test_id == "delete_nonexistent":
        r = api("DELETE", f"/api/deadlines/{uuid.uuid4()}?complete=false", token)
        if r["status"] == 404:
            return {"pass": True, "detail": "Correctly 404"}
        return {"pass": False, "detail": f"Expected 404, got {r['status']}"}

    # === VALIDATION ===
    if test_id == "days_needed_zero":
        r = api("POST", "/api/deadlines", token, {
            "name": "QA Val", "task": "val test", "due_date": _future_date(3), "days_needed": 0,
        })
        if r["status"] == 422:
            return {"pass": True, "detail": "Correctly rejected days_needed=0"}
        if r["status"] == 200:
            api("DELETE", f"/api/deadlines/{r['body'].get('id')}?complete=false", token)
            return {"pass": False, "detail": "Accepted days_needed=0, should reject (ge=1)"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "days_needed_negative":
        r = api("POST", "/api/deadlines", token, {
            "name": "QA Val", "task": "val test", "due_date": _future_date(3), "days_needed": -5,
        })
        if r["status"] == 422:
            return {"pass": True, "detail": "Correctly rejected negative days_needed"}
        if r["status"] == 200:
            api("DELETE", f"/api/deadlines/{r['body'].get('id')}?complete=false", token)
            return {"pass": False, "detail": "Accepted days_needed=-5!"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "garbage_date":
        cr = api("POST", "/api/deadlines", token, {
            "name": "QA Date", "task": "date test", "due_date": _future_date(3),
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup failed: {cr['status']}"}
        did = cr["body"]["id"]
        r = api("PUT", f"/api/deadlines/{did}", token, {"due_date": "not-a-date-lol"})
        api("DELETE", f"/api/deadlines/{did}?complete=false", token)
        if r["status"] == 422:
            return {"pass": True, "detail": "Correctly rejected garbage date"}
        return {"pass": False, "detail": f"Expected 422, got {r['status']}: {r['body']}"}

    # === SECURITY ===
    if test_id == "xss_name":
        xss = '<img src=x onerror=alert(1)>'
        r = api("POST", "/api/deadlines", token, {
            "name": xss, "task": "xss test", "due_date": _future_date(3),
        })
        if r["status"] == 200:
            did = r["body"].get("id")
            stored_name = r["body"].get("name", "")
            api("DELETE", f"/api/deadlines/{did}?complete=false", token)
            if "<img" in stored_name or "onerror" in stored_name:
                return {"pass": False, "detail": f"XSS stored verbatim: {stored_name}"}
            return {"pass": True, "detail": "XSS sanitized or escaped"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "huge_name":
        r = api("POST", "/api/deadlines", token, {
            "name": "A" * 10000, "task": "size test", "due_date": _future_date(3),
        })
        if r["status"] == 200:
            did = r["body"].get("id")
            api("DELETE", f"/api/deadlines/{did}?complete=false", token)
            return {"pass": False, "detail": "Accepted 10000 char name — no length limit"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "injection_token":
        r = api("GET", "/api/deadlines", token="' OR '1'='1")
        if r["status"] == 200 and isinstance(r["body"], list) and len(r["body"]) > 0:
            return {"pass": False, "detail": "CRITICAL: injection token returned data!"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    # === HEALTH & STATS ===
    if test_id == "health_endpoint":
        r = api("GET", "/api/health")
        if r["status"] == 200:
            return {"pass": True, "detail": f"Health OK: {r['body']}"}
        return {"pass": False, "detail": f"Health returned {r['status']}: {r['error']}"}

    if test_id == "root_endpoint":
        r = api("GET", "/api/")
        if r["status"] == 200:
            return {"pass": True, "detail": f"Root OK"}
        return {"pass": False, "detail": f"Root returned {r['status']}"}

    if test_id == "stats_valid":
        r = api("GET", "/api/stats", token)
        if r["status"] == 200 and isinstance(r["body"], dict):
            keys = set(r["body"].keys())
            expected = {"total", "upcoming", "overdue"}
            if expected.issubset(keys):
                return {"pass": True, "detail": f"Stats OK: {r['body'].get('total')} total, {r['body'].get('overdue')} overdue"}
            return {"pass": False, "detail": f"Missing keys: {expected - keys}"}
        return {"pass": False, "detail": f"Expected 200+dict, got {r['status']}"}

    if test_id == "stats_no_token":
        r = api("GET", "/api/stats?token=")
        if r["status"] in (401, 403, 422):
            return {"pass": True, "detail": f"Correctly rejected with {r['status']}"}
        return {"pass": False, "detail": f"Expected auth error, got {r['status']}"}

    # === SOURCES ===
    if test_id == "list_sources":
        r = api("GET", "/api/sources", token)
        if r["status"] == 200 and isinstance(r["body"], list):
            return {"pass": True, "detail": f"Got {len(r['body'])} sources"}
        return {"pass": False, "detail": f"Expected 200+list, got {r['status']}"}

    if test_id == "create_source":
        r = api("POST", "/api/sources", token, {
            "type": "telegram_channel", "identifier": "@qa_test_channel_fake",
            "display_name": "QA Test Channel",
        })
        if r["status"] == 200:
            sid = r["body"].get("id", r["body"].get("_id", ""))
            # Cleanup
            if sid:
                api("DELETE", f"/api/sources/{sid}", token)
            return {"pass": True, "detail": f"Source created: {sid}"}
        return {"pass": False, "detail": f"Expected 200, got {r['status']}: {r['body']}"}

    if test_id == "delete_source":
        # Create then delete
        cr = api("POST", "/api/sources", token, {
            "type": "telegram_channel", "identifier": "@qa_delete_test",
            "display_name": "QA Delete Test",
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup create failed: {cr['status']}"}
        sid = cr["body"].get("id", cr["body"].get("_id", ""))
        r = api("DELETE", f"/api/sources/{sid}", token)
        if r["status"] == 200:
            return {"pass": True, "detail": "Source deleted OK"}
        return {"pass": False, "detail": f"Delete returned {r['status']}: {r['body']}"}

    if test_id == "sources_no_token":
        r = api("GET", "/api/sources?token=")
        if r["status"] in (401, 403, 422):
            return {"pass": True, "detail": f"Correctly rejected with {r['status']}"}
        return {"pass": False, "detail": f"Expected auth error, got {r['status']}"}

    # === COMPLETION ===
    if test_id == "complete_deadline":
        cr = api("POST", "/api/deadlines", token, {
            "name": "QA Complete", "task": "To be completed", "due_date": _future_date(1),
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup failed: {cr['status']}"}
        did = cr["body"]["id"]
        r = api("DELETE", f"/api/deadlines/{did}?complete=true", token)
        if r["status"] == 200:
            body = r["body"] if isinstance(r["body"], dict) else {}
            if body.get("completed") is True:
                return {"pass": True, "detail": "Completed + deleted + tracked"}
            return {"pass": True, "detail": f"Deleted with complete=true, response: {body}"}
        return {"pass": False, "detail": f"Expected 200, got {r['status']}"}

    if test_id == "complete_nonexistent":
        r = api("DELETE", f"/api/deadlines/{uuid.uuid4()}?complete=true", token)
        if r["status"] == 404:
            return {"pass": True, "detail": "Correctly 404"}
        return {"pass": False, "detail": f"Expected 404, got {r['status']}"}

    # === PAGINATION ===
    if test_id == "list_skip":
        r = api("GET", f"/api/deadlines?skip=999", token)
        if r["status"] == 200 and isinstance(r["body"], list) and len(r["body"]) == 0:
            return {"pass": True, "detail": "Empty list for skip=999"}
        return {"pass": False, "detail": f"Got {r['status']}: {r['body']}"}

    if test_id == "list_limit_1":
        r = api("GET", f"/api/deadlines?limit=1", token)
        if r["status"] == 200 and isinstance(r["body"], list) and len(r["body"]) <= 1:
            return {"pass": True, "detail": f"Got {len(r['body'])} deadline(s) with limit=1"}
        return {"pass": False, "detail": f"Expected <=1 results, got {r['status']}: {len(r['body']) if isinstance(r['body'], list) else r['body']}"}

    if test_id == "list_limit_huge":
        r = api("GET", f"/api/deadlines?limit=9999", token)
        # Should either cap at 500 (validation) or return 422
        if r["status"] == 422:
            return {"pass": True, "detail": "Correctly rejected limit > 500"}
        if r["status"] == 200:
            return {"pass": False, "detail": f"Accepted limit=9999 — returned {len(r['body'])} items, no server-side cap"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    if test_id == "list_limit_negative":
        r = api("GET", f"/api/deadlines?limit=-1", token)
        if r["status"] == 422:
            return {"pass": True, "detail": "Correctly rejected negative limit"}
        if r["status"] == 200:
            return {"pass": False, "detail": "Accepted limit=-1!"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    # === DAYS NEEDED ===
    if test_id == "create_with_days":
        r = api("POST", "/api/deadlines", token, {
            "name": "QA Days", "task": "days test", "due_date": _future_date(10), "days_needed": 5,
        })
        if r["status"] == 200:
            dn = r["body"].get("days_needed")
            did = r["body"]["id"]
            api("DELETE", f"/api/deadlines/{did}?complete=false", token)
            if dn == 5:
                return {"pass": True, "detail": "days_needed=5 stored correctly"}
            return {"pass": False, "detail": f"days_needed={dn}, expected 5"}
        return {"pass": False, "detail": f"Expected 200, got {r['status']}"}

    if test_id == "update_days_needed":
        cr = api("POST", "/api/deadlines", token, {
            "name": "QA Days Upd", "task": "upd test", "due_date": _future_date(10),
        })
        if cr["status"] != 200:
            return {"pass": False, "detail": f"Setup failed: {cr['status']}"}
        did = cr["body"]["id"]
        r = api("PUT", f"/api/deadlines/{did}", token, {"days_needed": 3})
        api("DELETE", f"/api/deadlines/{did}?complete=false", token)
        if r["status"] == 200 and r["body"].get("days_needed") == 3:
            return {"pass": True, "detail": "days_needed updated to 3"}
        return {"pass": False, "detail": f"Got {r['status']}: days_needed={r['body'].get('days_needed') if r['status']==200 else r['body']}"}

    if test_id == "days_needed_large":
        r = api("POST", "/api/deadlines", token, {
            "name": "QA Large Days", "task": "large test", "due_date": _future_date(10), "days_needed": 999,
        })
        if r["status"] == 200:
            did = r["body"]["id"]
            api("DELETE", f"/api/deadlines/{did}?complete=false", token)
            return {"pass": True, "detail": f"days_needed=999 accepted (no upper limit)"}
        return {"pass": True, "detail": f"Rejected with {r['status']}"}

    return {"pass": False, "detail": f"Unknown test: {test_id}"}


# ── Core Boss Logic ──────────────────────────────────────────────────

def health_check() -> bool:
    r = api("GET", "/api/deadlines?token=health-check-probe")
    # Any HTTP response means server is up
    return r["status"] > 0


def run_cycle(batch: int = 5, focus: str = "", timeout: int = 300) -> None:
    """Full QA cycle: run tests, analyze, report."""

    print("\n=== Phase 1: PREPARATION ===")
    features = {name: [t[1] for t in info.get("tasks", [])] for name, info in PALETTES.items()}
    print(f"  Focus: {qa.suggest_focus(features)}")
    print(f"  Stats: {qa.stats()}")

    if not health_check():
        print("\n  FATAL: API not responding!")
        qa.log_finding("CRITICAL", "API health check failed — server unreachable",
                       details=f"Base URL: {BASE_URL}")
        return

    print("  Health: OK")

    token = get_test_token()
    if not token:
        print("\n  FATAL: No test token. Cannot proceed.")
        return

    # Verify token
    r = api("GET", "/api/deadlines", token)
    if r["status"] != 200:
        print(f"\n  FATAL: Test token invalid (status={r['status']})")
        return
    print(f"  Token: valid ({len(r['body'])} existing deadlines)")

    strategy = f"focus={focus}" if focus else "auto"
    exp_id = qa.start_experiment(strategy)
    print(f"\n=== {exp_id}: Testing ===")

    # Select tests
    if focus and focus in PALETTES:
        tests = PALETTES[focus]["tasks"][:batch]
    else:
        all_tests = []
        for p in PALETTES.values():
            all_tests.extend(p["tasks"])
        tests = random.sample(all_tests, min(batch, len(all_tests)))

    results = []
    for test_id, desc in tests:
        print(f"\n  [{test_id}] {desc}")
        try:
            result = run_test(test_id, token)
            status = "PASS" if result["pass"] else "FAIL"
            print(f"    {status}: {result['detail']}")
            results.append({"test_id": test_id, "desc": desc, **result})

            if not result["pass"]:
                qa.log_finding(
                    "HIGH" if "SECURITY" in result["detail"] or "CRITICAL" in result["detail"] else "MEDIUM",
                    f"[{test_id}] {desc}: {result['detail']}",
                )
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({"test_id": test_id, "desc": desc, "pass": False, "detail": str(e)})
            qa.log_finding("HIGH", f"[{test_id}] Exception: {e}")

    passed = sum(1 for r in results if r["pass"])
    failed = sum(1 for r in results if not r["pass"])
    qa.finish_experiment(exp_id, {"passed": passed, "failed": failed, "total": len(results)})
    print(f"\n=== {exp_id}: Done ({passed}/{len(results)} passed) ===")


def show_coverage() -> None:
    features = {name: [t[1] for t in info.get("tasks", [])] for name, info in PALETTES.items()}
    coverage = qa.get_coverage(features)
    print("\n=== Feature Coverage ===")
    for feature, info in coverage.items():
        icon = "v" if info["tested"] else " "
        print(f"  [{icon}] {feature}: {info['count']} hits")
    print(f"\n{qa.suggest_focus(features)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="QA Boss for Deadline Dashboard")
    sub = parser.add_subparsers(dest="command")
    run_p = sub.add_parser("run", help="Full QA cycle")
    run_p.add_argument("--batch", type=int, default=5)
    run_p.add_argument("--focus", type=str, default="")
    run_p.add_argument("--timeout", type=int, default=300)
    sub.add_parser("analyze", help="Analyze without injection")
    sub.add_parser("coverage", help="Feature coverage report")
    sub.add_parser("stats", help="QA loop statistics")
    sub.add_parser("actionable", help="Items for main project")

    args = parser.parse_args()
    if args.command == "run":
        run_cycle(batch=args.batch, focus=args.focus, timeout=args.timeout)
    elif args.command == "analyze":
        for k, v in qa.stats().items():
            print(f"  {k}: {v}")
        print()
        print(qa.get_actionable_for_main_project())
    elif args.command == "coverage":
        show_coverage()
    elif args.command == "stats":
        for k, v in qa.stats().items():
            print(f"  {k}: {v}")
    elif args.command == "actionable":
        print(qa.get_actionable_for_main_project())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
