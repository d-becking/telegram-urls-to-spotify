import os
import glob
import json
import argparse
import asyncio
import random
from spotify_client import sp
from functionalities import (process_html_files, load_links_from_json, create_or_get_playlist, extract_spotify_track_ids,
                             add_tracks_to_playlist, extract_youtube_video_ids, get_video_titles_from_youtube,
                             process_shazam_links, process_bandcamp_links, process_soundcloud_links, search_spotify_track,
                             get_playlist_info, collect_all_tracks_from_playlists, check_for_duplicates_in_playlist,
                             process_discogs_csv_rows, delete_all_playlist_tracks)


parser = argparse.ArgumentParser(description='Spotify Playlist Automat (SPA)')
parser.add_argument('--extract_new_links', action="store_true", help='extract links from Telegram-exported chat html data')
parser.add_argument("--tg_chat_export_path", default="./chat_data", type=str, help='path to Telegram-exported html files')
parser.add_argument("--spotify", action="store_true", help='generate/update spotify playlist')
parser.add_argument("--yt", action="store_true", help='generate/update youtube playlist')
parser.add_argument("--shazam", action="store_true", help='generate/update shazam playlist')
parser.add_argument("--bandcamp", action="store_true", help='generate/update bandcamp playlist')
parser.add_argument("--soundcloud", action="store_true", help='generate/update soundcloud playlist')
parser.add_argument("--all", action="store_true", help='generate/update all playlists')
parser.add_argument("--merge_playlists", action="store_true", help='Merge all playlists into one Allstar playlist')
parser.add_argument('--print_playlist_info', action="store_true", help='prints meta info of a playlist link')
parser.add_argument('--playlist_url', default='https://open.spotify.com/playlist/<YOUR_PLAYLIST_ID>', type=str, help='playlist link')
parser.add_argument('--pers_pl_name_pref', default='', type=str, help='Personalized prefix for playlist name')
parser.add_argument('--discogs_csv_path', default='', type=str, help='Path to Discogs-exported csv file')
parser.add_argument("--delete_all_tracks", action="store_true", help='Deletes all tracks from a playlist')


def main():
    args = parser.parse_args()
    json_file_path = f"{args.tg_chat_export_path}/categorized_links.json"
    user_id = sp.current_user()['id']
    pl_prefix = args.pers_pl_name_pref + '_' if args.pers_pl_name_pref else ''

    if args.extract_new_links:
        html_files = glob.glob(os.path.join(args.tg_chat_export_path, "*.html"))
        html_files.sort(key=lambda x: os.path.basename(x))
        categorized_links = process_html_files(html_files)
        with open(json_file_path, 'w', encoding='utf-8') as json_file:
            json.dump(categorized_links, json_file, indent=4)

    if args.spotify or args.all:  # Extract Spotify IDs and generate playlist
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}SPOTIFY_ONLY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            spotify_links = load_links_from_json(json_file_path, category='spotify')
            track_ids = extract_spotify_track_ids(spotify_links)
            unique_track_ids = list(dict.fromkeys(track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids)

    if args.yt or args.all:  # Extract YouTube video IDs and get titles from YouTube API
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}YT_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            youtube_links = load_links_from_json(json_file_path, category='youtube')
            youtube_video_ids = extract_youtube_video_ids(youtube_links)
            video_titles = get_video_titles_from_youtube(youtube_video_ids)

            youtube_track_ids = []
            for video_id, title in video_titles.items():
                spotify_track_id = search_spotify_track(sp, title, min_similarity=0.65)
                if spotify_track_id:
                    youtube_track_ids.append(spotify_track_id)
            unique_track_ids = list(dict.fromkeys(youtube_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids)

    if args.shazam or args.all:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}SHAZAM_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            shazam_urls = load_links_from_json(json_file_path, category='shazam')
            shazam_track_ids = asyncio.run(process_shazam_links(shazam_urls))
            unique_track_ids = list(dict.fromkeys(shazam_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids)

    if args.bandcamp or args.all:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}BANDCAMP_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            bandcamp_urls = load_links_from_json(json_file_path, category='bandcamp')
            bc_track_ids = process_bandcamp_links(bandcamp_urls)
            unique_track_ids = list(dict.fromkeys(bc_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids)

    if args.soundcloud or args.all:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}SOUNDCLOUD_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            soundcloud_urls = load_links_from_json(json_file_path, category='soundcloud')
            soundcloud_track_ids = process_soundcloud_links(soundcloud_urls)
            unique_track_ids = list(dict.fromkeys(soundcloud_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids)

    if args.merge_playlists:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}ALLSTARS")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            playlist_names = [  # Create joint playlist
                f"{pl_prefix}SPOTIFY_ONLY",
                f"{pl_prefix}YT_2_SPOTIFY",
                f"{pl_prefix}BANDCAMP_2_SPOTIFY",
                f"{pl_prefix}SOUNDCLOUD_2_SPOTIFY",
                f"{pl_prefix}SHAZAM_2_SPOTIFY"
            ]
            all_track_ids = collect_all_tracks_from_playlists(sp, user_id, playlist_names)
            all_unique_track_ids = list(dict.fromkeys(all_track_ids))
            # random.shuffle(all_unique_track_ids)
            add_tracks_to_playlist(sp, playlist_id, all_unique_track_ids)
            check_for_duplicates_in_playlist(sp, playlist_id)

    if args.discogs_csv_path:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}DISCOGS_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            discogs_track_ids = process_discogs_csv_rows(args.discogs_csv_path, min_similarity=0.8)
            unique_track_ids = list(dict.fromkeys(discogs_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids)

    if args.print_playlist_info:
        playlist_id = args.playlist_url.split("/")[-1].split("?")[0]
        get_playlist_info(playlist_id)

if __name__ == '__main__':
    main()
