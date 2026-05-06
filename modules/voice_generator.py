import edge_tts
import os
import asyncio

VOICE = "en-US-GuyNeural"
OUTPUT_DIR = "generated/audio"

VOICES = {
    "guy": "en-US-GuyNeural",
    "aria": "en-US-AriaNeural",
    "davis": "en-US-DavisNeural",
    "tony": "en-US-TonyNeural",
    "jenny": "en-US-JennyNeural",
}

async def generate_voice(text: str, filename: str, voice_key: str = "guy") -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{filename}.mp3")
    
    voice = VOICES.get(voice_key, VOICE)
    
    try:
        communicate = edge_tts.Communicate(text, voice, rate="+15%", pitch="+0Hz")
        await communicate.save(output_path)
        
        size = os.path.getsize(output_path)
        return {
            'success': True,
            'path': output_path,
            'filename': f"{filename}.mp3",
            'size_bytes': size,
            'voice': voice
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'path': None
        }

async def list_voices() -> list:
    voices = await edge_tts.list_voices()
    en_voices = [v for v in voices if v['Locale'].startswith('en-')]
    return [{'name': v['ShortName'], 'gender': v['Gender']} for v in en_voices]
