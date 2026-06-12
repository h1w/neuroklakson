from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher

from config import load_legacy_config, load_settings
from handlers import common, generation, learning
from repositories.database import Database

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

config = load_legacy_config()


async def main() -> None:
    settings = load_settings()
    bot = Bot(settings.bot_token)
    database = Database(settings.database_url)
    dispatcher = Dispatcher()
    dispatcher.include_router(common.router)
    dispatcher.include_router(generation.router)
    dispatcher.include_router(learning.router)

    try:
        await database.connect()
        bot["database"] = database
        bot["settings"] = settings
        await dispatcher.start_polling(bot)
    finally:
        await database.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
