"""Read published Manytask groups through a user's own Manytask session."""
import json
import asyncio
import logging
import os
import re
from weakref import WeakValueDictionary
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlsplit
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup
from cryptography.fernet import Fernet, InvalidToken
from bson import ObjectId
from pymongo import ReturnDocument

from services.database import get_db

BASE_URL = "https://app.manytask.org"
ALLOWED_HOSTS = {"app.manytask.org", "gitlab.manytask.org"}
MSK = ZoneInfo("Europe/Moscow")
_account_locks = WeakValueDictionary()


def account_lock(user_id):
    key = str(user_id)
    lock = _account_locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _account_locks[key] = lock
    return lock


class ManytaskError(Exception):
    def __init__(self, message, *, auth_required=False):
        super().__init__(message)
        self.auth_required = auth_required


class _HideAuthRequests(logging.Filter):
    def filter(self, record):
        # httpx INFO logs include OAuth codes and state in request URLs.
        return not any(host in record.getMessage() for host in ALLOWED_HOSTS)


logging.getLogger("httpx").addFilter(_HideAuthRequests())


def session_cipher():
    try:
        return Fernet(os.environ["MANYTASK_SESSION_KEY"].encode())
    except (KeyError, ValueError):
        raise ManytaskError("Администратор ещё не настроил подключение Manytask.") from None


def encrypt_session(user_id, cookie):
    return session_cipher().encrypt(json.dumps([str(user_id), cookie]).encode()).decode()


def decrypt_session(user_id, encrypted):
    try:
        owner, cookie = json.loads(session_cipher().decrypt(encrypted.encode()))
        if owner != str(user_id) or not isinstance(cookie, str):
            raise ValueError
        return cookie
    except (InvalidToken, ValueError, TypeError):
        raise ManytaskError("Подключите аккаунт Manytask заново.", auth_required=True) from None


def canonical_course_url(value):
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        raise ManytaskError("Некорректная ссылка курса Manytask.") from None
    slug = parts.path.strip("/")
    if (parts.scheme != "https" or parts.netloc != "app.manytask.org"
            or parts.query or parts.fragment or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}", slug)
            or parts.path not in {f"/{slug}", f"/{slug}/"}
            or slug in {"login", "logout", "signup", "login_finish", "signup_finish", "api", "instance_admin"}):
        raise ManytaskError("Укажите ссылку курса: https://app.manytask.org/название-курса/")
    return f"{BASE_URL}/{slug}/"


async def _request(client, method, url, *, stop_on_login=False, **kwargs):
    for _ in range(10):
        parts = urlsplit(str(url))
        if stop_on_login and (parts.netloc == "gitlab.manytask.org" or parts.path in {"/signup", "/login"}):
            raise ManytaskError("Сессия Manytask истекла. Подключите аккаунт заново.", auth_required=True)
        if parts.scheme != "https" or parts.netloc not in ALLOWED_HOSTS:
            raise ManytaskError("Manytask перенаправил запрос на неподдерживаемый адрес.")
        try:
            response = await client.request(method, url, follow_redirects=False, **kwargs)
        except httpx.HTTPError:
            raise ManytaskError("Manytask временно недоступен. Повторите позже.") from None
        if response.status_code == 429:
            raise ManytaskError("Manytask ограничил частоту запросов. Повторите через 15 минут.")
        if response.status_code >= 500:
            raise ManytaskError("Manytask временно недоступен. Повторите позже.")
        if response.status_code not in {301, 302, 303, 307, 308}:
            return response
        # Never forward credentials to a redirect destination, including 307/308.
        url = urljoin(str(response.url), response.headers.get("location", ""))
        method, kwargs = "GET", {}
    raise ManytaskError("Не удалось завершить перенаправления Manytask.")


