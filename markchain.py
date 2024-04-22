import markovify
import random
import re

async def create_chain(text, chain_length=2):
    chain = {}
    words = text.split()
    
    for i in range(len(words) - chain_length):
        key = tuple(words[i:i + chain_length])
        value = words[i + chain_length]
        
        if key in chain:
            chain[key].append(value)
        else:
            chain[key] = [value]
    
    return chain

async def generate_text(chain, chain_length=2, max_words=100):
    seed = random.choice(list(chain.keys()))
    text = list(seed)
    
    while len(text) < max_words:
        key = tuple(text[-chain_length:])
        if key in chain:
            next_word = random.choice(chain[key])
            text.append(next_word)
        else:
            break
    
    return ' '.join(text)

async def makeShortSentence(text, max_words=100):
    text = await textCleaner(text)
    
    chain = await create_chain(text)
    generated_text = await generate_text(chain, 2, max_words)
    
    return generated_text

async def textCleaner(text):
  text = re.sub(r'--', ' ', text)
  text = re.sub('[\[].*?[\]]', '', text)
  text = re.sub(r'(\b|\s+\-?|^\-?)(\d+|\d*\.\d+)\b','', text)
  text = ' '.join(text.split())
  return text