import os
import random
import subprocess
import json

GAMEPLAY_DIR = os.getenv('GAMEPLAY_FOLDER', 'assets/gameplay')
GENERATED_DIR = 'generated/video'

# Local FFmpeg path
FFMPEG  = os.path.abspath('ffmpeg.exe') if os.path.exists('ffmpeg.exe') else 'ffmpeg'
FFPROBE = os.path.abspath('ffprobe.exe') if os.path.exists('ffprobe.exe') else 'ffprobe'

SUPPORTED = ('.mp4', '.mov', '.mkv', '.avi')

def get_random_clip(audio_duration: float) -> dict:
    clips = [f for f in os.listdir(GAMEPLAY_DIR) if f.lower().endswith(SUPPORTED)]
    if not clips:
        return {'success': False, 'error': f'No clips found in {GAMEPLAY_DIR}'}

    clip = random.choice(clips)
    clip_path = os.path.join(GAMEPLAY_DIR, clip)
    return {'success': True, 'path': clip_path, 'filename': clip}

def get_clip_duration(path: str) -> float:
    cmd = [
        FFPROBE, '-v', 'quiet', '-print_format', 'json',
        '-show_streams', path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        data = json.loads(result.stdout)
        for stream in data.get('streams', []):
            if stream.get('codec_type') == 'video':
                return float(stream.get('duration', 0))
    except Exception:
        pass
    return 0.0

def crop_vertical(input_path: str, output_path: str, start_time: float, duration: float) -> dict:
    """Crop a clip to 9:16 (1080x1920) and trim to duration."""
    os.makedirs(GENERATED_DIR, exist_ok=True)

    clip_dur = get_clip_duration(input_path)
    max_start = max(0, clip_dur - duration - 1)
    ss = random.uniform(0, max_start) if max_start > 0 else 0

    # Crop: scale to fill 1080x1920, then crop center
    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920"
    )

    cmd = [
        FFMPEG, '-y',
        '-ss', str(ss),
        '-i', input_path,
        '-t', str(duration),
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'fast',
        '-crf', '23',
        '-an',
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            return {'success': False, 'error': result.stderr[-500:]}
        return {'success': True, 'path': output_path}
    except Exception as e:
        return {'success': False, 'error': str(e)}