async def login_manytask(client, username, password):
    response = await _request(client, "GET", f"{BASE_URL}/login")
    soup = BeautifulSoup(response.text, "html.parser")
    form = soup.find("form", action="/users/sign_in")
    if form is None or response.url.host != "gitlab.manytask.org":
        raise ManytaskError("Не удалось открыть форму входа GitLab Manytask.")
    data = {item["name"]: item.get("value", "") for item in form.select('input[name][type="hidden"]')}
    data.update({"user[login]": username, "user[password]": password})
    response = await _request(client, "POST", "https://gitlab.manytask.org/users/sign_in", data=data)
    # GitLab uses an HTML/JS redirect for the OAuth callback, not always HTTP 302.
    soup = BeautifulSoup(response.text, "html.parser")
    for link in soup.select("a[href]"):
        target = urlsplit(urljoin(str(response.url), link["href"]))
        if target.scheme == "https" and target.netloc == "app.manytask.org" and target.path == "/login_finish":
            response = await _request(client, "GET", target.geturl())
            break
    if response.url.host != "app.manytask.org" or response.url.path in {"/signup", "/signup_finish"}:
        raise ManytaskError("Вход не завершён. Проверьте логин и пароль. Если требуется 2FA или подтверждение, вход через эту форму пока не поддерживается.")
    cookie = client.cookies.get("session", domain="app.manytask.org", path="/")
    if not cookie:
        raise ManytaskError("Manytask не выдал сессию. Завершите регистрацию на сайте курса.")
    return cookie


async def read_course(client, url):
    response = await _request(client, "GET", url, stop_on_login=True)
    if response.url.host != "app.manytask.org" or response.url.path in {"/signup", "/login", "/login_finish"}:
        raise ManytaskError("Сессия Manytask истекла. Подключите аккаунт заново.", auth_required=True)
    if response.status_code == 403:
        raise ManytaskError("У этого аккаунта нет доступа к курсу Manytask.")
    if response.status_code != 200 or response.url.path != urlsplit(url).path:
        raise ManytaskError("Курс недоступен. Сначала завершите подключение курса на сайте Manytask.")
    return response.text


def _deadline_time(element):
    zone = element.get("data-tippy-content", "")
    if zone in {"MSK", "Europe/Moscow"}:
        tz = MSK
    elif zone in {"UTC", "GMT"}:
        tz = timezone.utc
    else:
        match = re.fullmatch(r"UTC([+-])(\d{2}):(\d{2})", zone)
        if not match:
            raise ValueError("Unknown timezone")
        offset = timedelta(hours=int(match[2]), minutes=int(match[3]))
        tz = timezone(offset if match[1] == "+" else -offset)
    text = element.get_text(" ", strip=True)
    match = re.search(r"(\d{2}\.\d{2}\.\d{4})\s+(\d{2}:\d{2})", text)
    if not match:
        raise ValueError("Missing deadline")
    return datetime.strptime(" ".join(match.groups()), "%d.%m.%Y %H:%M").replace(tzinfo=tz).astimezone(timezone.utc)


def parse_course(html, url, now=None):
    soup = BeautifulSoup(html, "html.parser")
    if not soup.select_one("#toggleDeadlinesBtn"):
        raise ManytaskError("Не распознана страница заданий Manytask. Импорт не выполнен.")
    now = now or datetime.now(timezone.utc)
    deadlines = []
    seen = set()
    for group in soup.select(".mt-lecture"):
        try:
            name = group.select_one("span.fs-2").get_text(" ", strip=True)
            if not name or name in seen or len(name) > 250:
                raise ValueError("Invalid group")
            seen.add(name)
            stages = []
            for item in group.select(".task-deadline"):
                date = item.select_one(".task-deadline__deadline-time")
                percent = item.select_one(".deadline-percent")
                if date is not None and percent is not None:
                    stages.append((float(percent.get_text(strip=True).removesuffix("%")), _deadline_time(date)))
            if not stages:
                raise ValueError("Missing stages")
            if max(date for _, date in stages) <= now:
                continue
            full = [date for percent, date in stages if percent == 100]
            if len(full) != 1:
                raise ValueError("No full-score deadline")
            late = [f"{percent:g}% — {date.astimezone(MSK):%d.%m.%Y %H:%M} МСК"
                    for percent, date in stages if date > full[0]]
            deadlines.append({
                "external_id": name,
                "task_name": name,
                "subject": f"Manytask · {urlsplit(url).path.strip('/')}",
                "due_date": full[0].isoformat(),
                "details": ("Поздняя сдача: " + "; ".join(late)) if late else "",
                "confidence": 1.0,
            })
        except (ValueError, AttributeError, OverflowError):
            raise ManytaskError("Не удалось однозначно определить срок на полный балл. Формат этого курса пока не поддерживается.") from None
    return deadlines


async def invalidate_session(user_id):
    db = get_db()
    await db.users.update_one({"_id": user_id}, {"$unset": {"manytask_session": ""}})
    await db.sources.update_many(
        {"user_id": str(user_id), "type": "manytask_course", "is_active": True},
        {"$set": {"last_error": "Сессия Manytask истекла. Подключите аккаунт заново."}},
    )


