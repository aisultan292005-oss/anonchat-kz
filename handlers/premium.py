import logging
from aiogram import Bot, F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery, SuccessfulPayment

import database.repo as repo
from config import PAYMENT_PROVIDER_TOKEN, PREMIUM_DAYS, PREMIUM_PRICE_XTR
from database.models import Gender
from keyboards import main_menu_kb
try:
    from handlers.welcome import bottom_menu_kb
except ImportError:
    bottom_menu_kb = main_menu_kb, premium_kb, pref_gender_kb
from utils.design import msg_premium_info, msg_premium_offer, msg_premium_activated

logger = logging.getLogger(__name__)
router = Router()


def _pref_label(pref: Gender | None) -> str:
    if pref == Gender.male: return "Только мужчины"
    if pref == Gender.female: return "Только женщины"
    return "Случайный выбор"


@router.message(F.text == "⭐ Premium")
async def btn_premium(message: Message):
    user = await repo.get_user(message.from_user.id)
    is_prem = await repo.is_premium_active(message.from_user.id)
    if is_prem:
        until = user.premium_until.strftime("%d.%m.%Y") if user.premium_until else "∞"
        pref_label = _pref_label(user.pref_gender)
        await message.answer(
            msg_premium_info(until, pref_label),
            reply_markup=pref_gender_kb(user.pref_gender.value if user.pref_gender else None),
        )
    else:
        await message.answer(
            msg_premium_offer(PREMIUM_PRICE_XTR, PREMIUM_DAYS),
            reply_markup=premium_kb(),
        )


@router.callback_query(F.data == "buy_premium")
async def cb_buy_premium(call: CallbackQuery, bot: Bot):
    await call.message.delete()
    await bot.send_invoice(
        chat_id=call.from_user.id,
        title="Premium подписка",
        description=f"Анонимный чат · Premium · {PREMIUM_DAYS} дней",
        payload="premium_subscription",
        provider_token=PAYMENT_PROVIDER_TOKEN,
        currency="XTR",
        prices=[LabeledPrice(label="Premium", amount=PREMIUM_PRICE_XTR)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def payment_received(message: Message):
    payment: SuccessfulPayment = message.successful_payment
    uid = message.from_user.id
    await repo.save_payment(uid, payment.telegram_payment_charge_id, payment.total_amount)
    await repo.activate_premium(uid)
    user = await repo.get_user(uid)
    until = user.premium_until.strftime("%d.%m.%Y") if user and user.premium_until else ""
    logger.info("Premium activated: %s", uid)
    await message.answer(msg_premium_activated(PREMIUM_DAYS, until), reply_markup=bottom_menu_kb())


@router.callback_query(F.data.startswith("pref:"))
async def cb_pref(call: CallbackQuery):
    if not await repo.is_premium_active(call.from_user.id):
        await call.answer("Доступно только для Premium", show_alert=True)
        return
    val = call.data.split(":")[1]
    pref = None if val == "none" else (Gender.male if val == "male" else Gender.female)
    await repo.update_user(call.from_user.id, pref_gender=pref)
    await call.answer(f"Фильтр: {_pref_label(pref)}")
    user = await repo.get_user(call.from_user.id)
    await call.message.edit_reply_markup(
        reply_markup=pref_gender_kb(user.pref_gender.value if user.pref_gender else None)
    )


@router.callback_query(F.data == "back_main")
async def cb_back_main(call: CallbackQuery):
    await call.message.delete()
