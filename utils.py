from PIL import Image
import re

# Нормализовать текст для демотиватора
# Чтобы она не вылезала за границы картинки
async def normalizeStringForDemotivator(text, every=30, max_str_size=60):
    text = text[:max_str_size]
    lines = []
    for i in range(0, len(text), every):
        lines.append(text[i:i+every])
    return '\n'.join(lines)

# Умный размер картинки, чтобы был нормальный размер и телеграм схавал по объёму
async def smartImageResize(image, min_size=600, max_size=1200):
    # Получаем ширину и высоту изображения
    width, height = image.size

    # Вычисляем соотношение сторон
    aspect_ratio = width / height

    # Подгоняем изображение под минимальный размер
    if width < min_size or height < min_size:
        if width < height:
            new_width = min_size
            new_height = int(min_size / aspect_ratio)
        else:
            new_height = min_size
            new_width = int(min_size * aspect_ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)

    # Подгоняем изображение под максимальный размер
    if width > max_size or height > max_size:
        if width > height:
            new_width = max_size
            new_height = int(max_size / aspect_ratio)
        else:
            new_height = max_size
            new_width = int(max_size * aspect_ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)
    
    return image

# Проверить, есть ли в строке ссылка
async def isTextContainsLink(text):
    # Регулярное выражение для поиска ссылок
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    
    return re.search(pattern, text) is not None

# Удалить ссылку из строки
async def removeLinkFromText(text):
    # Регулярное выражение для поиска ссылок
    pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'

    return re.sub(pattern, '', text)