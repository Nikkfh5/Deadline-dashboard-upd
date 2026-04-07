"""
debug/monitor.py — Health and status monitor for Deadline Dashboard.

Usage:
  python debug/monitor.py --health        # check API + frontend
  python debug/monitor.py --full          # detailed system check
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import urllib.error

if sys.stdout.encoding and sys.stdout.encoding.lower().startswith("cp"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = "http://176.124.205.198:8001"
FRONTEND_URL = "http://176.124.205.198:3000"


def check_endpoint(url: str, timeout: int = 5) -> tuple[bool, int, str]:
    """Check if URL responds. Returns (ok, status_code, detail)."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.status, "OK"
    except urllib.error.HTTPError as e:
        return True, e.code, f"HTTP {e.code}"
    except Exception as e:
        return False, 0, str(e)


def health_check() -> bool:
    """Quick health check."""
    ok, status, detail = check_endpoint(f"{BASE_URL}/api/deadlines?token=probe")
    if ok:
        print(f"  API: UP (status={status})")
    else:
        print(f"  API: DOWN ({detail})")

    ok2, status2, detail2 = check_endpoint(FRONTEND_URL)
    if ok2:
        print(f"  Frontend: UP (status={status2})")
    else:
        print(f"  Frontend: DOWN ({detail2})")

    return ok and ok2


def full_check() -> None:
    """Detailed system check."""
    print("\n=== System Health ===\n")
    ok, status, detail = check_endpoint(f"{BASE_URL}/api/deadlines?token=probe")
    print(f"  Backend API:  {'UP' if ok else 'DOWN'} ({detail})")
    ok2, status2, detail2 = check_endpoint(FRONTEND_URL)
    print(f"  Frontend:     {'UP' if ok2 else 'DOWN'} ({detail2})")

    print("\n=== API Endpoints ===\n")
    for method, path in [
        ("GET", "/api/deadlines?token=probe"),
        ("GET", "/api/stats?token=probe"),
    ]:
        ok, status, detail = check_endpoint(f"{BASE_URL}{path}")
        print(f"  {method} {path}: {status} ({detail})")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Monitor for Deadline Dashboard")
    parser.add_argument("--health", action="store_true", help="Quick health check")
    parser.add_argument("--full", action="store_true", help="Detailed check")
    args = parser.parse_args()
    if args.full:
        full_check()
    else:
        health_check()


if __name__ == "__main__":
    main()
