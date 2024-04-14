import asyncio
import logging
import configparser
import sys

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

logging.basicConfig(level=logging.INFO, stream=sys.stdout)\

config = configparser.ConfigParser()
config.read('credentials.cfg')

bot = Bot(config['BOT']['Token'])
dp = Dispatcher()

@dp.message(CommandStart())
async def commandStartHandler(message: types.Message) -> None:
    await message.answer(f'Пошел нахуй {message.from_user.full_name}!')

@dp.message(Command('help'))
async def commandHelpHandler(message: types.Message) -> None:
    help_msg = "Пошел нахуй, команд нет"
    await message.answer(help_msg)

@dp.message()
async def catchMessages(message: types.Message) -> None:
    await message.answer(message.text)

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())