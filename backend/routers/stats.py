from fastapi import APIRouter, Query
from datetime import datetime, timedelta

from services.database import get_db
from services.auth import get_user_by_token

router = APIRouter(prefix="/api/stats", tags=["stats"])

DAY_NAMES_RU = {
    1: "Пн", 2: "Вт", 3: "Ср",
    4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс",
}


@router.get("")
async def get_stats(token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])
    now = datetime.utcnow()

    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    # Single aggregation pipeline using $facet
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$facet": {
            # Counts
            "counts": [
                {"$group": {
                    "_id": None,
                    "total": {"$sum": 1},
                    "upcoming": {"$sum": {"$cond": [{"$gt": ["$due_date", now]}, 1, 0]}},
                    "overdue": {"$sum": {"$cond": [
                        {"$and": [
                            {"$ne": ["$due_date", None]},
                            {"$lte": ["$due_date", now]},
                        ]}, 1, 0,
                    ]}},
                    "rescheduled": {"$sum": {"$cond": [{"$eq": ["$is_postponed", True]}, 1, 0]}},
                }},
            ],
            # Source breakdown
            "by_source": [
                {"$group": {
                    "_id": {"$ifNull": ["$source.type", "manual"]},
                    "count": {"$sum": 1},
                }},
            ],
            # Weekly breakdown (next 7 days)
            "week": [
                {"$match": {
                    "due_date": {"$gte": week_start, "$lt": week_end},
                }},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$due_date"}},
                    "count": {"$sum": 1},
                }},
            ],
            # Busiest day of week (next 7 days only)
            "busiest": [
                {"$match": {"due_date": {"$gte": week_start, "$lt": week_end}}},
                {"$group": {
                    "_id": {"$dayOfWeek": "$due_date"},  # 1=Sun..7=Sat
                    "count": {"$sum": 1},
                }},
                {"$sort": {"count": -1}},
                {"$limit": 1},
            ],
        }},
    ]

    result = await db.deadlines.aggregate(pipeline).to_list(1)
    facets = result[0] if result else {}

    # Extract counts
    counts_doc = (facets.get("counts") or [{}])[0] if facets.get("counts") else {}
    total = counts_doc.get("total", 0)
    upcoming = counts_doc.get("upcoming", 0)
    overdue = counts_doc.get("overdue", 0)
    rescheduled = counts_doc.get("rescheduled", 0)

    # Extract source breakdown
    by_source = {"manual": 0, "telegram": 0, "wiki": 0}
    for doc in facets.get("by_source", []):
        src = doc["_id"]
        by_source[src] = by_source.get(src, 0) + doc["count"]

    # Build week data
    week_counts = {doc["_id"]: doc["count"] for doc in facets.get("week", [])}
    week_data = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_key = day.strftime("%Y-%m-%d")
        # Monday=0..Sunday=6 via isoweekday (1..7)
        day_name = DAY_NAMES_RU.get(day.isoweekday(), day.strftime("%a"))
        week_data.append({
            "day": f"{day_name} {day.strftime('%d.%m')}",
            "count": week_counts.get(day_key, 0),
        })

    # Busiest day
    # MongoDB $dayOfWeek: 1=Sun, 2=Mon, ..., 7=Sat
    mongo_dow_to_name = {1: "Вс", 2: "Пн", 3: "Вт", 4: "Ср", 5: "Чт", 6: "Пт", 7: "Сб"}
    busiest_day = None
    busiest_count = 0
    busiest_docs = facets.get("busiest", [])
    if busiest_docs:
        busiest_day = mongo_dow_to_name.get(busiest_docs[0]["_id"], "?")
        busiest_count = busiest_docs[0]["count"]

    # Completed this week
    week_ago = now - timedelta(days=7)
    completed_this_week = await db.completions.count_documents({
        "user_id": user_id,
        "completed_at": {"$gte": week_ago},
    })

    return {
        "total": total,
        "upcoming": upcoming,
        "overdue": overdue,
        "rescheduled": rescheduled,
        "completed_this_week": completed_this_week,
        "by_source": by_source,
        "week": week_data,
        "busiest_day": busiest_day,
        "busiest_count": busiest_count,
    }
