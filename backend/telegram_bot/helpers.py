from datetime import datetime, timedelta


def format_time_left(due_utc: datetime) -> str:
    """Format time remaining until deadline as human-readable string."""
    now = datetime.utcnow()
    diff = due_utc - now

    if diff.total_seconds() <= 0:
        # Overdue
        diff = now - due_utc
        days = diff.days
        hours = diff.seconds // 3600
        if days > 0:
            return f"{days}д {hours}ч назад"
        elif hours > 0:
            minutes = (diff.seconds % 3600) // 60
            return f"{hours}ч {minutes}мин назад"
        else:
            minutes = diff.seconds // 60
            return f"{minutes}мин назад"

    days = diff.days
    hours = diff.seconds // 3600
    if days > 0:
        return f"{days}д {hours}ч"
    elif hours > 0:
        minutes = (diff.seconds % 3600) // 60
        return f"{hours}ч {minutes}мин"
    else:
        minutes = diff.seconds // 60
        return f"{minutes}мин"


def format_due_date_msk(due_utc: datetime) -> str:
    """Format UTC datetime as Moscow time string."""
    msk = due_utc + timedelta(hours=3)
    return msk.strftime("%d.%m.%Y %H:%M")


def format_due_short_msk(due_utc: datetime) -> str:
    """Format UTC datetime as short Moscow time (dd.mm HH:MM)."""
    msk = due_utc + timedelta(hours=3)
    return msk.strftime("%d.%m %H:%M")
