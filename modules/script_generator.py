import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=api_key)

def _get_model():
    try:
        available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        name = available[0] if available else 'gemini-1.5-flash'
        return genai.GenerativeModel(name.replace('models/', ''))
    except:
        return genai.GenerativeModel('gemini-1.5-flash')

model = _get_model()

SCRIPT_PROMPT = """You are a viral YouTube Shorts script writer specializing in brainrot content.
Generate a highly engaging short-form video script for the topic: "{topic}"

Return ONLY valid JSON in this exact format:
{{
  "hook": "attention-grabbing opening line (max 15 words)",
  "script": "full spoken script (60-90 seconds when read aloud, punchy sentences)",
  "title": "YouTube video title (max 60 chars, clickbait but accurate)",
  "hashtags": ["#tag1", "#tag2", "#tag3", "#tag4", "#tag5"],
  "duration_estimate": "estimated seconds when spoken"
}}

Rules:
- Hook must be shocking or controversial
- Use Gen-Z/internet slang naturally
- Script must be fast-paced with short punchy sentences
- Optimize for viewer retention in first 3 seconds
- No markdown, only raw JSON
"""

def generate_script(topic: str) -> dict:
    try:
        response = model.generate_content(SCRIPT_PROMPT.format(topic=topic))
        text = response.text.strip()
        
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        
        import json
        result = json.loads(text.strip())
        result['success'] = True
        return result
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'hook': '',
            'script': '',
            'title': '',
            'hashtags': [],
            'duration_estimate': '0'
        }
