from flask import Flask, request, jsonify, send_file
import requests
import os
import re
import tempfile
import base64

app = Flask(__name__)

SPOTIFY_API_URL = "https://spotisongdownloader.com/api/composer/spotify/ssdw23456ytrfds.php"

# Identifiants Spotify (les mêmes que dans ton script JS)
SPOTIFY_CLIENT_ID = '9efa9943cf4f470f84533bc9fea99392'
SPOTIFY_CLIENT_SECRET = 'd0421a577f0c4b258d5b6b7b05371d88'

spotify_token = None
token_expiry = 0

def get_spotify_token():
    """Get Spotify API access token"""
    global spotify_token, token_expiry
    
    import time
    current_time = time.time()
    
    # Réutiliser le token s'il est encore valide
    if spotify_token and current_time < token_expiry:
        return spotify_token
    
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('utf-8')
    auth_base64 = base64.b64encode(auth_bytes).decode('utf-8')
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post(
            'https://accounts.spotify.com/api/token',
            headers=headers,
            data=data,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        
        spotify_token = result['access_token']
        # Expiration - 1 minute de sécurité
        token_expiry = current_time + result['expires_in'] - 60
        
        return spotify_token
    except Exception as e:
        print(f"Error getting Spotify token: {e}")
        return None

def extract_track_id(spotify_url):
    """Extract track ID from Spotify URL"""
    match = re.search(r'track/([a-zA-Z0-9]+)', spotify_url)
    if match:
        return match.group(1)
    return None

def get_track_info(spotify_url):
    """Extract real track info from Spotify API"""
    track_id = extract_track_id(spotify_url)
    
    if not track_id:
        return None
    
    token = get_spotify_token()
    if not token:
        return None
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        response = requests.get(
            f'https://api.spotify.com/v1/tracks/{track_id}',
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        track_data = response.json()
        
        return {
            "song_name": track_data['name'],
            "artist_name": ', '.join([artist['name'] for artist in track_data['artists']]),
            "album_image": track_data['album']['images'][0]['url'] if track_data['album']['images'] else None,
            "duration_ms": track_data['duration_ms']
        }
    except Exception as e:
        print(f"Error getting track info: {e}")
        return None

def get_download_link(spotify_url):
    """Get download link from the downloader service"""
    
    track_info = get_track_info(spotify_url)
    
    if not track_info:
        return None
    
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
    
    cookies = {
        "quality": "m4a"
    }
    
    try:
        response = requests.post(
            SPOTIFY_API_URL, 
            headers=headers, 
            data=data, 
            cookies=cookies, 
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "success":
            return {
                "download_link": result.get("dlink"),
                "track_info": track_info
            }
        else:
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/api/track', methods=['GET', 'POST'])
def get_track():
    """Get track download link or file"""
    
    if request.method == 'POST':
        data = request.get_json()
        spotify_url = data.get('url')
        download = data.get('download', False)
    else:
        spotify_url = request.args.get('url')
        download = request.args.get('download', 'false').lower() == 'true'
    
    if not spotify_url:
        return jsonify({"error": "Spotify URL is required"}), 400
    
    # Validate Spotify URL
    if not spotify_url.startswith("https://open.spotify.com/track/"):
        return jsonify({"error": "Invalid Spotify track URL"}), 400
    
    # Get download link with track info
    result = get_download_link(spotify_url)
    
    if not result or not result.get("download_link"):
        return jsonify({"error": "Failed to get download link"}), 500
    
    download_link = result["download_link"]
    track_info = result["track_info"]
    
    # If download=true, download and send file
    if download:
        try:
            audio_response = requests.get(download_link, timeout=60)
            audio_response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.m4a') as tmp_file:
                tmp_file.write(audio_response.content)
                tmp_path = tmp_file.name
            
            # Send file and clean up
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
    
    # Otherwise, just return the link with track info
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
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def home():
    """API documentation"""
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
