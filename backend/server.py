from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import json
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List
import uuid
from datetime import datetime


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')


# Structured JSON logging
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log = {
            "ts": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0]:
            log["exception"] = self.formatException(record.exc_info)
        ctx = getattr(record, "ctx", None)
        if ctx:
            log["ctx"] = ctx
        return json.dumps(log, ensure_ascii=False)


handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from services.database import init_db, close_db
    await init_db()
    logger.info("Database initialized")

    # Start Telegram bot
    try:
        from telegram_bot.bot import start_bot
        await start_bot()
    except Exception as e:
        logger.error(f"Failed to start Telegram bot: {e}")

    # Start Telethon userbot
    try:
        from telegram_userbot.client import start_userbot
        await start_userbot()
    except Exception as e:
        logger.error(f"Failed to start Telethon userbot: {e}")

    # Start scheduler
    try:
        from scheduler.scheduler import setup_scheduler
        setup_scheduler()
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

    yield

    # Shutdown
    try:
        from scheduler.scheduler import shutdown_scheduler
        shutdown_scheduler()
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {e}")

    try:
        from telegram_bot.bot import stop_bot
        await stop_bot()
    except Exception as e:
        logger.error(f"Bot shutdown error: {e}")

    try:
        from telegram_userbot.client import stop_userbot
        await stop_userbot()
    except Exception as e:
        logger.error(f"Userbot shutdown error: {e}")

    await close_db()
    logger.info("Shutdown complete")


app = FastAPI(lifespan=lifespan)

# Legacy router for backward compatibility
api_router = APIRouter(prefix="/api")


class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str


@api_router.get("/")
async def root():
    return {"message": "Hello World"}

@api_router.get("/health")
async def health_check():
    from services.database import get_db
    from telegram_bot.bot import get_bot_app
    health = {"status": "ok", "timestamp": datetime.utcnow().isoformat(), "services": {}}

    try:
        db = get_db()
        await db.command("ping")
        health["services"]["mongodb"] = "ok"
    except Exception:
        health["services"]["mongodb"] = "error"
        health["status"] = "degraded"

    health["services"]["telegram_bot"] = "running" if get_bot_app() else "stopped"

    return health

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    from services.database import get_db
    db = get_db()
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    from services.database import get_db
    db = get_db()
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**sc) for sc in status_checks]


# Include routers
app.include_router(api_router)

from routers.deadlines import router as deadlines_router
from routers.users import router as users_router
from routers.sources import router as sources_router
app.include_router(deadlines_router)
app.include_router(users_router)
app.include_router(sources_router)

cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
