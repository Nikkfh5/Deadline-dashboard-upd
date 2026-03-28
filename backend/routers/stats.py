from fastapi import APIRouter, Query
from datetime import datetime, timedelta

from services.database import get_db
from services.auth import get_user_by_token

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("")
async def get_stats(token: str = Query(...)):
    user = await get_user_by_token(token)
    db = get_db()
    user_id = str(user["_id"])
    now = datetime.utcnow()

    # All deadlines for this user
    all_deadlines = await db.deadlines.find({"user_id": user_id}).to_list(5000)

    total = len(all_deadlines)
    upcoming = 0
    overdue = 0
    completed = 0  # past deadlines that aren't overdue markers
    by_source = {"manual": 0, "telegram": 0, "wiki": 0}
    rescheduled = 0

    # Next 7 days: count per day
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    days_map = {}
    for i in range(7):
        day = week_start + timedelta(days=i)
        days_map[day.strftime("%Y-%m-%d")] = 0

    busiest_day = None
    busiest_count = 0

    for d in all_deadlines:
        due = d.get("due_date")
        source_type = d.get("source", {}).get("type", "manual")
        by_source[source_type] = by_source.get(source_type, 0) + 1

        if d.get("is_postponed"):
            rescheduled += 1

        if due:
            if due > now:
                upcoming += 1
            else:
                overdue += 1

            # Week chart
            day_key = due.strftime("%Y-%m-%d")
            if day_key in days_map:
                days_map[day_key] += 1

    # Find busiest day overall
    day_counts = {}
    for d in all_deadlines:
        due = d.get("due_date")
        if due and due > now:
            dk = due.strftime("%A")  # day of week
            day_counts[dk] = day_counts.get(dk, 0) + 1

    if day_counts:
        busiest_day = max(day_counts, key=day_counts.get)
        busiest_count = day_counts[busiest_day]

    # Week data as list for frontend chart
    week_data = []
    day_names_ru = {
        "Monday": "Пн", "Tuesday": "Вт", "Wednesday": "Ср",
        "Thursday": "Чт", "Friday": "Пт", "Saturday": "Сб", "Sunday": "Вс",
    }
    for date_str, count in days_map.items():
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        day_name = day_names_ru.get(dt.strftime("%A"), dt.strftime("%a"))
        week_data.append({
            "day": f"{day_name} {dt.strftime('%d.%m')}",
            "count": count,
        })

    return {
        "total": total,
        "upcoming": upcoming,
        "overdue": overdue,
        "rescheduled": rescheduled,
        "by_source": by_source,
        "week": week_data,
        "busiest_day": busiest_day,
        "busiest_count": busiest_count,
    }
