import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

import database.repo as repo
from config import ADMIN_IDS
from keyboards import admin_kb, admin_report_kb, main_menu_kb

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not _is_admin(message.from_user.id):
        return
    stats = await repo.get_stats()
    await message.answer(
        f"🛠 <b>Админ-панель</b>\n\n"
        f"👥 Пользователей: <b>{stats['total_users']}</b>\n"
        f"✅ Зарегистрировано: <b>{stats['registered']}</b>\n"
        f"⭐ Premium: <b>{stats['premium']}</b>\n"
        f"🚫 Забанено: <b>{stats['banned']}</b>\n"
        f"💬 Активных чатов: <b>{stats['active_chats']}</b>\n"
        f"🔍 В очереди: <b>{stats['in_queue']}</b>\n"
        f"📋 Открытых жалоб: <b>{stats['open_reports']}</b>",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    stats = await repo.get_stats()
    await call.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"👥 Всего пользователей: <b>{stats['total_users']}</b>\n"
        f"✅ Зарегистрировано: <b>{stats['registered']}</b>\n"
        f"⭐ Premium: <b>{stats['premium']}</b>\n"
        f"🚫 Забанено: <b>{stats['banned']}</b>\n"
        f"💬 Всего сессий: <b>{stats['total_sessions']}</b>\n"
        f"💬 Активных чатов: <b>{stats['active_chats']}</b>\n"
        f"🔍 В очереди: <b>{stats['in_queue']}</b>\n"
        f"📋 Открытых жалоб: <b>{stats['open_reports']}</b>",
        reply_markup=admin_kb(),
    )


@router.callback_query(F.data == "admin:reports")
async def cb_admin_reports(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    reports = await repo.get_open_reports()
    if not reports:
        await call.answer("✅ Нет открытых жалоб!", show_alert=True)
        return

    await call.message.edit_text(
        f"📋 Открытых жалоб: <b>{len(reports)}</b>\n\nОтправляю по одной..."
    )
    for r in reports[:5]:  # Show max 5 at once
        await call.message.answer(
            f"📋 <b>Жалоба #{r.id}</b>\n"
            f"От: <code>{r.reporter_id}</code>\n"
            f"На: <code>{r.reported_id}</code>\n"
            f"Причина: {r.reason}\n"
            f"Дата: {r.created_at.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=admin_report_kb(r.id, r.reported_id),
        )


@router.callback_query(F.data.startswith("admin_ban:"))
async def cb_admin_ban(call: CallbackQuery, bot):
    if not _is_admin(call.from_user.id):
        return
    _, reported_id_str, report_id_str = call.data.split(":")
    reported_id = int(reported_id_str)
    report_id = int(report_id_str)

    await repo.ban_user(reported_id)
    await repo.resolve_report(report_id)

    # Disconnect if in chat
    partner_id = repo.get_partner(reported_id)
    if partner_id:
        repo.disconnect(reported_id)
        await bot.send_message(partner_id, "😔 Собеседник был заблокирован модератором.", reply_markup=bottom_menu_kb())
    elif repo.in_queue(reported_id):
        repo.dequeue(reported_id)

    try:
        await bot.send_message(reported_id, "🚫 Ты заблокирован за нарушение правил.")
    except Exception:
        pass

    await call.message.edit_text(
        f"✅ Пользователь <code>{reported_id}</code> заблокирован. Жалоба #{report_id} закрыта."
    )
    logger.info("Admin %s banned user %s (report %s)", call.from_user.id, reported_id, report_id)


@router.callback_query(F.data.startswith("admin_close:"))
async def cb_admin_close(call: CallbackQuery):
    if not _is_admin(call.from_user.id):
        return
    report_id = int(call.data.split(":")[1])
    await repo.resolve_report(report_id)
    await call.message.edit_text(f"✅ Жалоба #{report_id} закрыта без бана.")
    logger.info("Admin %s closed report %s", call.from_user.id, report_id)


# ── /ban & /unban commands ────────────────────────────────────────────────────

@router.message(Command("ban"))
async def cmd_ban(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /ban <user_id>")
        return
    uid = int(parts[1])
    await repo.ban_user(uid)
    await message.answer(f"🚫 Пользователь <code>{uid}</code> заблокирован.")


@router.message(Command("unban"))
async def cmd_unban(message: Message):
    if not _is_admin(message.from_user.id):
        return
    parts = message.text.split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /unban <user_id>")
        return
    uid = int(parts[1])
    await repo.unban_user(uid)
    await message.answer(f"✅ Пользователь <code>{uid}</code> разблокирован.")
