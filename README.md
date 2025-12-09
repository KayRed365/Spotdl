# Spotify Track Downloader API

API simple pour télécharger des pistes Spotify via spotisongdownloader.com

## 🚀 Déploiement sur Render

1. Créez un nouveau dépôt GitHub avec ces fichiers :
   - `app.py`
   - `requirements.txt`
   - `render.yaml`

2. Connectez votre repo à Render.com

3. L'API sera automatiquement déployée !

## 📡 Endpoints

### GET/POST `/api/track`

**Paramètres :**
- `url` (requis) : URL de la piste Spotify
- `download` (optionnel) : `true` pour télécharger le fichier, `false` pour obtenir le lien

**Exemples :**

```bash
# Obtenir le lien de téléchargement
curl "https://your-app.onrender.com/api/track?url=https://open.spotify.com/track/51mFN9rbJRAvVhxFlIly6X"

# Télécharger directement le fichier
curl "https://your-app.onrender.com/api/track?url=https://open.spotify.com/track/51mFN9rbJRAvVhxFlIly6X&download=true" -o track.m4a

# POST request
curl -X POST "https://your-app.onrender.com/api/track" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://open.spotify.com/track/51mFN9rbJRAvVhxFlIly6X", "download": false}'
```

**Réponse (download=false) :**
```json
{
  "status": "success",
  "download_url": "https://awd8.mymp3.xyz/phmp4?fname=...",
  "spotify_url": "https://open.spotify.com/track/..."
}
```

**Réponse (download=true) :**
Fichier audio M4A téléchargé directement

### GET `/health`

Check de santé de l'API

### GET `/`

Documentation de l'API

## 🛠️ Installation locale

```bash
# Cloner le repo
git clone https://github.com/votre-username/spotify-downloader-api.git
cd spotify-downloader-api

# Installer les dépendances
pip install -r requirements.txt

# Lancer l'API
python app.py
```

L'API sera disponible sur `http://localhost:5000`

## ⚠️ Notes

- Cette API utilise un service tiers (spotisongdownloader.com)
- Le service peut avoir des limitations de rate limiting
- À utiliser conformément aux conditions d'utilisation de Spotify

## 📝 License

MIT
