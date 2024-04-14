from PIL import ImageFont, Image
from demotivator import Demotivator, demotivate
from demotivator.indent import ImageIndentation

# Исходные генератор демотиваторов через библиотеку:
# https://github.com/SolovovChann/demotivator/
async def generateDemotivator(image, text) -> Image:
    return demotivate(image, 'font.ttf', text)