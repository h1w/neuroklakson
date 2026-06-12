import asyncio
import configparser
import logging
import random
import sys
from io import BytesIO
from pathlib import Path

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart, Filter

import dbconnector as dbc
from config import load_legacy_config
from demotivate import generateDemotivator, generateQuote
from markchain import makeShortSentence
from utils import (
    doWithProbability,
    normalizeStringForDemotivator,
    removeLinkFromText,
    splitStringIntoLines,
)
from voiceover import textVoiceover

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

config = configparser.ConfigParser()
if Path('credentials.cfg').exists():
    config.read('credentials.cfg')
if not config.has_option('BOT', 'Token'):
    config = load_legacy_config()

bot = Bot(config['BOT']['Token'])
dp = Dispatcher()

class IsGroupFilter(Filter):
    def __init__(self) -> None:
        pass
    
    async def __call__(self, message: types.Message) -> bool:
        if message.chat.type == 'group' or message.chat.type == 'supergroup':
            return True
        else:
            return False

# Приветствие бота
@dp.message(CommandStart())
async def commandStartHandler(message: types.Message) -> None:
    await message.answer(f'Пошел нахуй {message.from_user.full_name}!')

# Помощь в командах бота
@dp.message(IsGroupFilter(), Command('help', 'h'))
async def commandHelpHandler(message: types.Message) -> None:
    help_msg = """Команды бота:
/start - пошел нахуй
/help, /h - помощь по командам
/createdemotivator, /crdem, /cd <first_line> | <second_line or NONE> - создание демотиватора вручную: отослать картинку с текстом или ответить на картинку с текстом демотиватора
/demotivatorgeneration, /demgen, /d - демотиватор на основе картинок и сообщений чата
/generatemessage, /genmsg, /gm - сгенерировать бредосообщение
/generatebugurt, /genbug, /b - Сгенерировать бугурт
/createquote, /cq, /q - Создать цитату, необходимо ответить на сообщение человека, в котором содержится текст
/stats, /s - Статистика чата
/voiceover, /v - Озвучка сообщения
"""
    await message.answer(help_msg)

# Генератор демотиваторов вручную через команду
# Можно как отправить команду с текстом и картинкой,
# Так и ответив на картинку написать команду с текстом
# И получить в результате демотиватор
@dp.message(IsGroupFilter(), Command('createdemotivator', 'crdem', 'cd'))
async def commandCreateDemotivatorManuallyHandler(message: types.Message) -> None:
    try:
        if message.text is not None:
            command_args = message.text.split(' ')[1:]
        elif message.caption is not None:
            command_args = message.caption.split(' ')[1:]
        else:
            await message.answer("Еблан, мне не из чего делать демотиватор, пошел нахуй!")
            return
        
        args_string = ' '.join(command_args)
        first_line, second_line = args_string, ''
        args_string = args_string.split('|')
        if len(args_string) > 1:
            first_line, second_line = args_string[0], args_string[1]
        
        if message.reply_to_message is not None:
            if message.reply_to_message.photo is not None:
                photo = message.reply_to_message.photo[-1]
            else:
                await message.answer("Еблан, мне не из чего делать демотиватор, пошел нахуй!")
                return
        else:
            if message.photo is not None:
                photo = message.photo[-1]
            else:
                await message.answer("Еблан, мне не из чего делать демотиватор, пошел нахуй!")
                return
        
        first_line = await normalizeStringForDemotivator(first_line)
        second_line = await normalizeStringForDemotivator(second_line)
        
        photo_bytes = BytesIO()
        await bot.download(photo.file_id, photo_bytes)
        
        demotivator_image = await generateDemotivator(photo_bytes, first_line, second_line, str(config['BOT']['BredoDemotivatorWatermark']), str(config['BOT']['BredoDemotivatorTextFont']))
        
        img_byte_array = BytesIO()
        demotivator_image.save(img_byte_array, format="PNG")
        img_byte_array.seek(0)
        
        await message.answer_photo(types.BufferedInputFile(img_byte_array.getvalue(), "aboba.png"))
    except Exception as e:
        logging.exception(e)
    finally:
        pass

