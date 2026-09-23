"""Manytask contracts: full-score deadlines, isolated sessions and bounded login."""
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from bson import ObjectId
from datetime import datetime, timezone

import httpx
import pytest
from cryptography.fernet import Fernet

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

URL = "https://app.manytask.org/python-2026-fall/"
NOW = datetime(2026, 9, 23, tzinfo=timezone.utc)


def course_html(group="01.2.BasicTypes_hard", first="01.10.2026", zone="UTC+03:00"):
    # Same structure as Manytask 26.0.5; no student scores or account data.
    return f'''<button id="toggleDeadlinesBtn">Show past deadlines</button>
    <div class="mt-lecture"><span class="fs-2">{group}</span>
      <div class="task-deadlines">
        <div class="task-deadline passed-deadline" style="display:none">
          <span class="deadline-percent">100%</span>
          <div class="task-deadline__deadline-time" data-tippy-content="{zone}">
            <span>{first}</span><span>23:59</span></div></div>
        <div class="task-deadline"><span class="deadline-percent">50%</span>
          <div class="task-deadline__deadline-time" data-tippy-content="{zone}">
            <span>30.01.2027</span><span>23:59</span></div></div>
      </div></div>'''


def test_one_group_uses_full_score_time_and_includes_late_deadline():
    from services.manytask import parse_course
    result = parse_course(course_html(), URL, NOW)
    assert len(result) == 1
    assert result[0]["task_name"] == "01.2.BasicTypes_hard"
    assert result[0]["due_date"] == "2026-10-01T20:59:00+00:00"
    assert "50%" in result[0]["details"] and "30.01.2027 23:59 МСК" in result[0]["details"]
    moved = parse_course(course_html(first="02.10.2026"), URL, NOW)
    assert result[0]["external_id"] == moved[0]["external_id"]
    other = parse_course(course_html(group="01.2.BasicTypes"), URL, NOW)
    assert result[0]["external_id"] != other[0]["external_id"]


def test_passed_full_score_is_kept_while_late_submission_is_open():
    from services.manytask import parse_course
    assert len(parse_course(course_html(first="01.09.2026"), URL, NOW)) == 1
    assert parse_course(course_html(), URL, datetime(2027, 2, 1, tzinfo=timezone.utc)) == []


@pytest.mark.parametrize("html", ["<form>Sign in</form>", course_html(zone="unknown"),
                                  course_html().replace("100%", "75%")])
def test_unrecognized_page_or_full_score_is_not_an_empty_success(html):
    from services.manytask import ManytaskError, parse_course
    with pytest.raises(ManytaskError):
        parse_course(html, URL, NOW)


@pytest.mark.parametrize("url", ["https://[invalid", "http://app.manytask.org/course", "https://evil.test/course",
    "https://app.manytask.org:444/course", "https://user@app.manytask.org/course",
    "https://app.manytask.org/course?token=secret", "https://app.manytask.org/course/../login",
    "https://app.manytask.org/api/course", "https://app.manytask.org/login"])
def test_course_urls_are_restricted(url):
    from services.manytask import ManytaskError, canonical_course_url
    with pytest.raises(ManytaskError):
        canonical_course_url(url)


def test_session_encryption_is_bound_to_the_dashboard_user(monkeypatch):
    from services.manytask import encrypt_session, decrypt_session, ManytaskError
    monkeypatch.setenv("MANYTASK_SESSION_KEY", Fernet.generate_key().decode())
    encrypted = encrypt_session("alice", "sensitive-cookie")
    assert "sensitive-cookie" not in encrypted
    assert decrypt_session("alice", encrypted) == "sensitive-cookie"
    with pytest.raises(ManytaskError):
        decrypt_session("bob", encrypted)


