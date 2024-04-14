import asyncio
import logging
import configparser
import sys
import json
from io import BytesIO, StringIO
from PIL import Image

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

from demotivate import generateDemotivator
from utils import normalizeStringForDemotivator, smartImageResize

logging.basicConfig(level=logging.INFO, stream=sys.stdout)\

config = configparser.ConfigParser()
config.read('credentials.cfg')

bot = Bot(config['BOT']['Token'])
dp = Dispatcher()

# Приветствие бота
@dp.message(CommandStart())
async def commandStartHandler(message: types.Message) -> None:
    await message.answer(f'Пошел нахуй {message.from_user.full_name}!')

# Помощь в командах бота
@dp.message(Command('help', 'h'))
async def commandHelpHandler(message: types.Message) -> None:
    help_msg = "Пошел нахуй, команд нет"
    await message.answer(help_msg)

# Генератор демотиваторов вручную через команду
# Можно как отправить команду с текстом и картинкой,
# Так и ответив на картинку написать команду с текстом
# И получить в результате демотиватор
@dp.message(Command('demotivator', 'dem', 'd'))
async def commandDemotivatorHandler(message: types.Message) -> None:
    try:
        command_args = message.text.split(' ')[1:]
    except:
        command_args = message.caption.split(' ')[1:]
    finally:
        args_string = ' '.join(command_args)
        
        try:
            photo = message.photo[-1]
        except:
            photo = message.reply_to_message.photo[-1]            
        finally:
            dem_text = await normalizeStringForDemotivator(args_string)
            
            photo_bytes = BytesIO()
            await bot.download(photo.file_id, photo_bytes)
            
            image = Image.open(photo_bytes)
            image = await smartImageResize(image)
            demotivator_image = await generateDemotivator(image, dem_text)
            
            img_byte_array = BytesIO()
            demotivator_image.save(img_byte_array, format="PNG")
            img_byte_array.seek(0)
            
            await message.answer_photo(types.BufferedInputFile(img_byte_array.getvalue(), "aboba.png"))

@dp.message()
async def catchMessages(message: types.Message) -> None:
    # Обработчик любых сообщений
    # Классификация по группам/личным чатам/каналам
    # Обработка простых команд
    try:
        pass
    except:
        pass
    finally:
        pass

async def main() -> None:
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())