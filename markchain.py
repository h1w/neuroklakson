import markovify
import random
import re

async def makeShortSentence(text, text_len=200):
    text = await textCleaner(text)
    text_model = markovify.Text(text, state_size=2)
    
    generates = []
    for i in range(30):
        generates.append(text_model.make_short_sentence(text_len))
    generates = list(set(generates))
    generates = [x for x in generates if x is not None]
    
    return random.choice(generates)

async def textCleaner(text):
  text = re.sub(r'--', ' ', text)
  text = re.sub('[\[].*?[\]]', '', text)
  text = re.sub(r'(\b|\s+\-?|^\-?)(\d+|\d*\.\d+)\b','', text)
  text = ' '.join(text.split())
  return text