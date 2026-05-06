"""
Simple translation via MyMemory free API.
No API key required for small volumes.
"""
import logging
import aiohttp

logger = logging.getLogger(__name__)

LANG_CODES = {"ru": "ru", "en": "en", "kz": "kk"}


async def translate(text: str, from_lang: str, to_lang: str) -> str:
    if from_lang == to_lang:
        return text
    if len(text) > 500:
        text = text[:500]
    try:
        fl = LANG_CODES.get(from_lang, "ru")
        tl = LANG_CODES.get(to_lang, "ru")
        url = f"https://api.mymemory.translated.net/get?q={aiohttp.helpers.quote(text)}&langpair={fl}|{tl}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=3)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    translated = data.get("responseData", {}).get("translatedText", "")
                    if translated:
                        return f"{translated}\n<i>🌐 переведено</i>"
    except Exception as e:
        logger.warning("Translation failed: %s", e)
    return text
