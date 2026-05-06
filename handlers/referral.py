"""Referral system — invite friends, get Premium."""
import logging
from aiogram import F, Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()

REFERRALS_FOR_PREMIUM = 3   # invites needed for free Premium
PREMIUM_DAYS_REWARD = 7     # days of Premium per referral milestone


def referral_kb(bot_username: str, user_id: int) -> object:
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    b = InlineKeyboardBuilder()
    b.button(text="📤 Поделиться ссылкой", switch_inline_query=f"Присоединяйся к AnonChat KZ! {link}")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    b.adjust(1)
    return b.as_markup()


@router.message(F.text == "👥 Рефералы")
async def btn_referral(message: Message, bot: Bot):
    user = await repo.get_user(message.from_user.id)
    if not user or not user.is_registered:
        await message.answer("Необходимо пройти регистрацию: /start")
        return

    ref_count = await repo.get_referral_count(message.from_user.id)
    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start=ref_{message.from_user.id}"
    needed = REFERRALS_FOR_PREMIUM - (ref_count % REFERRALS_FOR_PREMIUM)
    progress = "●" * (ref_count % REFERRALS_FOR_PREMIUM) + "○" * needed

    await message.answer(
        f"<b>Реферальная программа</b>\n{DIV}\n"
        f"Приглашай друзей — получай Premium!\n\n"
        f"Твоя ссылка:\n<code>{link}</code>\n\n"
        f"Приглашено: <b>{ref_count}</b>\n"
        f"До награды: <b>{needed}</b> {progress}\n"
        f"Награда: <b>{PREMIUM_DAYS_REWARD} дней Premium</b> за каждые {REFERRALS_FOR_PREMIUM} друзей",
        reply_markup=referral_kb(bot_info.username, message.from_user.id),
    )


async def process_referral(new_user_id: int, referrer_id: int, bot: Bot):
    """Called when a new user registers via referral link."""
    if new_user_id == referrer_id:
        return

    await repo.add_referral(referrer_id, new_user_id)
    ref_count = await repo.get_referral_count(referrer_id)

    logger.info("Referral: %s invited by %s (total: %s)", new_user_id, referrer_id, ref_count)

    # Reward every N referrals
    if ref_count % REFERRALS_FOR_PREMIUM == 0:
        await repo.activate_premium_days(referrer_id, PREMIUM_DAYS_REWARD)
        try:
            await bot.send_message(
                referrer_id,
                f"<b>Награда получена!</b>\n{DIV}\n"
                f"Вы пригласили <b>{ref_count}</b> друзей!\n"
                f"Начислено: <b>+{PREMIUM_DAYS_REWARD} дней Premium</b> ⭐"
            )
        except Exception as e:
            logger.warning("Failed to notify referrer: %s", e)
    else:
        needed = REFERRALS_FOR_PREMIUM - (ref_count % REFERRALS_FOR_PREMIUM)
        try:
            await bot.send_message(
                referrer_id,
                f"<b>Новый реферал!</b>\n{DIV}\n"
                f"Друг зарегистрировался по вашей ссылке.\n"
                f"До Premium: ещё <b>{needed}</b> приглашений"
            )
        except Exception:
            pass
