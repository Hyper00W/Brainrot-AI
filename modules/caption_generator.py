from faster_whisper import WhisperModel
import os
import json

CAPTIONS_DIR = 'generated/captions'
_model = None

def _get_model(size: str = 'base'):
    global _model
    if _model is None:
        _model = WhisperModel(size, device='cpu', compute_type='int8')
    return _model

def transcribe(audio_path: str, model_size: str = 'base') -> dict:
    """Transcribe audio and return word-level timestamps."""
    os.makedirs(CAPTIONS_DIR, exist_ok=True)

    try:
        model = _get_model(model_size)
        segments, _ = model.transcribe(audio_path, word_timestamps=True, language='en')

        words = []
        for seg in segments:
            for w in seg.words:
                words.append({
                    'word':  w.word.strip(),
                    'start': round(w.start, 3),
                    'end':   round(w.end, 3),
                })

        base = os.path.splitext(os.path.basename(audio_path))[0]
        out_path = os.path.join(CAPTIONS_DIR, f"{base}.json")
        with open(out_path, 'w') as f:
            json.dump(words, f, indent=2)

        return {'success': True, 'words': words, 'path': out_path, 'count': len(words)}
    except Exception as e:
        return {'success': False, 'error': str(e), 'words': []}

def load_captions(json_path: str) -> list:
    with open(json_path) as f:
        return json.load(f)

