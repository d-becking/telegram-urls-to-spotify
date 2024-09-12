import os
import glob
import json
import argparse

from spotify_client import sp
from functionalities import (process_html_files, load_links_from_json, create_or_get_playlist, extract_spotify_track_ids,
                             add_tracks_to_playlist, remove_duplicates_from_playlist, extract_youtube_video_ids,
                             get_video_titles_from_youtube, search_spotify_track, get_playlist_info)

parser = argparse.ArgumentParser(description='Spotify playlist automat')
parser.add_argument('--print_playlist_info', action="store_true", help='prints meta info of a playlist link')
parser.add_argument('--playlist_url',
                                default='https://open.spotify.com/playlist/7lwr0g1SzDVSMT3lDtctLz?si=765b47477f094fe7',
                                help='a playlist link')
parser.add_argument('--extract_new_links', action="store_true", help='extract links from Telegram-exported chat html data')
parser.add_argument("--tg_chat_export_path", default="./chat_data", help='path to Telegram-exported html files')
parser.add_argument("--spotify", action="store_true", help='generate/update spotify playlist')
parser.add_argument("--yt", action="store_true", help='generate/update youtube playlist')


def main():
    args = parser.parse_args()
    json_file_path = "categorized_links.json"
    user_id = sp.current_user()['id'] # Get the current Spotify user ID

    if args.extract_new_links:
        html_files = glob.glob(os.path.join(args.tg_chat_export_path, "*.html"))
        categorized_links = process_html_files(html_files)
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(categorized_links, json_file, indent=4)

    if args.spotify: # Extract Spotify IDs and generate playlist
        playlist_name = "BERG_SPOTIFY_ONLY"
        spotify_links = load_links_from_json(json_file_path, category='spotify')
        track_ids = extract_spotify_track_ids(spotify_links)

        playlist_id = create_or_get_playlist(sp, user_id, playlist_name)
        add_tracks_to_playlist(sp, playlist_id, track_ids)
        remove_duplicates_from_playlist(sp, playlist_id)

    if args.yt: # Extract YouTube video IDs and get titles from YouTube API
        youtube_links = load_links_from_json(json_file_path, category='youtube')
        youtube_video_ids = extract_youtube_video_ids(youtube_links)
        video_titles = get_video_titles_from_youtube(youtube_video_ids)

        playlist_name = "BERG_YT_2_SPOTIFY_CERT0.65+"
        youtube_track_ids = []
        for video_id, title in video_titles.items():
            spotify_track_id = search_spotify_track(sp, title, min_similarity=0.65)
            if spotify_track_id:
                youtube_track_ids.append(spotify_track_id)

        playlist_id = create_or_get_playlist(sp, user_id, playlist_name)
        add_tracks_to_playlist(sp, playlist_id, youtube_track_ids)
        remove_duplicates_from_playlist(sp, playlist_id)

        playlist_name = "BERG_YT_2_SPOTIFY_CERT0.3-0.65"
        youtube_track_ids = []
        for video_id, title in video_titles.items():
            spotify_track_id = search_spotify_track(sp, title, min_similarity=0.3, max_similarity=0.65)
            if spotify_track_id:
                youtube_track_ids.append(spotify_track_id)

        playlist_id = create_or_get_playlist(sp, user_id, playlist_name)
        add_tracks_to_playlist(sp, playlist_id, youtube_track_ids)
        remove_duplicates_from_playlist(sp, playlist_id)

    if args.print_playlist_info:
        playlist_id = args.playlist_url.split("/")[-1].split("?")[0]
        get_playlist_info(playlist_id)

if __name__ == '__main__':
    main()
