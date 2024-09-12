# Spotify Playlist Automat

This project provides scripts and utilities to extract and process URLs from Telegram chats exported in `*.html` format. 
The extracted URLs are categorized into the following groups: 'YouTube', 'Spotify', 'Shazam', 'Bandcamp', 
'SoundCloud', 'Discogs', 'Hardwax', 'Deejay', and 'Other'.

Once categorized, the program attempts to create Spotify playlists based on the provided links. It utilizes the APIs of
Spotify, YouTube, and Shazam, as well as custom web scrapers, to accurately identify artist and title information for 
each link.

Finally, a built-in search engine refines the playlist by adding only tracks that are confidently matched to the music 
pieces associated with the URLs. To achieve this, the program employs several certainty measures and iterates through 
Spotify requests for accurate results.

# Telegram URLs to Spotify
## Installation

Clone the repository and install the requirements by executing `create_venv.sh`:
   ```bash
   git clone https://github.com/d-becking/telegram-urls-to-spotify.git
   cd spotify-playlist-automat
   ./create_venv.sh
   ```

Alternatively, you can manually create a virtual environment and install the requirements:
   ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
   ```


### **API Credentials Setup**

### Spotify API  

To use the Spotify API, you need to set up API credentials. Follow these steps:

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications) and create a new app.
2. Obtain your **Client ID** and **Client Secret** from the app's settings.
3. Set your Spotify credentials in the environment variables or configure them in `spotify_client.py`.

To set credentials using environment variables, add these to your terminal session:

```bash
export SPOTIFY_CLIENT_ID='your-client-id'
export SPOTIFY_CLIENT_SECRET='your-client-secret'
export SPOTIFY_REDIRECT_URI='your-redirect-uri'
```

### YouTube API:
1. Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
2. Enable the **YouTube Data API v3** for your project.
3. Obtain your API Key from the credentials section.
4. Set your YouTube API Key in the environment:
```bash
export YOUTUBE_API_KEY='your-youtube-api-key'
```

## Getting Started

First, you may want to extract the links from the Telegram html files and cluster them:
   ```bash
   python spotify_playlist_automat.py --extract_new_links --tg_chat_export_path './<YOUR_PATH>'
   ```

After that you can generate playlists based on the categorized links for different platforms:
   ```bash
   python spotify_playlist_automat.py --spotify --yt
   ```

or all together:
   ```bash
   python spotify_playlist_automat.py --all
   ```

If you want to merge all generated playlist into one large Allstars playlist use:
   ```bash
   python spotify_playlist_automat.py --merge_playlists
   ```

### License

This project is licensed under the BSD-3 License - see the LICENSE file for details.

### Contributing
Contributions are welcome! Please open a pull request or an issue for any changes or improvements.
Feel free to reach out via Email (see my [homepage](https://dbecking.com/)).