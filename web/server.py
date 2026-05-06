import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from aiohttp import web
from database.engine import init_db
from database.models import Session, ChatMessage, User
from database import repo
from sqlalchemy import select, desc, and_
from database.engine import async_session_factory

logger = logging.getLogger(__name__)
PANEL_DIR = os.path.dirname(__file__)


async def api_stats(request):
    stats = await repo.get_stats()
    return web.json_response(stats)


async def api_active_chats(request):
    """Active sessions from DB (ended_at is NULL) + in-memory active."""
    result = []
    seen = set()

    async with async_session_factory() as s:
        # Get sessions that are not ended yet
        r = await s.execute(
            select(Session)
            .where(Session.ended_at == None)
            .order_by(desc(Session.started_at))
            .limit(50)
        )
        sessions = r.scalars().all()

        for sess in sessions:
            pair = tuple(sorted([sess.user_a, sess.user_b]))
            if pair in seen:
                continue
            seen.add(pair)

            user_a = await s.get(User, sess.user_a)
            user_b = await s.get(User, sess.user_b)

            # Last message
            lm = await s.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == sess.id)
                .order_by(desc(ChatMessage.sent_at))
                .limit(1)
            )
            last_msg_obj = lm.scalar_one_or_none()
            last_msg = last_msg_obj.content[:60] if last_msg_obj else None

            from database.cities import KZ_CITIES

            def user_info(u):
                if not u:
                    return "неизвестно"
                g = "👨" if str(u.gender) in ("Gender.male", "male") else "👩"
                return f"{g} {u.age or '?'} лет"

            def city_label(u):
                if not u or not u.city:
                    return ""
                return next((c for l, c in KZ_CITIES if c == u.city), u.city)

            # Check if truly active (in memory) or just not closed
            is_live = repo.in_chat(sess.user_a) or repo.in_chat(sess.user_b)

            result.append({
                "session_id": sess.id,
                "user_a": sess.user_a,
                "user_b": sess.user_b,
                "user_a_info": user_info(user_a),
                "user_b_info": user_info(user_b),
                "city_a": city_label(user_a),
                "city_b": city_label(user_b),
                "gender_a": "male" if user_a and str(user_a.gender) in ("Gender.male", "male") else "female",
                "last_message": last_msg,
                "started_at": sess.started_at.isoformat() if sess.started_at else "",
                "is_live": is_live,
            })

    return web.json_response(result)


async def api_queue(request):
    import datetime
    result = []
    async with async_session_factory() as s:
        for uid, meta in list(repo._queue.items()):
            user = await s.get(User, uid)
            if not user:
                continue
            from database.cities import KZ_CITIES
            city = next((c for l, c in KZ_CITIES if c == user.city), user.city or "")
            g = "👨" if str(user.gender) in ("Gender.male", "male") else "👩"
            result.append({
                "user_id": uid,
                "info": f"{g} {user.age or '?'} лет",
                "city": city,
                "gender": "male" if str(user.gender) in ("Gender.male", "male") else "female",
                "joined_at": datetime.datetime.now().isoformat(),
            })
    return web.json_response(result)


async def api_messages(request):
    session_id = int(request.match_info["session_id"])

    async with async_session_factory() as s:
        r = await s.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.sent_at)
        )
        messages = r.scalars().all()

    sides = {}
    result = []
    for m in messages:
        if m.sender_id not in sides:
            sides[m.sender_id] = "a" if len(sides) == 0 else "b"
        result.append({
            "sender_id": m.sender_id,
            "content": m.content,
            "sent_at": m.sent_at.isoformat(),
            "side": sides[m.sender_id],
        })
    return web.json_response(result)


async def api_all_sessions(request):
    """Last 20 sessions including ended ones."""
    result = []
    async with async_session_factory() as s:
        r = await s.execute(
            select(Session).order_by(desc(Session.started_at)).limit(20)
        )
        sessions = r.scalars().all()
        from database.cities import KZ_CITIES

        for sess in sessions:
            user_a = await s.get(User, sess.user_a)
            user_b = await s.get(User, sess.user_b)

            def user_info(u):
                if not u: return "неизвестно"
                g = "👨" if str(u.gender) in ("Gender.male","male") else "👩"
                return f"{g} {u.age or '?'} лет"

            def city_label(u):
                if not u or not u.city: return ""
                return next((c for l, c in KZ_CITIES if c == u.city), u.city)

            lm = await s.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == sess.id)
                .order_by(desc(ChatMessage.sent_at)).limit(1)
            )
            last = lm.scalar_one_or_none()

            result.append({
                "session_id": sess.id,
                "user_a": sess.user_a,
                "user_b": sess.user_b,
                "user_a_info": user_info(user_a),
                "user_b_info": user_info(user_b),
                "city_a": city_label(user_a),
                "city_b": city_label(user_b),
                "gender_a": "male" if user_a and str(user_a.gender) in ("Gender.male","male") else "female",
                "last_message": last.content[:60] if last else None,
                "started_at": sess.started_at.isoformat() if sess.started_at else "",
                "ended_at": sess.ended_at.isoformat() if sess.ended_at else None,
                "is_live": sess.ended_at is None,
            })
    return web.json_response(result)


async def serve_panel(request):
    return web.FileResponse(os.path.join(PANEL_DIR, "panel.html"))


async def create_app():
    await init_db()
    app = web.Application()
    app.router.add_get("/", serve_panel)
    app.router.add_get("/api/stats", api_stats)
    app.router.add_get("/api/active-chats", api_active_chats)
    app.router.add_get("/api/all-sessions", api_all_sessions)
    app.router.add_get("/api/queue", api_queue)
    app.router.add_get("/api/messages/{session_id}", api_messages)
    return app


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)

    async def main():
        app = await create_app()
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8080)
        await site.start()
        logger.info("Панель мониторинга: http://localhost:8080")
        await asyncio.Event().wait()

    asyncio.run(main())
