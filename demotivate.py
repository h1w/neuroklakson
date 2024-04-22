from PIL import ImageFont, Image
from demotivator import Demotivator, demotivate
from demotivator.indent import ImageIndentation

from utils import normalizeStringForDemotivator

# Исходные генератор демотиваторов через библиотеку:
# https://github.com/SolovovChann/demotivator/
async def generateDemotivator(image, text) -> Image:
    text = await normalizeStringForDemotivator(text)
    return demotivate(image, 'font.ttf', text)