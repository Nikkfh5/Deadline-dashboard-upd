import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from services.database import get_db
from telegram_bot.utils import get_current_user

logger = logging.getLogger(__name__)

SETTINGS_CB = "settings:"

REMINDER_OPTIONS = [
    (0, "Выключены"),
    (10, "10 мин"),
    (30, "30 мин"),
    (60, "1 час"),
    (180, "3 часа"),
    (720, "12 часов"),
    (1440, "24 часа"),
    (2880, "2 дня"),
]


def _format_reminder_list(minutes_list: list) -> str:
    if not minutes_list or minutes_list == [0] or minutes_list == 0:
        return "выключены"
    labels = []
    for m in sorted(minutes_list):
        if m <= 0:
            continue
        if m >= 1440:
            labels.append(f"{m // 1440}д")
        elif m >= 60:
            labels.append(f"{m // 60}ч")
        else:
            labels.append(f"{m}мин")
    return ", ".join(labels) if labels else "выключены"


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show settings menu."""
    user = await get_current_user(update)
    if not user:
        return

    settings = user.get("settings", {})
    reminders = settings.get("reminder_minutes", [1440, 60])
    notif = settings.get("notifications_enabled", True)

    text = (
        "<b>Настройки</b>\n\n"
        f"Уведомления: {'включены' if notif else 'выключены'}\n"
        f"Напоминания: {_format_reminder_list(reminders)}\n"
    )

    buttons = [
        [InlineKeyboardButton(
            f"{'🔔 Выкл. уведомления' if notif else '🔕 Вкл. уведомления'}",
            callback_data=f"{SETTINGS_CB}notif_toggle",
        )],
        [InlineKeyboardButton(
            "⏰ Настроить напоминания",
            callback_data=f"{SETTINGS_CB}reminders",
        )],
    ]

    msg = update.message or update.callback_query.message
    await msg.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle settings button presses."""
    query = update.callback_query
    await query.answer()

    action = query.data.removeprefix(SETTINGS_CB)
    db = get_db()
    user = await db.users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        return

    settings = user.get("settings", {})

    if action == "notif_toggle":
        new_val = not settings.get("notifications_enabled", True)
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"settings.notifications_enabled": new_val}},
        )
        await query.edit_message_text(
            f"Уведомления {'включены 🔔' if new_val else 'выключены 🔕'}",
        )
        return

    if action == "reminders":
        current = settings.get("reminder_minutes", [1440, 60])
        if isinstance(current, (int, float)):
            current = [int(current)]

        buttons = []
        for minutes, label in REMINDER_OPTIONS:
            is_active = minutes in current if minutes > 0 else (not current or current == [0])
            mark = "✅ " if is_active else ""
            buttons.append([InlineKeyboardButton(
                f"{mark}{label}",
                callback_data=f"{SETTINGS_CB}rem_{minutes}",
            )])
        buttons.append([InlineKeyboardButton("« Назад", callback_data=f"{SETTINGS_CB}back")])

        await query.edit_message_text(
            f"<b>Напоминания</b>\n\nСейчас: {_format_reminder_list(current)}\n\nНажми чтобы вкл/выкл:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if action.startswith("rem_"):
        minutes = int(action.removeprefix("rem_"))
        current = settings.get("reminder_minutes", [1440, 60])
        if isinstance(current, (int, float)):
            current = [int(current)]

        if minutes == 0:
            # Toggle off all
            new_list = [0]
        elif minutes in current:
            # Remove this interval
            new_list = [m for m in current if m != minutes and m != 0]
            if not new_list:
                new_list = [0]
        else:
            # Add this interval, remove 0 if present
            new_list = [m for m in current if m != 0] + [minutes]

        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"settings.reminder_minutes": sorted(new_list)}},
        )

        # Re-render reminder menu
        buttons = []
        for m, label in REMINDER_OPTIONS:
            is_active = m in new_list if m > 0 else (new_list == [0])
            mark = "✅ " if is_active else ""
            buttons.append([InlineKeyboardButton(
                f"{mark}{label}",
                callback_data=f"{SETTINGS_CB}rem_{m}",
            )])
        buttons.append([InlineKeyboardButton("« Назад", callback_data=f"{SETTINGS_CB}back")])

        await query.edit_message_text(
            f"<b>Напоминания</b>\n\nСейчас: {_format_reminder_list(new_list)}\n\nНажми чтобы вкл/выкл:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return

    if action == "back":
        # Re-show main settings
        user = await db.users.find_one({"telegram_id": update.effective_user.id})
        settings = user.get("settings", {})
        reminders = settings.get("reminder_minutes", [1440, 60])
        notif = settings.get("notifications_enabled", True)

        text = (
            "<b>Настройки</b>\n\n"
            f"Уведомления: {'включены' if notif else 'выключены'}\n"
            f"Напоминания: {_format_reminder_list(reminders)}\n"
        )

        buttons = [
            [InlineKeyboardButton(
                f"{'🔔 Выкл. уведомления' if notif else '🔕 Вкл. уведомления'}",
                callback_data=f"{SETTINGS_CB}notif_toggle",
            )],
            [InlineKeyboardButton(
                "⏰ Настроить напоминания",
                callback_data=f"{SETTINGS_CB}reminders",
            )],
        ]

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))
