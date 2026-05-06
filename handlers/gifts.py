"""Gift system — send sticker gifts to partner for Stars."""
import logging
from aiogram import F, Router, Bot
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, SuccessfulPayment
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

import database.repo as repo
from utils.design import DIV

logger = logging.getLogger(__name__)
router = Router()

GIFTS = [
    {"id": "gift_heart",   "name": "❤️ Сердце",     "price": 10,  "emoji": "❤️"},
    {"id": "gift_fire",    "name": "🔥 Огонь",       "price": 15,  "emoji": "🔥"},
    {"id": "gift_star",    "name": "⭐ Звезда",      "price": 20,  "emoji": "⭐"},
    {"id": "gift_crown",   "name": "👑 Корона",      "price": 50,  "emoji": "👑"},
    {"id": "gift_diamond", "name": "💎 Бриллиант",   "price": 100, "emoji": "💎"},
]


def gifts_kb() -> object:
    b = InlineKeyboardBuilder()
    for g in GIFTS:
        b.button(text=f"{g['emoji']} {g['name']} · {g['price']} ⭐", callback_data=f"send_gift:{g['id']}")
    b.row(InlineKeyboardButton(text="← Назад", callback_data="nav:main"))
    b.adjust(1)
    return b.as_markup()


@router.message(F.text == "🎁 Подарок")
async def btn_gift(message: Message):
    if not repo.in_chat(message.from_user.id):
        await message.answer(f"<b>Подарки</b>\n{DIV}\nПодарки можно отправлять только во время активного чата.")
        return
    await message.answer(
        f"<b>Отправить подарок собеседнику</b>\n{DIV}\n"
        f"Выберите подарок — собеседник увидит его анонимно:",
        reply_markup=gifts_kb(),
    )


@router.callback_query(F.data.startswith("send_gift:"))
async def cb_send_gift(call: CallbackQuery, bot: Bot):
    if not repo.in_chat(call.from_user.id):
        await call.answer("Вы не в чате", show_alert=True)
        return

    gift_id = call.data.split(":")[1]
    gift = next((g for g in GIFTS if g["id"] == gift_id), None)
    if not gift:
        return

    partner_id = repo.get_partner(call.from_user.id)
    if not partner_id:
        await call.answer("Собеседник недоступен", show_alert=True)
        return

    from config import PAYMENT_PROVIDER_TOKEN
    await call.message.delete()
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title=f"Подарок: {gift['name']}",
        description=f"Анонимный подарок собеседнику",
        payload=f"gift:{gift_id}:{partner_id}",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(label=gift["name"], amount=gift["price"])],
    )


@router.pre_checkout_query(lambda q: q.invoice_payload.startswith("gift:"))
async def pre_checkout_gift(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def gift_payment_received(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    if not payload.startswith("gift:"):
        return

    _, gift_id, partner_id_str = payload.split(":")
    partner_id = int(partner_id_str)
    gift = next((g for g in GIFTS if g["id"] == gift_id), None)
    if not gift:
        return

    await message.answer(
        f"<b>Подарок отправлен!</b>\n{DIV}\n"
        f"Вы анонимно отправили {gift['emoji']} <b>{gift['name']}</b>"
    )
    try:
        await bot.send_message(
            partner_id,
            f"🎁 <b>Вам подарок!</b>\n{DIV}\n"
            f"Собеседник анонимно отправил вам {gift['emoji']} <b>{gift['name']}</b>"
        )
    except Exception as e:
        logger.warning("Failed to deliver gift: %s", e)

    logger.info("Gift sent: %s -> %s: %s", message.from_user.id, partner_id, gift_id)
