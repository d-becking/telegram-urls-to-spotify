import os
import glob
import json
import argparse
import asyncio
import numpy as np
import matplotlib.pyplot as plt
from spotify_client import sp
from functionalities import (process_html_files, load_links_from_json, create_or_get_playlist, extract_spotify_track_ids,
                             add_tracks_to_playlist, extract_youtube_video_ids, get_video_titles_from_youtube,
                             process_shazam_links, process_bandcamp_links, process_soundcloud_links, search_spotify_track,
                             get_playlist_info, collect_all_tracks_from_playlists, check_for_duplicates_in_playlist,
                             process_discogs_csv_rows, delete_all_playlist_tracks)


parser = argparse.ArgumentParser(description='Spotify Playlist Automat (SPA)')
parser.add_argument('--extract_new_links', action="store_true", help='extract links from Telegram-exported chat html data')
parser.add_argument("--tg_chat_export_path", default="", type=str, help='path to Telegram-exported html files')
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
parser.add_argument("--verbose", action="store_true", help='Stdout process information.')
parser.add_argument("--test_run", action="store_true", help='Only tests for new search results but does not add them.')
parser.add_argument("--analyse_playlist_metadata", action="store_true", help='Outputs and visualizes some metadata of playlists.')
print("###########################################################################################")

