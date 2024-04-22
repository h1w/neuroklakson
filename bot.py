import asyncio
import logging
import configparser
import sys
import json
import random
from io import BytesIO, StringIO
from PIL import Image

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command

from demotivate import generateDemotivator
from utils import normalizeStringForDemotivator, smartImageResize, isTextContainsLink, removeLinkFromText, isTextIsLink, doWithProbability, splitStringIntoLines
import dbconnector as dbc
from markchain import makeShortSentence
from parse2ch import parseTredToPostTextList

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

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
    # help_msg = "Пошел нахуй, команд нет"
    help_msg = """Команды бота:
    \t/start - пошел нахуй
    \t/help, /h - помощь по командам
    \t/createdemotivator, /crdem, /cd - создание демотиватора вручную: отослать картинку с текстом или ответить на картинку с текстом демотиватора
    \t/demotivatorgeneration, /demgen, /d - демотиватор на основе картинок и сообщений чата
    \t/generatemessage, /genmsg, /gm - сгенерировать бредосообщение
    \t/generatebugurt, /genbug, /b - Сгенерировать бугурт
    """
    await message.answer(help_msg)

# Генератор демотиваторов вручную через команду
# Можно как отправить команду с текстом и картинкой,
# Так и ответив на картинку написать команду с текстом
# И получить в результате демотиватор
@dp.message(Command('createdemotivator', 'crdem', 'cd'))
async def commandCreateDemotivatorManuallyHandler(message: types.Message) -> None:
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

# Автоматическая генерация Демотиваторов
# Рандомная картинка из беседы + рандомная сгенерированная фраза из беседы
@dp.message(Command('demotivatorgeneration', 'demgen', 'd'))
async def commandDemotivatorGeneratorHandler(message: types.Message) -> None:
    try:
        # Взять рандомную картинку
        # Сделать рандомную фразу
        # Сделать демотиватор
        # Отправить в чат
        chat_id = message.chat.id
        
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoDemotivatorMinWordSize']), int(config['BOT']['BredoDemotivatorMaxWordSize'])))
        
        if answer_msg == None:
            answer_msg = "Я ещё очень тупой, нужно немного подождать"
            await message.answer(f'{answer_msg}')
        else:
            photo_file_id = await dbc.getRandomPhoto(chat_id)
            msg = answer_msg
            
            photo_bytes = BytesIO()
            await bot.download(photo_file_id, photo_bytes)
            
            image = Image.open(photo_bytes)
            image = await smartImageResize(image)
            demotivator_image = await generateDemotivator(image, msg)
            
            img_byte_array = BytesIO()
            demotivator_image.save(img_byte_array, format="PNG")
            img_byte_array.seek(0)
            
            await message.answer_photo(types.BufferedInputFile(img_byte_array.getvalue(), "aboba.png"))
    except:
        pass
    finally:
        pass

# генерация сообщений
# Команда для генерации сообщений
@dp.message(Command('generatemessage', 'genmsg', 'gm'))
async def commandGenerateMessageHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoMessageMinWordSize']), int(config['BOT']['BredoMessageMaxWordSize'])))
        
        if answer_msg == None:
            answer_msg = "Я ещё очень тупой, нужно немного подождать"
            await message.answer(f'{answer_msg}')
        else:
            await message.answer(f'{answer_msg}')
    except Exception as e:
        answer_msg = "Еще слишком рано\nПодожди немного"
        await message.answer(f'{answer_msg}')
        pass
    finally:
        pass

# Генератор бугуртов
# Сгенерировать бугурт
@dp.message(Command('generatebugurt', 'genbug', 'b'))
async def commandGenerateBugurtHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoBugurtMessageMinWordSize']), int(config['BOT']['BredoBugurtMessageMaxWordSize'])))
        if answer_msg == None:
            answer_msg = "Я ещё очень тупой, нужно немного подождать"
            await message.answer(f'{answer_msg}')
        else:
            bugurt_text_lines = await splitStringIntoLines(answer_msg, int(config['BOT']['BredoBugurtMessageMinWordsPerLine']), int(config['BOT']['BredoBugurtMessageMaxWordsPerLine']), int(config['BOT']['BredoBugurtMessageMinLines']), int(config['BOT']['BredoBugurtMessageMaxLines']))
            bugurt_text = '\n@\n'.join(bugurt_text_lines)
            await message.answer(f'{bugurt_text}')
        
    except Exception as e:
        print(e)
        answer_msg = "Еще слишком рано\nПодожди немного"
        await message.answer(f'{answer_msg}')
        pass
    finally:
        pass

# Обработчик любых сообщений
# Обработка простых команд
@dp.message()
async def catchMessages(message: types.Message) -> None:
    try:
        chat_id = None
        msg = None
        photo_file_id = None
        
        chat_id = message.chat.id
        
        # С какой-то вероятностью может ответить бредогенератором на сообщение
        # Установка на генерацию сообщения в конфиге
        if await doWithProbability(random.randint(int(config['BOT']['BredoGenerationProbabilityMin']), int(config['BOT']['BredoGenerationProbabilityMax']))):
            msgs = await dbc.getAllMessages(chat_id)
            msgs_text = '\n'.join(msgs)
            
            answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoMessageMinWordSize']), int(config['BOT']['BredoMessageMaxWordSize'])))
            
            if answer_msg != None:
                await message.answer(f'{answer_msg}')
        
        if message.text != None:
            msg = message.text
        elif message.caption != None:
            msg = message.caption
        
        if message.photo != None:
            photo_file_id = message.photo[-1].file_id
        
        if chat_id != None and msg != None:
            msg = await removeLinkFromText(msg)
            await dbc.insertMessage(chat_id, msg)
        if chat_id != None and photo_file_id != None:
            await dbc.insertPhoto(chat_id, photo_file_id)
    except Exception as e:
        print(e)
        pass
    finally:
        pass

async def main() -> None:
    await dbc.createTable()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())