#!/bin/bash

if [ -z "$1" ]; then
    echo "Error: No date provided."
    echo "Usage: ./example_automator.sh YYYY-MM-DD"
    exit 1
fi

DATE=$1
PLAYLIST_NAME="MyPlaylist"

shift # Shift positional parameters to access additional flags
ADDITIONAL_FLAGS="$@"

source ./env/bin/activate

export SPOTIPY_CLIENT_ID=""
export SPOTIPY_CLIENT_SECRET=""
export YOUTUBE_API_KEY=""

# Extracting new URLs
python3 spotify_playlist_automat.py --extract_new_links --tg_chat_export_path "./<your_path>_$DATE"

# Search and add new tracks to playlists
python3 spotify_playlist_automat.py --all --merge_playlists --pers_pl_name_pref BERG --tg_chat_export_path "./berg_$DATE" --verbose $ADDITIONAL_FLAGS

deactivate

echo "All scripts executed successfully with date: $DATE"
