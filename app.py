from flask import Flask, request, jsonify, send_file
import requests
import os
import re
import tempfile
import base64
import time

app = Flask(__name__)

# Endpoint du site de téléchargement
SPOTIFY_API_URL = "https://spotisongdownloader.com/api/composer/spotify/ssdw23456ytrfds.php"

# Identifiants Spotify (inchangés)
SPOTIFY_CLIENT_ID = '9efa9943cf4f470f84533bc9fea99392'
SPOTIFY_CLIENT_SECRET = 'd0421a577f0c4b258d5b6b7b05371d88'

spotify_token = None
token_expiry = 0

def get_spotify_token():
    """Récupère un token Spotify API valide"""
    global spotify_token, token_expiry
    current_time = time.time()

    if spotify_token and current_time < token_expiry:
        return spotify_token

    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_base64 = base64.b64encode(auth_string.encode()).decode()

    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    data = {'grant_type': 'client_credentials'}

    try:
        res = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data, timeout=10)
        res.raise_for_status()
        result = res.json()
        spotify_token = result['access_token']
        token_expiry = current_time + result['expires_in'] - 60
        return spotify_token
    except Exception as e:
        print(f"Error getting Spotify token: {e}")
        return None

def extract_track_id(spotify_url):
    match = re.search(r'track/([a-zA-Z0-9]+)', spotify_url)
    return match.group(1) if match else None

def get_track_info(spotify_url):
    """Récupère info track depuis Spotify API"""
    track_id = extract_track_id(spotify_url)
    if not track_id:
        return None

    token = get_spotify_token()
    if not token:
        return None

    headers = {'Authorization': f'Bearer {token}'}
    try:
        res = requests.get(f'https://api.spotify.com/v1/tracks/{track_id}', headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return {
            "song_name": data['name'],
            "artist_name": ', '.join([a['name'] for a in data['artists']]),
            "album_image": data['album']['images'][0]['url'] if data['album']['images'] else None,
            "duration_ms": data['duration_ms']
        }
    except Exception as e:
        print(f"Error getting track info: {e}")
        return None

def get_download_link(spotify_url):
    """Récupère le lien de téléchargement via SpotisongDownloader"""
    track_info = get_track_info(spotify_url)
    if not track_info:
        return None

    session = requests.Session()

    # Étape 1: visiter track.php pour récupérer les cookies valides
    try:
        session.get('https://spotisongdownloader.com/track.php', timeout=10)
    except Exception as e:
        print(f"Error initializing session: {e}")
        return None

    # Étape 2: POST pour récupérer le dlink
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://spotisongdownloader.com",
        "Referer": "https://spotisongdownloader.com/track.php",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest",
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache"
    }

    data = {
        "song_name": track_info["song_name"],
        "artist_name": track_info["artist_name"],
        "url": spotify_url,
        "zip_download": "false",
        "quality": "m4a"
    }

    try:
        res = session.post(SPOTIFY_API_URL, headers=headers, data=data, timeout=30)
        res.raise_for_status()
        result = res.json()
        if result.get("status") == "success":
            return {"download_link": result.get("dlink"), "track_info": track_info}
        else:
            print(f"Downloader returned failure: {result}")
            return None
    except Exception as e:
        print(f"Error fetching download link: {e}")
        return None

@app.route('/api/track', methods=['GET', 'POST'])
def get_track():
    if request.method == 'POST':
        data = request.get_json()
        spotify_url = data.get('url')
        download = data.get('download', False)
    else:
        spotify_url = request.args.get('url')
        download = request.args.get('download', 'false').lower() == 'true'

    if not spotify_url:
        return jsonify({"error": "Spotify URL is required"}), 400

    if not spotify_url.startswith("https://open.spotify.com/track/"):
        return jsonify({"error": "Invalid Spotify track URL"}), 400

    result = get_download_link(spotify_url)
    if not result or not result.get("download_link"):
        return jsonify({"error": "Failed to get download link"}), 500

    download_link = result["download_link"]
    track_info = result["track_info"]

    if download:
        try:
            audio_response = requests.get(download_link, timeout=60)
            audio_response.raise_for_status()

            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
                tmp_file.write(audio_response.content)
                tmp_path = tmp_file.name

            response = send_file(
                tmp_path,
                mimetype='audio/mp4',
                as_attachment=True,
                download_name=f'{track_info["song_name"]}.m4a'
            )

            @response.call_on_close
            def cleanup():
                try:
                    os.unlink(tmp_path)
                except:
                    pass

            return response

        except Exception as e:
            return jsonify({"error": f"Failed to download audio: {str(e)}"}), 500

    return jsonify({
        "status": "success",
        "download_url": download_link,
        "spotify_url": spotify_url,
        "track_name": track_info["song_name"],
        "artist_name": track_info["artist_name"],
        "album_image": track_info.get("album_image"),
        "duration_ms": track_info.get("duration_ms")
    })

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "name": "Spotify Track Downloader API",
        "version": "2.0.0",
        "endpoints": {
            "/api/track": {
                "methods": ["GET", "POST"],
                "parameters": {
                    "url": "Spotify track URL (required)",
                    "download": "true/false - Download file or return link (optional, default: false)"
                },
                "examples": {
                    "get_link": "/api/track?url=https://open.spotify.com/track/TRACK_ID",
                    "download_file": "/api/track?url=https://open.spotify.com/track/TRACK_ID&download=true"
                }
            }
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