async def _read_and_store_session(client, user_id, url):
    # Manytask may rotate its cookie while refreshing OAuth tokens, even when a
    # particular course is inaccessible. Persist it before parsing the page.
    try:
        return await read_course(client, url)
    finally:
        cookie = client.cookies.get("session", domain="app.manytask.org", path="/")
        if cookie:
            await get_db().users.update_one(
                {"_id": user_id}, {"$set": {"manytask_session": encrypt_session(user_id, cookie)}})


async def save_course(source, extracted):
    from services.deadline_extractor import content_hash, save_extracted_deadlines
    snapshot_hash = content_hash(json.dumps(extracted, sort_keys=True, ensure_ascii=False))
    if snapshot_hash != source.get("last_content_hash"):
        await save_extracted_deadlines(
            user_ids=[source["user_id"]], extracted=extracted, source_id=str(source["_id"]),
            source_type="manytask", raw_text=source["identifier"],
            source_name=source["display_name"], source_url=source["identifier"],
        )
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    changes = {"last_content_hash": snapshot_hash, "last_checked_at": now, "last_error": None, "updated_at": now}
    await get_db().sources.update_one(
        {"_id": source["_id"], "user_id": source["user_id"], "is_active": True}, {"$set": changes})
    source.update(changes)


async def connect_course(user_id, url, username="", password=""):
    session_cipher()  # Fail before accepting a password if encryption is unconfigured.
    url = canonical_course_url(url)
    db = get_db()
    async with account_lock(user_id):
        user = await db.users.find_one({"_id": user_id})
        async with httpx.AsyncClient(timeout=15) as client:
            if username and password:
                await login_manytask(client, username, password)
            else:
                encrypted = user.get("manytask_session")
                if not encrypted:
                    raise ManytaskError("Введите логин и пароль аккаунта GitLab Manytask.")
                client.cookies.set("session", decrypt_session(user_id, encrypted), domain="app.manytask.org", path="/")
            try:
                html = await _read_and_store_session(client, user_id, url)
            except ManytaskError as error:
                if error.auth_required:
                    await invalidate_session(user_id)
                raise
            extracted = parse_course(html, url)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        source = await db.sources.find_one_and_update(
            {"user_id": str(user_id), "type": "manytask_course", "identifier": url},
            {"$set": {"is_active": True, "joined": True, "display_name": f"Manytask · {urlsplit(url).path.strip('/')}",
                      "updated_at": now},
             "$setOnInsert": {"created_at": now, "last_checked_at": None}},
            upsert=True, return_document=ReturnDocument.AFTER,
        )
        await save_course(source, extracted)
        return source


async def check_manytask_sources():
    db = get_db()
    sources = await db.sources.find({"type": "manytask_course", "is_active": True}).to_list(None)
    for owner in dict.fromkeys(s["user_id"] for s in sources):
        async with account_lock(owner):
            user_id = ObjectId(owner)
            user = await db.users.find_one({"_id": user_id})
            if not user or not user.get("manytask_session"):
                continue
            try:
                cookie = decrypt_session(owner, user["manytask_session"])
            except ManytaskError as error:
                if error.auth_required:
                    await invalidate_session(user_id)
                continue
            async with httpx.AsyncClient(timeout=15) as client:
                client.cookies.set("session", cookie, domain="app.manytask.org", path="/")
                active = await db.sources.find({"user_id": owner, "type": "manytask_course", "is_active": True}).to_list(None)
                for source in active:
                    try:
                        url = canonical_course_url(source["identifier"])
                        html = await _read_and_store_session(client, user_id, url)
                        await save_course(source, parse_course(html, url))
                    except ManytaskError as error:
                        if error.auth_required:
                            await invalidate_session(user_id)
                            break
                        await db.sources.update_one({"_id": source["_id"], "user_id": owner},
                                                    {"$set": {"last_error": str(error)}})
                    except Exception:
                        # Neither upstream HTML nor cookies belong in logs/API errors.
                        logging.getLogger(__name__).error("Manytask sync failed for source %s", source["_id"])
                        await db.sources.update_one({"_id": source["_id"], "user_id": owner},
                                                    {"$set": {"last_error": "Ошибка синхронизации. Проверка повторится через 3 часа."}})
