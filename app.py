import os
import threading
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'brainrot-secret-2024')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///brainrot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    script = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')
    youtube_id = db.Column(db.String(50))
    filename = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    render_log = db.Column(db.Text)

class QueueItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'))
    status = db.Column(db.String(50), default='queued')
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/sync', methods=['POST'])
def sync_videos():
    """Scan generated/video for files and add to DB if missing."""
    results = []
    folder = 'generated/video'
    if not os.path.exists(folder): return jsonify([])
    
    files = [f for f in os.listdir(folder) if f.startswith('short_') and f.endswith('.mp4') and not f.endswith('_gameplay.mp4')]
    
    for f in files:
        # Check if already in DB
        existing = Video.query.filter_by(filename=f).first()
        if not existing:
            v = Video(title=f"Discovered {f}", status='pending', filename=f)
            db.session.add(v)
            results.append(f)
    
    db.session.commit()
    return jsonify({'synced': results})

@app.route('/api/generate-script', methods=['POST'])
def generate_script():
    from modules.script_generator import generate_script
    data = request.json
    topic = data.get('topic', '')
    result = generate_script(topic)
    return jsonify(result)

@app.route('/api/generate-voice', methods=['POST'])
def generate_voice():
    import asyncio
    from modules.voice_generator import generate_voice
    data = request.json
    text = data.get('text', '')
    filename = data.get('filename', 'output')
    result = asyncio.run(generate_voice(text, filename))
    return jsonify(result)

@app.route('/api/videos', methods=['GET'])
def get_videos():
    videos = Video.query.order_by(Video.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': v.id,
        'title': v.title,
        'status': v.status,
        'youtube_id': v.youtube_id,
        'created_at': v.created_at.isoformat(),
        'filename': v.filename
    } for v in videos])

@app.route('/api/queue', methods=['GET'])
def get_queue():
    items = QueueItem.query.filter_by(status='queued').all()
    return jsonify([{'id': i.id, 'video_id': i.video_id, 'status': i.status} for i in items])

@app.route('/api/logs', methods=['GET'])
def get_logs():
    videos = Video.query.filter(Video.render_log != None).order_by(Video.created_at.desc()).limit(10).all()
    return jsonify([{'title': v.title, 'log': v.render_log, 'status': v.status} for v in videos])

@app.route('/api/render', methods=['POST'])
def render_video():
    data = request.json
    title      = data.get('title', 'Untitled')
    audio_path = data.get('audio_path', '')
    script     = data.get('script', '')
    output_name = f"short_{int(datetime.utcnow().timestamp())}"

    video = Video(title=title, script=script, status='rendering', render_log='', filename=f"{output_name}.mp4")
    db.session.add(video)
    db.session.commit()
    vid_id = video.id

    def pipeline():
        log_lines = []
        def log(msg): log_lines.append(msg)

        with app.app_context():
            v = db.session.get(Video, vid_id)
            try:
                from modules.caption_generator import transcribe
                from modules.gameplay import get_random_clip, crop_vertical
                from modules.renderer import render_video as render
                import mutagen.mp3

                log('> Transcribing audio with Whisper...')
                cap = transcribe(audio_path)
                if not cap['success']: raise Exception(cap['error'])
                log(f'> Captions: {cap["count"]} words')

                try:
                    from mutagen.mp3 import MP3
                    dur = MP3(audio_path).info.length
                except Exception:
                    dur = 60.0

                log('> Selecting gameplay clip...')
                clip = get_random_clip(dur)
                if not clip['success']: raise Exception(clip['error'])

                cropped_path = f'generated/video/{output_name}_gameplay.mp4'
                log(f'> Cropping clip: {clip["filename"]}')
                crop = crop_vertical(clip['path'], cropped_path, 0, dur)
                if not crop['success']: raise Exception(crop['error'])

                music_path = None
                music_dir = os.getenv('MUSIC_FOLDER', 'assets/music')
                music_files = [f for f in os.listdir(music_dir) if f.endswith(('.mp3','.wav'))] if os.path.exists(music_dir) else []
                if music_files:
                    import random
                    music_path = os.path.join(music_dir, random.choice(music_files))

                log('> Rendering final video...')
                result = render(cropped_path, audio_path, cap['path'], output_name, music_path)
                if not result['success']: raise Exception(result['error'])

                log(f'> Done! {result["size_mb"]}MB -> {result["path"]}')
                v.status = 'pending'
                v.render_log = '\n'.join(log_lines)
            except Exception as e:
                log(f'ERROR: {e}')
                v.status = 'error'
                v.render_log = '\n'.join(log_lines)
            finally:
                db.session.commit()

    threading.Thread(target=pipeline, daemon=True).start()
    return jsonify({'success': True, 'video_id': vid_id, 'message': 'Rendering started in background'})

@app.route('/api/upload/<int:video_id>', methods=['POST'])
def upload_video(video_id):
    from modules.uploader import upload_video as yt_upload
    v = db.session.get(Video, video_id)
    if not v: return jsonify({'success': False, 'error': 'Video not found'})

    data    = request.json or {}
    hashtags = data.get('hashtags', [])
    
    path = os.path.join('generated/video', v.filename)
    if not os.path.exists(path):
        return jsonify({'success': False, 'error': f'File not found: {v.filename}'})

    result = yt_upload(
        video_path  = path,
        title       = v.title,
        description = v.script or '',
        hashtags    = hashtags
    )
    if result['success']:
        v.youtube_id = result['video_id']
        v.status = 'uploaded'
        db.session.commit()
    return jsonify(result)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        os.makedirs('generated/audio', exist_ok=True)
        os.makedirs('generated/video', exist_ok=True)
        os.makedirs('generated/captions', exist_ok=True)
        os.makedirs('assets/gameplay', exist_ok=True)
        os.makedirs('assets/music', exist_ok=True)
    app.run(debug=True, port=5000)