def main():
    args = parser.parse_args()
    if args.tg_chat_export_path:
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
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids, testrun=args.test_run)

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
                spotify_track_id = search_spotify_track(sp, title, min_similarity=0.65, verbose=args.verbose)
                if spotify_track_id:
                    youtube_track_ids.append(spotify_track_id)
            unique_track_ids = list(dict.fromkeys(youtube_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids, testrun=args.test_run)

    if args.shazam or args.all:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}SHAZAM_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            shazam_urls = load_links_from_json(json_file_path, category='shazam')
            shazam_track_ids = asyncio.run(process_shazam_links(shazam_urls, verbose=args.verbose))
            unique_track_ids = list(dict.fromkeys(shazam_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids, testrun=args.test_run)

    if args.bandcamp or args.all:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}BANDCAMP_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            bandcamp_urls = load_links_from_json(json_file_path, category='bandcamp')
            bc_track_ids = process_bandcamp_links(bandcamp_urls, verbose=args.verbose)
            unique_track_ids = list(dict.fromkeys(bc_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids, testrun=args.test_run)

    if args.soundcloud or args.all:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}SOUNDCLOUD_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            soundcloud_urls = load_links_from_json(json_file_path, category='soundcloud')
            soundcloud_track_ids = process_soundcloud_links(soundcloud_urls, verbose=args.verbose)
            unique_track_ids = list(dict.fromkeys(soundcloud_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids, testrun=args.test_run)

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
            add_tracks_to_playlist(sp, playlist_id, all_unique_track_ids, testrun=args.test_run)
            check_for_duplicates_in_playlist(sp, playlist_id)

    if args.discogs_csv_path:
        playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}DISCOGS_2_SPOTIFY")
        if args.delete_all_tracks:
            delete_all_playlist_tracks(sp, playlist_id)
        else:
            discogs_track_ids = process_discogs_csv_rows(args.discogs_csv_path, min_similarity=0.8)
            unique_track_ids = list(dict.fromkeys(discogs_track_ids))
            add_tracks_to_playlist(sp, playlist_id, unique_track_ids, testrun=args.test_run)

    if args.print_playlist_info:
        playlist_id = args.playlist_url.split("/")[-1].split("?")[0]
        if playlist_id == '<YOUR_PLAYLIST_ID>':
            playlist_id = create_or_get_playlist(sp, user_id, f"{pl_prefix}ALLSTARS")
        get_playlist_info(playlist_id)

    if args.analyse_playlist_metadata:

        plot_results = False

        if os.path.exists('metadata.json'):
            print("Loading existing metadata.json...")
            with open('metadata.json', 'r') as f:
                metadata = json.load(f)
        else:
            print("Extracting metadata and saving to file metadata.json...")
            all_track_ids, metadata = collect_all_tracks_from_playlists(sp, user_id,
                                                                        [f"{pl_prefix}ALLSTARS"],
                                                                        return_metadata=True)
            with open('metadata.json', 'w') as f:
                json.dump(metadata, f, indent=4)

        flat_artists = []
        for entry in metadata["artists"]:
            flat_artists.extend(entry.split(', '))

        metadata["artists"] = flat_artists

        k_art, k_year, k_label = 112, 20, 106  # Number of top elements to retrieve

        # Artists - Sort by frequency
        uart, ctsart = np.unique(metadata["artists"], return_counts=True)
        sorted_indices_art = np.argsort(-ctsart)
        top_k_artists = uart[sorted_indices_art][:k_art]
        top_k_artists_counts = ctsart[sorted_indices_art][:k_art]

        # Year - Sort by frequency
        uyear, ctsyear = np.unique(metadata["year"], return_counts=True)
        sorted_indices_year = np.argsort(-ctsyear)
        top_k_years = uyear[sorted_indices_year][:k_year]
        top_k_years_counts = ctsyear[sorted_indices_year][:k_year]

        # Sort top-k years chronologically
        chronological_indices = np.argsort(top_k_years.astype(int))
        top_k_years = top_k_years[chronological_indices]
        top_k_years_counts = top_k_years_counts[chronological_indices]

        # Label - Sort by frequency
        ulab, ctslab = np.unique(metadata["label"], return_counts=True)
        sorted_indices_lab = np.argsort(-ctslab)
        top_k_labels = ulab[sorted_indices_lab][:k_label]
        top_k_labels_counts = ctslab[sorted_indices_lab][:k_label]

        # Print Results
        print(f"Top-{k_art} Artists:")
        for artist, count in zip(top_k_artists, top_k_artists_counts):
            print(f"{artist} ({count}x)")

        print(f"\nTop-{k_year} Years:")
        for year, count in zip(top_k_years, top_k_years_counts):
            print(f"{year} ({count}x)")

        print(f"\nTop-{k_label} Labels:")
        for label, count in zip(top_k_labels, top_k_labels_counts):
            print(f"{label} ({count}x)")

        if plot_results:

            def add_value_labels(ax, spacing=5):
                for rect in ax.patches:
                    y_value = rect.get_height()
                    x_value = rect.get_x() + rect.get_width() / 2
                    ax.annotate(f'{int(y_value)}',
                                (x_value, y_value),
                                textcoords="offset points",
                                xytext=(0, spacing),
                                ha='center')

            # Plotting Artists Histogram
            plt.figure(figsize=(21, 6))
            bars = plt.bar(top_k_artists, top_k_artists_counts,
                           color=plt.cm.viridis(np.linspace(0.3, 0.9, len(top_k_artists))),
                           edgecolor='black')
            plt.title(f"Most Reported Artists", fontsize=16)
            plt.ylabel("Count")
            plt.xticks(rotation=90, fontsize=10)
            plt.grid(axis='y', linestyle='--', alpha=0.6)
            add_value_labels(plt.gca())
            plt.xlim(-0.5, len(top_k_artists) - 0.5)  # Remove extra space on x-axis
            plt.tight_layout()
            plt.savefig("top_artists.png", bbox_inches='tight')
            plt.close()

            # Plotting Years Histogram (Chronological)
            plt.figure(figsize=(10, 5))
            bars = plt.bar(top_k_years, top_k_years_counts, color=plt.cm.plasma(np.linspace(0.3, 0.9, len(top_k_years))),
                           edgecolor='black')
            plt.title(f"Top-{k_year} Track Release Years", fontsize=16)
            plt.ylabel("Count")
            plt.xticks(rotation=45, fontsize=10)
            plt.grid(axis='y', linestyle='--', alpha=0.6)
            add_value_labels(plt.gca())
            plt.xlim(-0.5, len(top_k_years) - 0.5)  # Remove extra space on x-axis
            plt.tight_layout()
            plt.savefig("top_years.png", bbox_inches='tight')
            plt.close()

            # Plotting Labels Histogram
            plt.figure(figsize=(19, 6))
            bars = plt.bar(top_k_labels, top_k_labels_counts, color=plt.cm.magma(np.linspace(0.3, 0.9, len(top_k_labels))),
                           edgecolor='black')
            plt.title(f"Most Reported Labels", fontsize=16)
            plt.ylabel("Count")
            plt.xticks(rotation=90, fontsize=10)
            plt.grid(axis='y', linestyle='--', alpha=0.6)
            add_value_labels(plt.gca())
            plt.xlim(-0.5, len(top_k_labels) - 0.5)  # Remove extra space on x-axis
            plt.tight_layout()
            plt.savefig("top_labels.png", bbox_inches='tight')
            plt.close()

if __name__ == '__main__':
    main()
