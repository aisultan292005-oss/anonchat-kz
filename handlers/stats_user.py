from datetime import timezone
from aiogram import F, Router
from aiogram.types import Message
import database.repo as repo
from utils.design import msg_user_stats, msg_global_stats

router = Router()


@router.message(F.text == "📊 Статистика")
async def btn_stats(message: Message):
    user = await repo.get_user(message.from_user.id)
    global_stats = await repo.get_stats()

    if not user or not user.is_registered:
        await message.answer(msg_global_stats(global_stats))
        return

    avg_len = await repo.get_avg_session_length(message.from_user.id)
    avg_str = f"{avg_len:.0f} сообщ." if avg_len else "нет данных"
    peak_hour = await repo.get_peak_hour(message.from_user.id)
    peak_str = f"{peak_hour}:00 — {peak_hour+1}:00" if peak_hour is not None else "нет данных"
    import datetime
    days = (datetime.datetime.now(timezone.utc) - user.created_at).days if user.created_at else 0

    await message.answer(msg_user_stats(user, avg_str, peak_str, days, global_stats))
