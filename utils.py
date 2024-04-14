from PIL import Image

# Нормализовать текст для демотиватора
# Чтобы она не вылезала за границы картинки
async def normalizeStringForDemotivator(text, every=30, max_str_size=60):
    text = text[:max_str_size]
    lines = []
    for i in range(0, len(text), every):
        lines.append(text[i:i+every])
    return '\n'.join(lines)

# Умное уменьшение картинки, чтобы телеграм схавал
async def smartImageResize(image, max_width=1000, max_height=1000):
    # Получаем текущие размеры изображения
    width, height = image.size

    # Рассчитываем соотношение сторон изображения
    aspect_ratio = width / height

    # Подбираем новые размеры изображения в зависимости от максимальной ширины и высоты
    if width > max_width or height > max_height:
        if width > height:
            new_width = max_width
            new_height = int(max_width / aspect_ratio)
        else:
            new_height = max_height
            new_width = int(max_height * aspect_ratio)
    else:
        new_width, new_height = width, height

    # Изменяем размер изображения
    resized_image = image.resize((new_width, new_height))
    
    return resized_image