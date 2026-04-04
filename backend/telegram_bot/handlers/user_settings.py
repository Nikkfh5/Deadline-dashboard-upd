import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from services.database import get_db
from telegram_bot.utils import get_current_user

WAITING_CUSTOM_MINUTES = 99

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


def _render_reminder_buttons(current: list) -> InlineKeyboardMarkup:
    buttons = []
    for minutes, label in REMINDER_OPTIONS:
        is_active = minutes in current if minutes > 0 else (not current or current == [0])
        mark = "✅ " if is_active else ""
        buttons.append([InlineKeyboardButton(
            f"{mark}{label}",
            callback_data=f"{SETTINGS_CB}rem_{minutes}",
        )])
    # Custom intervals already set (not in REMINDER_OPTIONS)
    standard = {m for m, _ in REMINDER_OPTIONS}
    for m in sorted(current):
        if m > 0 and m not in standard:
            buttons.append([InlineKeyboardButton(
                f"✅ {m} мин (свой)",
                callback_data=f"{SETTINGS_CB}rem_{m}",
            )])
    buttons.append([InlineKeyboardButton("➕ Свой интервал (мин)", callback_data=f"{SETTINGS_CB}custom")])
    buttons.append([InlineKeyboardButton("« Назад", callback_data=f"{SETTINGS_CB}back")])
    return InlineKeyboardMarkup(buttons)


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
    parsing = settings.get("channel_parsing_enabled", True)

    text = (
        "<b>Настройки</b>\n\n"
        f"Уведомления: {'включены' if notif else 'выключены'}\n"
        f"Парсинг каналов: {'включён' if parsing else 'выключен'}\n"
        f"Напоминания: {_format_reminder_list(reminders)}\n"
    )

    buttons = [
        [InlineKeyboardButton(
            f"{'🔔 Выкл. уведомления' if notif else '🔕 Вкл. уведомления'}",
            callback_data=f"{SETTINGS_CB}notif_toggle",
        )],
        [InlineKeyboardButton(
            f"{'📡 Выкл. парсинг каналов' if parsing else '📡 Вкл. парсинг каналов'}",
            callback_data=f"{SETTINGS_CB}parsing_toggle",
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

    if action == "parsing_toggle":
        new_val = not settings.get("channel_parsing_enabled", True)
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"settings.channel_parsing_enabled": new_val}},
        )
        await query.edit_message_text(
            f"Парсинг каналов {'включён 📡' if new_val else 'выключен 🚫'}\n\n"
            + ("Новые дедлайны из каналов будут автоматически добавляться." if new_val
               else "Дедлайны из каналов больше не будут парситься."),
        )
        return

    if action == "reminders":
        current = settings.get("reminder_minutes", [1440, 60])
        if isinstance(current, (int, float)):
            current = [int(current)]

        await query.edit_message_text(
            f"<b>Напоминания</b>\n\nСейчас: {_format_reminder_list(current)}\n\nНажми чтобы вкл/выкл:",
            parse_mode="HTML",
            reply_markup=_render_reminder_buttons(current),
        )
        return

    if action == "custom":
        context.user_data["awaiting_custom_reminder"] = True
        await query.edit_message_text("Введи количество минут (число):")
        return

    if action.startswith("rem_"):
        minutes = int(action.removeprefix("rem_"))
        current = settings.get("reminder_minutes", [1440, 60])
        if isinstance(current, (int, float)):
            current = [int(current)]

        if minutes == 0:
            new_list = [0]
        elif minutes in current:
            new_list = [m for m in current if m != minutes and m != 0]
            if not new_list:
                new_list = [0]
        else:
            new_list = [m for m in current if m != 0] + [minutes]

        await db.users.update_one(
            {"_id": user["_id"]},
            {"$set": {"settings.reminder_minutes": sorted(new_list)}},
        )

        await query.edit_message_text(
            f"<b>Напоминания</b>\n\nСейчас: {_format_reminder_list(new_list)}\n\nНажми чтобы вкл/выкл:",
            parse_mode="HTML",
            reply_markup=_render_reminder_buttons(new_list),
        )
        return

    if action == "back":
        # Re-show main settings
        user = await db.users.find_one({"telegram_id": update.effective_user.id})
        settings = user.get("settings", {})
        reminders = settings.get("reminder_minutes", [1440, 60])
        notif = settings.get("notifications_enabled", True)
        parsing = settings.get("channel_parsing_enabled", True)

        text = (
            "<b>Настройки</b>\n\n"
            f"Уведомления: {'включены' if notif else 'выключены'}\n"
            f"Парсинг каналов: {'включён' if parsing else 'выключен'}\n"
            f"Напоминания: {_format_reminder_list(reminders)}\n"
        )

        buttons = [
            [InlineKeyboardButton(
                f"{'🔔 Выкл. уведомления' if notif else '🔕 Вкл. уведомления'}",
                callback_data=f"{SETTINGS_CB}notif_toggle",
            )],
            [InlineKeyboardButton(
                f"{'📡 Выкл. парсинг каналов' if parsing else '📡 Вкл. парсинг каналов'}",
                callback_data=f"{SETTINGS_CB}parsing_toggle",
            )],
            [InlineKeyboardButton(
                "⏰ Настроить напоминания",
                callback_data=f"{SETTINGS_CB}reminders",
            )],
        ]

        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(buttons))


async def custom_reminder_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle custom reminder minutes input."""
    if not context.user_data.get("awaiting_custom_reminder"):
        return False  # Not for us

    context.user_data.pop("awaiting_custom_reminder", None)

    text = update.message.text.strip()
    try:
        minutes = int(text)
    except ValueError:
        await update.message.reply_text("Нужно число. Попробуй /settings заново.")
        return True

    if minutes < 1 or minutes > 10080:
        await update.message.reply_text("От 1 до 10080 минут (7 дней). Попробуй /settings заново.")
        return True

    db = get_db()
    user = await db.users.find_one({"telegram_id": update.effective_user.id})
    if not user:
        return True

    current = user.get("settings", {}).get("reminder_minutes", [1440, 60])
    if isinstance(current, (int, float)):
        current = [int(current)]

    new_list = [m for m in current if m != 0] + [minutes]
    new_list = sorted(set(new_list))

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"settings.reminder_minutes": new_list}},
    )

    await update.message.reply_text(
        f"Добавлено: {minutes} мин\nНапоминания: {_format_reminder_list(new_list)}",
    )
    return True
