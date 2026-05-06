from aiogram import Router
from handlers.welcome import router as welcome_router
from handlers.captcha import router as captcha_router
from handlers.registration import router as reg_router
from handlers.navigation import router as nav_router
from handlers.chat import router as chat_router
from handlers.reports import router as report_router
from handlers.premium import router as premium_router
from handlers.admin import router as admin_router
from handlers.filters_setup import router as filters_router
from handlers.stats_user import router as stats_router
from handlers.settings import router as settings_router
from handlers.rating import router as rating_router
from handlers.gifts import router as gifts_router
from handlers.rooms import router as rooms_router
from handlers.notifications import router as notif_router
from handlers.referral import router as referral_router
from handlers.broadcast import router as broadcast_router
from handlers.calls import router as calls_router

main_router = Router()
main_router.include_routers(
    welcome_router,
    captcha_router,
    reg_router,
    nav_router,
    rating_router,
    gifts_router,
    rooms_router,
    notif_router,
    referral_router,
    broadcast_router,
    calls_router,
    chat_router,
    report_router,
    premium_router,
    admin_router,
    filters_router,
    stats_router,
    settings_router,
)
