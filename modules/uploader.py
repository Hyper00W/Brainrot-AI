import os
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
TOKEN_FILE = 'youtube_token.json'
CREDS_FILE = 'client_secrets.json'

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(CREDS_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())

    return build('youtube', 'v3', credentials=creds)

def upload_video(
    video_path: str,
    title: str,
    description: str,
    hashtags: list,
    privacy: str = 'public'
) -> dict:
    if not os.path.exists(video_path):
        return {'success': False, 'error': f'File not found: {video_path}'}

    if not os.path.exists(CREDS_FILE):
        return {'success': False, 'error': f'Missing {CREDS_FILE}. Download from Google Cloud Console.'}

    tags = [h.lstrip('#') for h in hashtags]
    desc = description + '\n\n' + ' '.join(hashtags)

    body = {
        'snippet': {
            'title': title[:100],
            'description': desc[:5000],
            'tags': tags[:500],
            'categoryId': '22',  # People & Blogs
        },
        'status': {
            'privacyStatus': privacy,
            'selfDeclaredMadeForKids': False,
        }
    }

    try:
        youtube = get_authenticated_service()
        media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True, chunksize=1024*1024*5)
        request = youtube.videos().insert(part=','.join(body.keys()), body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()

        video_id = response.get('id')
        return {
            'success': True,
            'video_id': video_id,
            'url': f'https://youtube.com/shorts/{video_id}'
        }
    except HttpError as e:
        return {'success': False, 'error': f'YouTube API error: {e}'}
    except Exception as e:
        return {'success': False, 'error': str(e)}
