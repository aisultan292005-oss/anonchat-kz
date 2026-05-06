import logging

from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, Message

import database.repo as repo
from config import ADMIN_IDS
from keyboards import main_menu_kb
try:
    from handlers.welcome import bottom_menu_kb
except ImportError:
    bottom_menu_kb = main_menu_kb, report_reason_kb

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.text == "🚨 Пожаловаться")
async def btn_report(message: Message):
    if not repo.in_chat(message.from_user.id):
        await message.answer("ℹ️ Жалобу можно подать только во время активного чата.")
        return
    await message.answer(
        "⚠️ Выбери причину жалобы:",
        reply_markup=report_reason_kb(),
    )


@router.callback_query(F.data.startswith("report:"))
async def cb_report(call: CallbackQuery, bot: Bot):
    reason_key = call.data.split(":")[1]
    if reason_key == "cancel":
        await call.message.edit_text("❌ Жалоба отменена.")
        return

    reason_map = {
        "indecent": "🔞 Непристойный контент",
        "insults": "🤬 Оскорбления",
        "spam": "🤖 Спам / бот",
        "other": "⚠️ Другое",
    }
    reason_text = reason_map.get(reason_key, "Другое")

    user_id = call.from_user.id
    partner_id = repo.get_partner(user_id)
    session_id = repo.get_session_db_id(user_id)

    if not partner_id:
        await call.message.edit_text("ℹ️ Ты больше не в чате.")
        return

    # Save report to DB
    report = await repo.create_report(user_id, partner_id, session_id, reason_text)

    # Fetch last messages for moderation
    history_lines = []
    if session_id:
        messages = await repo.get_recent_messages(session_id)
        for m in messages:
            who = "Ты" if m.sender_id == user_id else "Собеседник"
            history_lines.append(f"<b>{who}:</b> {m.content}")

    history_text = "\n".join(history_lines) if history_lines else "— нет сохранённых сообщений —"

    # Notify all admins
    from keyboards import admin_report_kb
    admin_text = (
        f"🚨 <b>Новая жалоба #{report.id}</b>\n\n"
        f"👤 Жалуется: <code>{user_id}</code>\n"
        f"🎯 На пользователя: <code>{partner_id}</code>\n"
        f"📝 Причина: {reason_text}\n\n"
        f"💬 <b>Последние сообщения:</b>\n{history_text}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id, admin_text,
                reply_markup=admin_report_kb(report.id, partner_id),
            )
        except Exception as e:
            logger.warning("Failed to notify admin %s: %s", admin_id, e)

    await call.message.edit_text(
        "✅ Жалоба отправлена. Модератор рассмотрит её в ближайшее время.\n"
        "Спасибо, что помогаешь делать чат безопаснее!"
    )
    logger.info("Report #%s: %s -> %s (%s)", report.id, user_id, partner_id, reason_text)
