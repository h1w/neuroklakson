from gtts import gTTS
from io import BytesIO

from utils import normalizeStringForDemotivator

async def textVoiceover(text, slow=False):
    voice_msg = await normalizeStringForDemotivator(text)
            
    tts = gTTS(voice_msg, lang='ru', slow=slow)
    fp = BytesIO()
    tts.write_to_fp(fp)
    audio_bytes = fp.getvalue()
    
    return audio_bytes