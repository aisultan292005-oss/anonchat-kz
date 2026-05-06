"""Like/dislike system after each chat."""
import logging
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()


def rate_kb(partner_id: int) -> object:
    b = InlineKeyboardBuilder()
    b.row(
        InlineKeyboardButton(text="👍 Лайк", callback_data=f"rate:like:{partner_id}"),
        InlineKeyboardButton(text="👎 Дизлайк", callback_data=f"rate:dislike:{partner_id}"),
    )
    b.row(InlineKeyboardButton(text="— Пропустить", callback_data="rate:skip"))
    return b.as_markup()


async def ask_rating(user_id: int, partner_id: int, bot: Bot):
    try:
        await bot.send_message(
            user_id,
            f"<b>Оцените собеседника</b>\n{DIV}\nКак прошло общение?",
            reply_markup=rate_kb(partner_id),
        )
    except Exception as e:
        logger.warning("Failed to send rating: %s", e)


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate(call: CallbackQuery, bot: Bot):
    parts = call.data.split(":")
    action = parts[1]

    if action == "skip":
        await call.message.edit_text(f"— Оценка пропущена.")
        return

    partner_id = int(parts[2])
    partner = await repo.get_user(partner_id)
    if not partner:
        await call.message.edit_text("Пользователь не найден.")
        return

    if action == "like":
        new_rep = partner.reputation + 1
        await repo.update_user(partner_id, reputation=new_rep)
        await call.message.edit_text(
            f"<b>Лайк отправлен!</b>\n{DIV}\nСпасибо за оценку."
        )
        try:
            await bot.send_message(
                partner_id,
                f"<b>Вам поставили лайк!</b>\n{DIV}\n"
                f"Ваш рейтинг: <b>{new_rep} ⭐</b>"
            )
        except Exception:
            pass
    else:
        new_rep = max(0, partner.reputation - 1)
        await repo.update_user(partner_id, reputation=new_rep)
        await call.message.edit_text(
            f"<b>Дизлайк отправлен.</b>\n{DIV}\nСпасибо за оценку."
        )

    logger.info("Rating: %s -> %s: %s", call.from_user.id, partner_id, action)
