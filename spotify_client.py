import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os

# Initialize the Spotify client
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8080")

cache_path = f".spotify-auth-{SPOTIPY_CLIENT_ID[:6]}-cache"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="playlist-modify-private playlist-read-private",
    cache_path=cache_path,
))
