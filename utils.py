from PIL import Image
import re
import random

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

# Проверить, что текст это ссылка
async def isTextIsLink(string):
    url_pattern = re.compile(
        r'^(?:http|ftp)s?://'  # протокол
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # доменное имя
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP адрес
        r'(?::\d+)?'  # порт
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return re.match(url_pattern, string) is not None

async def doWithProbability(probability_percent):
    random_number = random.randint(0, 99)
    
    if random_number <= probability_percent:
        return True
    else:
        return False

async def splitStringIntoLines(text, min_words_per_line=2, max_words_per_line=15, min_lines=2, max_lines=10):
    random_lines = []
    num_lines = random.randint(min_lines, max_lines)

    words = text.split()

    start_idx = 0
    while start_idx < len(words):
        end_idx = min(len(words), start_idx + random.randint(min_words_per_line, max_words_per_line))
        line = ' '.join(words[start_idx:end_idx])
        random_lines.append(line)
        start_idx = end_idx
        
    if len(random_lines) == 1:
        words = random_lines[0].split()
    
        split_index = random.randint(1, len(words) - 1)
        
        first_part = ' '.join(words[:split_index])
        second_part = ' '.join(words[split_index:])
        
        random_lines = [
            first_part,
            second_part
        ]
    
    return random_lines