# Автоматическая генерация Демотиваторов
# Рандомная картинка из беседы + рандомная сгенерированная фраза из беседы
@dp.message(IsGroupFilter(), Command('demotivatorgeneration', 'demgen', 'd'))
async def commandDemotivatorGeneratorHandler(message: types.Message) -> None:
    try:
        # Взять рандомную картинку
        # Сделать рандомную фразу
        # Сделать демотиватор
        # Отправить в чат
        chat_id = message.chat.id
        
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_first_line = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoDemotivatorMinWordSize']), int(config['BOT']['BredoDemotivatorMaxWordSize'])))
        answer_second_line = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoDemotivatorSecondLineMinWordSize']), int(config['BOT']['BredoDemotivatorSecondLineMaxWordSize'])))
        if answer_first_line is None and answer_second_line is None:
            answer_msg = "Я ещё очень тупой, нужно немного подождать"
            await message.answer(f'{answer_msg}')
        else:
            photo_file_id = await dbc.getRandomPhoto(chat_id)
            
            photo_bytes = BytesIO()
            await bot.download(photo_file_id, photo_bytes)
            
            demotivator_image = await generateDemotivator(photo_bytes, answer_first_line, answer_second_line, str(config['BOT']['BredoDemotivatorWatermark']), str(config['BOT']['BredoDemotivatorTextFont']))
            
            img_byte_array = BytesIO()
            demotivator_image.save(img_byte_array, format="PNG")
            img_byte_array.seek(0)
            
            await message.answer_photo(types.BufferedInputFile(img_byte_array.getvalue(), "aboba.png"))
    except Exception as e:
        logging.exception(e)
        pass
    finally:
        pass

# Автоматическая генерация Демотиваторов
# Рандомная картинка из беседы + рандомная сгенерированная фраза из беседы
@dp.message(IsGroupFilter(), Command('createquote', 'cq', 'q'))
async def commandCreateQuoteHandler(message: types.Message) -> None:
    try:
                
        if message.reply_to_message is not None:
            # author_name = f"{message.reply_to_message.from_user.first_name} {message.reply_to_message.from_user.last_name} | {message.reply_to_message.from_user.username}"
            author_name = message.reply_to_message.from_user.username
            author_id = message.reply_to_message.from_user.id
            author_profile_pictures_obj = await bot.get_user_profile_photos(author_id)
            
            author_profile_pic_bytes = BytesIO()
            await bot.download(author_profile_pictures_obj.photos[0][-1].file_id, author_profile_pic_bytes)
            
            msg_text = ''
            if message.reply_to_message.text is not None:
                msg_text = message.reply_to_message.text
            elif message.reply_to_message.caption is not None:
                msg_text = message.reply_to_message.caption
            else:
                await message.answer("Придурок, на что мне делать цитату? Образумься")
                return

            quote_image = await generateQuote(author_profile_pic_bytes, author_name, await normalizeStringForDemotivator(msg_text), str(config['BOT']['BredoQuoteHeadlineText']), config['BOT']['BredoQuoteHeadlineTextFont'], config['BOT']['BredoQuoteAuthorNameTextFont'], config['BOT']['BredoQuoteQuoteTextFont'])
            
            img_byte_array = BytesIO()
            quote_image.save(img_byte_array, format="PNG")
            img_byte_array.seek(0)

            await message.answer_photo(types.BufferedInputFile(img_byte_array.getvalue(), "aboba.png"))
        else:
            await message.answer("Придурок, на что мне делать цитату? Образумься")
            return

    except Exception as e:
        logging.exception(e)
    finally:
        pass

# генерация сообщений
# Команда для генерации сообщений
@dp.message(IsGroupFilter(), Command('generatemessage', 'genmsg', 'gm'))
async def commandGenerateMessageHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoMessageMinWordSize']), int(config['BOT']['BredoMessageMaxWordSize'])))
        
        if answer_msg is None:
            answer_msg = "Я ещё очень тупой, нужно немного подождать"
            await message.answer(f'{answer_msg}')
        else:
            await message.answer(f'{answer_msg}')
    except Exception as e:
        logging.exception(e)
        answer_msg = "Еще слишком рано\nПодожди немного"
        await message.answer(f'{answer_msg}')
        pass
    finally:
        pass

