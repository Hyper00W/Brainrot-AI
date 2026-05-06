# BRAINROT.AI — YouTube Shorts Automation
# =========================================
# Quick-start guide

## Setup

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate   # Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 4. Run the app
python app.py
```

Open http://localhost:5000

---

## Project Structure

```
Brainrot/
├── app.py                  # Flask app + API routes
├── requirements.txt
├── .env                    # Your API keys (gitignored)
├── modules/
│   ├── script_generator.py # Gemini API scripts
│   ├── voice_generator.py  # EdgeTTS voice synthesis
│   ├── caption_generator.py# Whisper word-level captions
│   ├── gameplay.py         # Clip selection + FFmpeg crop
│   ├── renderer.py         # Final video assembly
│   └── uploader.py         # YouTube Data API v3
├── templates/
│   └── index.html          # Cyberpunk dashboard
├── static/
│   ├── css/main.css
│   └── js/dashboard.js
├── assets/
│   ├── gameplay/           # Drop .mp4 clips here
│   ├── music/              # Drop .mp3 tracks here
│   └── fonts/              # Optional: Montserrat-Bold.ttf
└── generated/
    ├── audio/              # EdgeTTS output
    ├── captions/           # Whisper JSON
    └── video/              # Final MP4s
```

---

## YouTube Upload Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create project → Enable **YouTube Data API v3**
3. OAuth 2.0 credentials → Desktop App
4. Download as `client_secrets.json` → place in project root
5. First upload will open browser for auth

---

## Workflow

1. **Generate Video** tab → enter topic → click Generate Script
2. Click Generate Voice to synthesize audio
3. Add gameplay clips to `assets/gameplay/`
4. Click Render (triggers background pipeline)
5. Upload Queue → upload to YouTube

---

## Notes

- Whisper `base` model used by default (fast, ~1GB RAM)
- FFmpeg must be installed and on PATH
- Background music is mixed at 8% volume automatically
- Captions use FFmpeg drawtext (no MoviePy dependency for rendering)
