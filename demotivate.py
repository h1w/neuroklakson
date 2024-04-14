from PIL import ImageFont, Image
from demotivator import Demotivator, demotivate
from demotivator.indent import ImageIndentation

# Исходные генератор демотиваторов через библиотеку:
# https://github.com/SolovovChann/demotivator/
async def generateDemotivator(image_bytes, text) -> Image:
    image = Image.open(image_bytes)
    return demotivate(image, 'font.ttf', text)