from flask import Flask, request, jsonify, send_file
import requests
import os
from urllib.parse import quote
import tempfile

app = Flask(__name__)

SPOTIFY_API_URL = "https://spotisongdownloader.com/api/composer/spotify/ssdw23456ytrfds.php"

def get_track_info(spotify_url):
    """Extract track info from Spotify API or use defaults"""
    # Pour simplifier, on utilise des valeurs par défaut
    # Vous pouvez intégrer l'API Spotify officielle ici
    return {
        "song_name": "Track",
        "artist_name": "Artist"
    }

def get_download_link(spotify_url):
    """Get download link from the downloader service"""
    
    track_info = get_track_info(spotify_url)
    
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://spotisongdownloader.com",
        "Referer": "https://spotisongdownloader.com/track.php",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "X-Requested-With": "XMLHttpRequest"
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
        response = requests.post(SPOTIFY_API_URL, headers=headers, data=data, cookies=cookies, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get("status") == "success":
            return result.get("dlink")
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
    
    # Get download link
    download_link = get_download_link(spotify_url)
    
    if not download_link:
        return jsonify({"error": "Failed to get download link"}), 500
    
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
                download_name='track.m4a'
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
    
    # Otherwise, just return the link
    return jsonify({
        "status": "success",
        "download_url": download_link,
        "spotify_url": spotify_url
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
        "version": "1.0.0",
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
