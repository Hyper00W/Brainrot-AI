import os
import subprocess
import json

OUTPUT_DIR      = 'generated/video'
W, H            = 1080, 1920
WORDS_PER_FRAME = 3

# Local FFmpeg path
FFMPEG = os.path.abspath('ffmpeg.exe') if os.path.exists('ffmpeg.exe') else 'ffmpeg'

def create_ass_file(words: list, output_path: str):
    """Create an Advanced Substation Alpha subtitle file with word-level highlighting."""
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Grobold,100,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,8,0,2,10,10,960,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
    ]
    
    events = []
    
    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    # Group words into chunks of 2-3 words
    chunk_size = 2
    for i in range(0, len(words), chunk_size):
        chunk = words[i:i + chunk_size]
        if not chunk: continue
        
        # For each word in the chunk, create a timed event where ONLY that word is yellow
        for highlight_idx in range(len(chunk)):
            t_start = format_time(chunk[highlight_idx]['start'])
            t_end = format_time(chunk[highlight_idx]['end'] if highlight_idx == len(chunk)-1 else chunk[highlight_idx+1]['start'])
            
            text_parts = []
            for j, w in enumerate(chunk):
                if j == highlight_idx:
                    text_parts.append(f"{{\\c&H00FFFF&}}{w['word']}{{\\c&HFFFFFF&}}")
                else:
                    text_parts.append(w['word'])
            
            line = " ".join(text_parts).upper()
            events.append(f"Dialogue: 0,{t_start},{t_end},Default,,0,0,0,,{line}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(header + events))

def render_video(
    gameplay_path: str,
    audio_path: str,
    captions_path: str,
    output_name: str,
    music_path: str = None,
    music_volume: float = 0.08
) -> dict:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{output_name}.mp4")
    ass_path = os.path.join('generated', 'captions', f"{output_name}.ass")
    os.makedirs(os.path.dirname(ass_path), exist_ok=True)

    with open(captions_path) as f:
        words = json.load(f)

    # 1. Create the subtitle file
    create_ass_file(words, ass_path)

    # 2. Build FFmpeg command with the ass filter
    # Note: subtitle path needs escaping for FFmpeg
    escaped_ass = ass_path.replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{escaped_ass}'"

    if music_path and os.path.exists(music_path):
        audio_filter = (
            f"[1:a]volume=1.0[va];"
            f"[2:a]volume={music_volume}[vm];"
            f"[va][vm]amix=inputs=2:duration=first[aout]"
        )
        cmd = [
            FFMPEG, '-y',
            '-i', gameplay_path,
            '-i', audio_path,
            '-i', music_path,
            '-filter_complex', f"{audio_filter};[0:v]{vf}[vout]",
            '-map', '[vout]',
            '-map', '[aout]',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-s', f'1080x1920',
            '-r', '30',
            output_path
        ]
    else:
        cmd = [
            FFMPEG, '-y',
            '-i', gameplay_path,
            '-i', audio_path,
            '-filter_complex', f"[0:v]{vf}[vout]",
            '-map', '[vout]',
            '-map', '1:a',
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '22',
            '-c:a', 'aac', '-b:a', '192k',
            '-pix_fmt', 'yuv420p',
            '-s', f'1080x1920',
            '-r', '30',
            '-shortest',
            output_path
        ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            return {'success': False, 'error': result.stderr[-800:]}
        size = os.path.getsize(output_path)
        return {'success': True, 'path': output_path, 'size_mb': round(size/1024/1024, 2)}
    except Exception as e:
        return {'success': False, 'error': str(e)}
