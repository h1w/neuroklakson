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
from utils import normalizeStringForDemotivator, smartImageResize, isTextContainsLink, removeLinkFromText, isTextIsLink
import dbconnector as dbc
from markchain import makeShortSentence
from parse2ch import parseTredToPostTextList

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
        
        answer_msg = await makeShortSentence(msgs_text, 150)
        
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

@dp.message(Command('generatemessage', 'genmsg', 'gm'))
async def commandGenerateMessageHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_msg = await makeShortSentence(msgs_text)
        
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


# Прочитать тред на дваче и добавить это в базу
# Спарсить все сообщения треда и добавить в базу сообщений текст со всех постов треда
@dp.message(Command('readtread2ch', 'rt2ch'))
async def commandReadTredFrom2chHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        command_args = message.text.split(' ')[1:]
    except:
        pass
    finally:
        args_string = ' '.join(command_args)
        if await isTextIsLink(args_string):        
            if '/res/' not in args_string:
                await message.answer("пошел нахуй\nнеправильно пишешь ссылку блять")
            else:
                texts_list = await parseTredToPostTextList(args_string)
                if texts_list is not None:
                    await dbc.insertMessages(chat_id, texts_list)
                
                    await message.answer(f"Успешно добавлено {len(texts_list)} постов")
                else:
                    await message.answer("пошел нахуй\nошибку бьёт падаль")
        else:
            await message.answer("пошел нахуй\nэто не ссылка на тред двача")

# Обработчик любых сообщений
# Обработка простых команд
@dp.message()
async def catchMessages(message: types.Message) -> None:
    try:
        chat_id = None
        msg = None
        photo_file_id = None
        
        chat_id = message.chat.id
        
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
    except:
        pass
    finally:
        pass

async def main() -> None:
    await dbc.createTable()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())