# Генератор бугуртов
# Сгенерировать бугурт
@dp.message(IsGroupFilter(), Command('generatebugurt', 'genbug', 'b'))
async def commandGenerateBugurtHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        msgs = await dbc.getAllMessages(chat_id)
        msgs_text = '\n'.join(msgs)
        
        answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoBugurtMessageMinWordSize']), int(config['BOT']['BredoBugurtMessageMaxWordSize'])))
        if answer_msg is None:
            answer_msg = "Я ещё очень тупой, нужно немного подождать"
            await message.answer(f'{answer_msg}')
        else:
            answer_msg = await normalizeStringForDemotivator(answer_msg)
            bugurt_text_lines = await splitStringIntoLines(answer_msg, int(config['BOT']['BredoBugurtMessageMinWordsPerLine']), int(config['BOT']['BredoBugurtMessageMaxWordsPerLine']), int(config['BOT']['BredoBugurtMessageMinLines']), int(config['BOT']['BredoBugurtMessageMaxLines']))
            bugurt_text = '\n@\n'.join(bugurt_text_lines)
            await message.answer(f'{bugurt_text}')
        
    except Exception as e:
        logging.exception(e)
        answer_msg = "Еще слишком рано\nПодожди немного"
        await message.answer(f'{answer_msg}')
        pass
    finally:
        pass

# Статистика чата
@dp.message(IsGroupFilter(), Command('stats', 's'))
async def commandChatStatsHandler(message: types.Message) -> None:
    try:
        chat_id = message.chat.id
        messages_count = await dbc.getMessagesCount(chat_id)
        photos_count = await dbc.getPhotosCount(chat_id)
        
        ans_msg = f"ID чата: *{chat_id}*\nСохранено: *{messages_count}* сообщений, *{photos_count}* изображений"
        
        await message.answer(ans_msg, parse_mode='Markdown')
    except Exception as e:
        logging.exception(e)
    finally:
        pass

# Озвучка сообщений
@dp.message(IsGroupFilter(), Command('voiceover', 'v'))
async def commandMessageVoiceoverHandler(message: types.Message) -> None:
    try:
        msg = None
        
        if message.reply_to_message is not None:
            if message.reply_to_message.text is not None:
                msg = message.reply_to_message.text
            elif message.reply_to_message.caption is not None:
                msg = message.reply_to_message.caption
        else:
            if message.text is not None:
                msg = ' '.join(message.text.split(' ')[1:])
                
                if len(msg) == 0:
                    msg = None
        
        if msg is not None:
            await message.answer_voice(types.BufferedInputFile(await textVoiceover(msg), "aboba"))
        else:
            await message.answer("Что мне озвучивать ебалай? Пошел нахуй конченый пидарас")
            return
    except Exception as e:
        logging.exception(e)
    finally:
        pass

# Обработчик любых сообщений
# Обработка простых команд
@dp.message(IsGroupFilter())
async def catchMessages(message: types.Message) -> None:
    try:
        chat_id = None
        msg = None
        photo_file_id = None
        
        chat_id = message.chat.id
        
        # С какой-то вероятностью может ответить бредогенератором на сообщение
        # Установка на генерацию сообщения в конфиге
        if await doWithProbability(int(config['BOT']['BredoGenerationProbability'])):
            msgs = await dbc.getAllMessages(chat_id)
            msgs_text = '\n'.join(msgs)
            
            answer_msg = await makeShortSentence(msgs_text, random.randint(int(config['BOT']['BredoMessageMinWordSize']), int(config['BOT']['BredoMessageMaxWordSize'])))
            
            if answer_msg is not None:
                await message.answer(f'{answer_msg}')
        
        msg = None
        if message.text is not None:
            msg = message.text
        elif message.caption is not None:
            msg = message.caption
        
        # С какой-то вероятностью может озвучить сообщение пользователя
        if msg is not None and await doWithProbability(int(config['BOT']['BredoMessageVoiceoverProbability'])):
            await message.answer_voice(types.BufferedInputFile(await textVoiceover(msg), "aboba"))
        
        if message.photo is not None:
            photo_file_id = message.photo[-1].file_id
        
        if chat_id is not None and msg is not None:
            msg = await removeLinkFromText(msg)
            await dbc.insertMessage(chat_id, msg)
        if chat_id is not None and photo_file_id is not None:
            await dbc.insertPhoto(chat_id, photo_file_id)
    except Exception as e:
        logging.exception(e)
        pass
    finally:
        pass

async def main() -> None:
    await dbc.createTable()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