@pytest.mark.asyncio
async def test_login_follows_gitlab_html_callback_and_keeps_only_manytask_cookie():
    from services.manytask import login_manytask
    seen = []
    def handle(request):
        seen.append(request)
        path = request.url.path
        if path == "/login":
            return httpx.Response(302, headers={"location": "https://gitlab.manytask.org/users/sign_in"})
        if path == "/users/sign_in" and request.method == "GET":
            return httpx.Response(200, text='<form action="/users/sign_in"><input name="authenticity_token" type="hidden" value="csrf"></form>')
        if path == "/users/sign_in":
            assert b"user%5Bpassword%5D=secret" in request.content
            return httpx.Response(200, headers={"set-cookie": "_gitlab_session=do-not-store; Path=/"},
                text='<a href="https://app.manytask.org/login_finish?code=code&amp;state=state">Redirect</a>')
        if path == "/login_finish":
            return httpx.Response(302, headers={"location": "/", "set-cookie": "session=only-this; Path=/"})
        return httpx.Response(200, text="Courses")
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        assert await login_manytask(client, "alice", "secret") == "only-this"
    assert len([r for r in seen if r.method == "POST"]) == 1


@pytest.mark.asyncio
async def test_redirect_cannot_send_request_to_other_hosts():
    from services.manytask import login_manytask, ManytaskError
    seen = []
    def handle(request):
        seen.append(request)
        return httpx.Response(302, headers={"location": "https://evil.test/steal"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(ManytaskError):
            await login_manytask(client, "alice", "secret")
    assert len(seen) == 1


@pytest.mark.asyncio
async def test_expired_session_is_detected_and_rotated_cookie_is_retained():
    from services.manytask import read_course, ManytaskError
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(
            302, headers={"location": "/signup"}))) as client:
        with pytest.raises(ManytaskError) as error:
            await read_course(client, URL)
        assert error.value.auth_required
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: httpx.Response(
            200, text=course_html(), headers={"set-cookie": "session=rotated; Path=/"}))) as client:
        await read_course(client, URL)
        assert client.cookies.get("session") == "rotated"


@pytest.mark.asyncio
async def test_sync_uses_user_source_and_skips_unchanged_snapshot(monkeypatch):
    from services import manytask
    from services import deadline_extractor
    source = {"_id": ObjectId(), "user_id": "alice", "identifier": URL,
              "display_name": "Python", "is_active": True}
    extracted = [{"external_id": "hw", "due_date": "2026-10-01T00:00:00Z"}]
    updates = AsyncMock()
    monkeypatch.setattr(manytask, "get_db", lambda: SimpleNamespace(sources=SimpleNamespace(update_one=updates)))
    save = AsyncMock(return_value=(1, []))
    monkeypatch.setattr(deadline_extractor, "save_extracted_deadlines", save)
    await manytask.save_course(source, extracted)
    assert save.call_args.kwargs["user_ids"] == ["alice"]
    assert save.call_args.kwargs["source_id"] == str(source["_id"])
    assert save.call_args.kwargs["source_type"] == "manytask"
    source.update(updates.call_args.args[1]["$set"])
    save.reset_mock()
    await manytask.save_course(source, extracted)
    save.assert_not_awaited()


@pytest.mark.asyncio
async def test_auth_failure_invalidates_only_its_owners_connection(monkeypatch):
    from services import manytask
    user = {"_id": ObjectId()}
    db = SimpleNamespace(users=SimpleNamespace(update_one=AsyncMock()),
                         sources=SimpleNamespace(update_many=AsyncMock()))
    monkeypatch.setattr(manytask, "get_db", lambda: db)
    await manytask.invalidate_session(user["_id"])
    assert db.users.update_one.call_args.args[0] == {"_id": user["_id"]}
    assert db.sources.update_many.call_args.args[0] == {
        "user_id": str(user["_id"]), "type": "manytask_course", "is_active": True}


@pytest.mark.asyncio
async def test_credentials_body_errors_do_not_echo_password(monkeypatch):
    from fastapi import FastAPI
    from routers import sources
    app = FastAPI()
    app.include_router(sources.router)
    monkeypatch.setattr(sources, "get_user_by_token", AsyncMock(return_value={"_id": ObjectId()}))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        for payload in [{"identifier": 5, "password": "do-not-echo"}, ["do-not-echo"],
                        {"identifier": URL, "username": "alice", "password": ["do-not-echo"]}]:
            response = await client.post("/api/sources/manytask?token=test", json=payload)
            assert response.status_code == 400
            assert "do-not-echo" not in response.text
