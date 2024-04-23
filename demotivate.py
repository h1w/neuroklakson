from PIL import Image, ImageDraw, ImageFont, ImageOps
import textwrap

from utils import normalizeStringForDemotivator

# Рисуем демотиватор:
async def generateDemotivator(image, top_text, bottom_text) -> Image:
    watermark='@нейроклаксон'
    font_color='white'
    fill_color='black'
    font_name='fonts/font.ttf'
    top_size=80
    bottom_size=50
    arrange=False
    
    top_text = await normalizeStringForDemotivator(top_text)
    bottom_text = await normalizeStringForDemotivator(bottom_text)
    
    """
        Создаем шаблон для демотиватора
        Вставляем фотографию в рамку
        """

    if arrange:
        user_img = Image.open(image).convert("RGBA")
        (width, height) = user_img.size
        img = Image.new('RGB', (width + 250, height + 260), color=fill_color)
        img_border = Image.new('RGB', (width + 10, height + 10), color='#000000')
        border = ImageOps.expand(img_border, border=2, fill='#ffffff')
        img.paste(border, (111, 96))
        img.paste(user_img, (118, 103))
        drawer = ImageDraw.Draw(img)
    else:
        img = Image.new('RGB', (1280, 1024), color=fill_color)
        img_border = Image.new('RGB', (1060, 720), color='#000000')
        border = ImageOps.expand(img_border, border=2, fill='#ffffff')
        user_img = Image.open(image)
        user_img = user_img.convert("RGBA").resize((1050, 710))
        (width, height) = user_img.size
        img.paste(border, (111, 96))
        img.paste(user_img, (118, 103))
        drawer = ImageDraw.Draw(img)

    """Подбираем оптимальный размер шрифта
    
    Добавляем текст в шаблон для демотиватора

    """
    font_1 = ImageFont.truetype(font=font_name, size=top_size, encoding='UTF-8')
    text_width = font_1.getsize(top_text)[0]

    while text_width >= (width + 250) - 20:
        font_1 = ImageFont.truetype(font=font_name, size=top_size, encoding='UTF-8')
        text_width = font_1.getsize(top_text)[0]
        top_size -= 1

    font_2 = ImageFont.truetype(font=font_name, size=bottom_size, encoding='UTF-8')
    text_width = font_2.getsize(bottom_text)[0]

    while text_width >= (width + 250) - 20:
        font_2 = ImageFont.truetype(font=font_name, size=bottom_size, encoding='UTF-8')
        text_width = font_2.getsize(bottom_text)[0]
        bottom_size -= 1

    size_1 = drawer.textsize(top_text, font=font_1)
    size_2 = drawer.textsize(bottom_text, font=font_2)

    if arrange:
        drawer.text((((width + 250) - size_1[0]) / 2, ((height + 190) - size_1[1])),
                    top_text, fill=font_color,
                    font=font_1)
        drawer.text((((width + 250) - size_2[0]) / 2, ((height + 235) - size_2[1])),
                    bottom_text, fill=font_color,
                    font=font_2)
    else:
        drawer.text(((1280 - size_1[0]) / 2, 840), top_text, fill=font_color, font=font_1)
        drawer.text(((1280 - size_2[0]) / 2, 930), bottom_text, fill=font_color, font=font_2)

    if watermark is not None:
        (width, height) = img.size
        idraw = ImageDraw.Draw(img)

        idraw.line((1000 - len(watermark) * 5, 817, 1008 + len(watermark) * 5, 817), fill=0, width=4)

        font_2 = ImageFont.truetype(font=font_name, size=20, encoding='UTF-8')
        size_2 = idraw.textsize(watermark.lower(), font=font_2)
        idraw.text((((width + 729) - size_2[0]) / 2, ((height - 192) - size_2[1])),
                    watermark.lower(), font=font_2)

    return img

# Рисуем цитату:
async def generateQuote(author_profile_pic, author_name, quote_text, headline_text="Цитаты клаксонутых", headline_text_font='fonts/font.ttf', author_name_font='fonts/font.ttf', quote_text_font='fonts/font.ttf') -> Image:
    headline_text_size=50
    author_name_size=40
    quote_text_size=35
    
    text = ''
    lines = textwrap.wrap(quote_text, width=28)

    for i in lines:
        text = text + i + '\n'

    if len(text.splitlines()) > 5:
        lines = text.splitlines()[0:5]
        text = ''
        for i in lines:
            text = text + i + '\n'

    user_img = Image.new('RGBA', (1000, 550), color='#000000')

    drawer = ImageDraw.Draw(user_img)
    font_1 = ImageFont.truetype(font=quote_text_font, size=quote_text_size, encoding='UTF-8')
    font_2 = ImageFont.truetype(font=headline_text_font, size=headline_text_size, encoding='UTF-8')
    font_3 = ImageFont.truetype(font=author_name_font, size=author_name_size, encoding='UTF-8')

    size_headline = drawer.textsize(headline_text, font=font_2)

    drawer.text((425, 120), f"{text[:-1]}", fill='white', font=font_1)
    drawer.text((425, 410), '© ' + author_name, fill='white', font=font_3)
    drawer.text(((1000 - size_headline[0]) / 2, 25), headline_text, fill='white', font=font_2)

    """
    Сглаживаем в форме круга фотографию автора цитаты
    """

    # user_photo = Image.open(author_profile_pic).resize((150, 150)).convert("RGBA")
    # width, height = user_photo.size
    # user_photo.crop(((width - height) / 2, 0, (width + height) / 2, height))
    # user_photo.resize((150, 150), Image.ANTIALIAS)
    # mask = Image.new('L', (150 * 2, 150 * 2), 0)
    # ImageDraw.Draw(mask).ellipse((0, 0) + mask.size, fill=255)
    # user_photo.putalpha(mask.resize((150, 150), Image.ANTIALIAS))
    # user_img.paste(user_photo, (50, 370), mask=user_photo)
    
    true_width, true_height = 350, 350
    user_photo = Image.open(author_profile_pic).resize((true_width, true_height)).convert("RGBA")
    width, height = user_photo.size
    user_photo.crop(((width-height) / 2, 0, (width + height) / 2, height))
    user_photo.resize((true_width, true_height), Image.ANTIALIAS)
    mask = Image.new('L', (true_width * 2, true_height * 2), 0)
    ImageDraw.Draw(mask).rectangle((0, 0) + mask.size, fill=255)
    user_photo.putalpha(mask.resize((true_width, true_height), Image.ANTIALIAS))
    user_img.paste(user_photo, (50, 120), mask=user_photo)

    return user_img