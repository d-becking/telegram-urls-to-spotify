import os
import re
import json
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from shazamio import Shazam
from difflib import SequenceMatcher
import unicodedata
import numpy as np
import requests
import csv
from datetime import datetime
from spotify_client import sp

######################################### General helpers  #############################################################
def load_links_from_json(json_file_path,  category):
    with open(json_file_path, 'r', encoding='utf-8') as json_file:
        links_data = json.load(json_file)
    if category == 'spotify':
        return links_data.get('spotify', [])
    elif category == 'youtube':
        return links_data.get('youtube', []) + links_data.get('youtu.be', [])
    elif category == 'shazam':
        return links_data.get('shazam', [])
    elif category == 'bandcamp':
        return links_data.get('bandcamp', [])
    elif category == 'soundcloud':
        return links_data.get('soundcloud', [])

def create_or_get_playlist(sp, user_id, playlist_name):
    playlists = sp.user_playlists(user_id)
    for playlist in playlists['items']: # Check if playlist already exists
        if playlist['name'] == playlist_name:
            print(f"Playlist '{playlist_name}' already exists.")
            print(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
            return playlist['id']
    # Create new if does not exist
    new_playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    print(f"Created new playlist '{playlist_name}'.")
    print(f"~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    return new_playlist['id']

def get_all_playlist_tracks(sp, playlist_id):
    existing_track_ids = []
    offset = 0
    limit = 100  # Spotify API returns up to 100 tracks per request
    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
        existing_track_ids.extend([item['track']['id'] for item in results['items']])
        if results['next'] is None:  # No more pages
            break
        offset += limit  # Move to the next page
    return existing_track_ids

def delete_all_playlist_tracks(sp, playlist_id):
    offset = 0
    limit = 100  # Spotify API returns up to 100 tracks per request
    while True:
        results = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
        tracks = [item['track']['uri'] for item in results['items']]
        if tracks:
            sp.playlist_remove_all_occurrences_of_items(playlist_id, tracks)
        else:
            break
        if results['next'] is None:  # If there are no more pages
            break
        offset = 0
    remaining_tracks = sp.playlist_tracks(playlist_id, limit=1)
    if not remaining_tracks['items']:
        print("All tracks removed successfully.")
    else:
        print(f"{len(remaining_tracks['items'])} tracks remain in the playlist.")


def add_tracks_to_playlist(sp, playlist_id, track_ids, testrun=False):
    existing_track_ids = get_all_playlist_tracks(sp, playlist_id)
    # Filter track IDs that are already in pl
    new_tracks = [track_id for track_id in track_ids if track_id not in existing_track_ids]
    if new_tracks:
        if testrun:
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            print(f"{len(new_tracks)} new tracks to add to the playlist.")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
            for id in new_tracks:
                track = sp.track(id)
                print(f"{[artist['name'] for artist in track['artists']]} - {track['name']}")
        else:
            batch_size = 100
            for i in range(0, len(new_tracks), batch_size):
                batch = new_tracks[i:i + batch_size]
                sp.playlist_add_items(playlist_id, batch)
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
                print(f"Added {len(batch)} new tracks to the playlist.")
                print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
    else:
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")
        print("No new tracks to add; all tracks are already in the playlist.")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

def collect_all_tracks_from_playlists(sp, user_id, playlist_names):
    all_track_ids = []
    for playlist_name in playlist_names:
        playlist_id = create_or_get_playlist(sp, user_id, playlist_name)
        offset = 0
        while True:
            results = sp.playlist_tracks(playlist_id, offset=offset, limit=100) # Fetch tracks in batches of 100
            tracks = results['items']
            if not tracks:
                break  # If no more tracks returned exit loop
            for track in tracks:
                track_id = track['track']['id']
                if track_id:
                    all_track_ids.append(track_id)
            offset += 100  # Increase the offset to get next batch
    return all_track_ids

def check_for_duplicates_in_playlist(sp, playlist_id):
    existing_tracks = get_all_playlist_tracks(sp, playlist_id)
    track_counts = {}
    duplicates = []
    for track_id in existing_tracks:
        if track_id in track_counts:
            track_counts[track_id] += 1
            duplicates.append(track_id)
        else:
            track_counts[track_id] = 1
    if duplicates:
        print(f"Found {len(duplicates)} duplicate tracks in the playlist.")
        return duplicates
    else:
        print("No duplicate tracks found in the playlist.")
        return None
########################################################################################################################


######################  Link extraction and clustering from Telegram chat export #######################################
def extract_links_from_html(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file, 'html.parser')
        # Find all <a> tags, extract href attributes, and filter out unwanted or empty links
        return [
            a.get('href').strip() for a in soup.find_all('a', href=True)
            if a.get('href') and a.get('href').strip() and '#go_to_message' not in a.get('href')
               and '//t.me/' not in a.get('href') and 'messages' not in a.get('href')
        ]
def categorize_links(links):
    categories = {
        'youtube': [],
        'youtu.be': [],
        'spotify': [],
        'shazam': [],
        'bandcamp': [],
        'soundcloud': [],
        'discogs': [],
        'hardwax': [],
        'deejay': [],
        'other': []
    }
    for link in links:
        if 'youtube' in link:
            categories['youtube'].append(link)
        elif 'youtu.be' in link:
            categories['youtu.be'].append(link)
        elif 'spotify' in link:
            categories['spotify'].append(link)
        elif 'shazam' in link:
            categories['shazam'].append(link)
        elif 'soundcloud' in link:
            categories['soundcloud'].append(link)
        elif 'bandcamp' in link:
            categories['bandcamp'].append(link)
        elif 'discogs' in link:
            categories['discogs'].append(link)
        elif 'hardwax' in link:
            categories['hardwax'].append(link)
        elif 'deejay' in link:
            categories['deejay'].append(link)
        else:
            categories['other'].append(link)
    return categories

def process_html_files(file_paths):
    all_links = []
    for file_path in file_paths:
        links = extract_links_from_html(file_path)
        all_links.extend(links)
    categorized_links = categorize_links(all_links)
    return categorized_links
########################################################################################################################


######################################### Provider-specific routines  ###################################################

### Spotify
def extract_spotify_track_ids(spotify_links):
    track_ids = []
    for link in spotify_links:
        if 'track' in link:  # Ensure it's a track link, not an album or playlist
            track_id = link.split('/')[-1].split('?')[0]
            track_ids.append(track_id)
    return track_ids

### YouTube
def extract_youtube_video_ids(youtube_links):
    video_ids = []
    for link in youtube_links:
        if 'playlist' in link:
            continue
        if 'youtu.be' in link:
            video_id = link.split('/')[-1]
        elif 'youtube.com' in link:
            video_id = re.search(r'v=([a-zA-Z0-9_-]+)', link).group(1)
        video_ids.append(video_id)
    return video_ids

def get_video_titles_from_youtube(video_ids):
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    youtube = build('youtube', 'v3', developerKey=api_key)
    video_titles = {}
    def clean_video_id(video_id):
        # Remove any query parameters (e.g., '?feature=shared') from the video ID
        return re.split(r'[?&]', video_id)[0]

    clean_video_ids = [clean_video_id(vid) for vid in video_ids]
    for i in range(0, len(clean_video_ids), 50):  # YouTube API allows max 50 IDs per request
        request = youtube.videos().list(part='snippet', id=','.join(clean_video_ids[i:i + 50]))
        response = request.execute()
        for item in response.get('items', []):
            video_id = item['id']
            title = item['snippet']['title']
            if " - " in title or " – " in title:
                video_titles[video_id] = title
            elif 'tags' in item['snippet'] and len(item['snippet']['tags']) >= 1:
                video_titles[video_id] = item['snippet']['tags'][0] + ' - ' + title
            else:
                video_titles[video_id] = title
    return video_titles

### Shazam
def extract_shazam_ids(link):
    # This regex matches "/track/" followed by a sequence of digits (at least 1 digit, no upper limit)
    match = re.search(r'/track/(\d+)', link)
    if match:
        shazam_id = match.group(1)  # Extract track ID
        return shazam_id
    return None
async def get_shazam_track_info(track_id):
    shazam = Shazam()
    result = await shazam.track_about(track_id)  # Await the result from the Shazam API
    return result['title'], result['subtitle']

async def process_shazam_links(shazam_links, verbose=False):
    track_ids = []
    for shazam_link in shazam_links:
        shid = extract_shazam_ids(shazam_link)
        title, artist = await get_shazam_track_info(shid)  # Await the track info
        spotify_track_id = search_spotify_track(sp, query_title=title, query_artist=artist, min_similarity=0.7,
                                                verbose=verbose)
        if spotify_track_id:
            track_ids.append(spotify_track_id)
    return track_ids

### Bandcamp
def scrape_bandcamp_track_info(link):
    response = requests.get(link)
    if response.status_code == 200:
        try:
            soup = BeautifulSoup(response.text, 'html.parser')
            track_title = soup.find('meta', {'property': 'og:title'})['content']
            artist = soup.find('meta', {'name': 'title'})['content'].split(', by ')[-1]
            if ", by" in track_title and artist in track_title:
                track_title = track_title.split(", by")[0]
            if "remix" in track_title.lower() or "edit" in track_title.lower():
                return track_title, None
            else:
                return track_title, artist
        except:
            return None, None
    return None, None

def process_bandcamp_links(links, verbose=False):
    track_ids = []
    for link in links:
        if not "/track/" in link:
            continue
        title, artist = scrape_bandcamp_track_info(link)
        if title or artist:
            spotify_track_id = search_spotify_track(sp, query_title=title, query_artist=artist, min_similarity=0.7,
                                                    verbose=verbose)
            if spotify_track_id:
                track_ids.append(spotify_track_id)
    return track_ids

### Soundcloud
def scrape_soundcloud_track_info(link):
    try:
        response = requests.get(link)
        response.raise_for_status()  # Raise an error for bad responses (e.g., 404)
        soup = BeautifulSoup(response.text, 'html.parser')
        # Try to extract from <meta> tags
        artist_tag = soup.find('meta', {'property': 'og:audio:artist'})
        if artist_tag:
            artist = artist_tag['content']
        else:
            # Try extracting from <span> or <a> tags
            artist_tag = soup.find('span', {'class': 'soundTitle__username'})
            if artist_tag:
                artist = artist_tag.text.strip()
            else:
                # Try extracting from Twitter or other <meta> tags
                artist_tag = soup.find('meta', {'name': 'twitter:audio:artist_name'})
                if artist_tag:
                    artist = artist_tag['content']
                else:
                    # use the <title> tag
                    full_title = soup.find('title').text
                    if " by " in full_title:
                        artist = full_title.split(" by ")[1].split(" | ")[0].strip()
                    else:
                        artist = None
        track_title_tag = soup.find('meta', {'property': 'og:title'})
        if track_title_tag:
            track_title = track_title_tag['content']
        else:
            full_title = soup.find('title').text
            if " by " in full_title:
                track_title = full_title.split(" by ")[0].replace("Stream ", "").strip()
            else:
                track_title = None
        if clean_string(artist) in track_title.lower():
            return track_title, None
        else:
            return track_title, artist
    except Exception as e:
        return None, None

def process_soundcloud_links(links, verbose=False):
    track_ids = []
    for link in links:
        title, artist = scrape_soundcloud_track_info(link)
        if title:
            title = re.sub(r'((?:[^-]+ - ){2}).*', r'\1', title)
        if title or artist:
            spotify_track_id = search_spotify_track(sp, query_title=title, query_artist=artist, min_similarity=0.7,
                                                    verbose=verbose)
            if spotify_track_id:
                track_ids.append(spotify_track_id)
    return track_ids

def process_discogs_csv_rows(discogs_csv_path, min_similarity=0.65):
    track_ids = []
    with open(discogs_csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader, None)
        rows = []
        for row in reader:
            rows.append((row, datetime.strptime(row[9], '%Y-%m-%d %H:%M:%S')))
    rows.sort(key=lambda x: x[1])  # Sort the rows by the date added (oldest to newest)

    for row, _ in rows:
        sim = 0
        sim_year = 0
        if "CD" in row[4].strip() and not "LP" in row[4].strip():  # no CDs, only Vinyl
            continue
        if "to sell" in row[8].strip():
            continue
        artist = clean_discogs_string(row[1])  # Column 2: Artist
        album_name = clean_string(row[2])  # Column 3: Single, EP, Album, or LP name
        label = clean_discogs_string(row[3])  # Column 4: Label name
        year = row[6].strip()

        result_year = sp.search(q=f'artist:{artist} album:{album_name} label:{label} year:{year}', type="album", limit=1)
        if result_year['albums']['items']:
            query = f'{artist} {album_name} {year}'
            album = result_year['albums']['items'][0]
            artists = " ".join([a["name"] for a in album["artists"]])
            result_year = f'{artists} {album["name"]} {album["release_date"].split("-")[0]}'
            sim_year = token_based_similarity(query, result_year, return_sim=True)
            album_tracks_year = sp.album_tracks(album['id'])['items']

        result = sp.search(q=f'artist:{artist} album:{album_name} label:{label}', type="album", limit=1)
        if result['albums']['items']:
            query = f'{artist} {album_name}'
            album = result['albums']['items'][0]
            artists = " ".join([a["name"] for a in album["artists"]])
            result = f'{artists} {album["name"]}'
            sim = token_based_similarity(query, result, return_sim=True)
            album_tracks = sp.album_tracks(album['id'])['items']

        if sim > min_similarity or sim_year > min_similarity:
            if sim > sim_year:
                track_ids.extend([track['id'] for track in album_tracks])
            else:
                track_ids.extend([track['id'] for track in album_tracks_year])
        else:
            free_search_sim = []
            free_search_titles = {}
            results_unfiltered = sp.search(q=f'{artist} {album_name}', type="album", limit=8)
            if results_unfiltered['albums']['items']:
                query = f'{artist} {album_name}'
                for i, album in enumerate(results_unfiltered['albums']['items']):
                    artists = " ".join([a["name"] for a in album["artists"]])
                    result = f'{artists} {album["name"]}'
                    sim = token_based_similarity(query, result, return_sim=True)
                    free_search_sim.append(sim)
                    free_search_titles[i] = sp.album_tracks(album['id'])['items']
                    if sim < 0.3 or sim == 1:
                        break
                sim_argmax = np.argmax(free_search_sim)
                if free_search_sim[sim_argmax] > min_similarity:
                    track_ids.extend([track['id'] for track in free_search_titles[sim_argmax]])
    return track_ids
########################################################################################################################


############################################### Search engine #########################################################
def clean_string(text):
    textup = text.lower()  # Lowercase the string
    textup = textup.replace('\u200b', '')  # Remove zero-width spaces (e.g., \u200b)
    textup = textup.replace('â\x80\x93', '-')  # Replace corrupted en dash
    textup = textup.replace('â\x80\x94', '-')  # Replace corrupted em dash
    textup = unicodedata.normalize('NFKD', textup)
    textup = re.sub(r'original mix', '', textup)
    textup = re.sub(r'original', '', textup)
    textup = re.sub(r'premiere', '', textup)
    textup = re.sub(r'remastered', '', textup)
    textup = re.sub(r'remaster', '', textup)
    textup = re.sub(r'live version', '', textup)
    # Remove content within parentheses if they don't contain specified keywords
    textup = re.sub(r'\((?!.*?\b(mix|remix|version|edit)\b).*?\)', '', textup)
    # Remove content within brackets if they don't contain specified keywords
    textup = re.sub(r'\[(?!.*?\b(mix|remix|version|edit)\b).*?\]', '', textup)
    # Remove unwanted characters, but keep non-alphanumeric characters if they are embedded within a word
    # Also keep accented characters within the Latin-1 Supplement Unicode block
    textup = re.sub(r'(?<![\w\u00C0-\u017F])[^\w\s\-\u00C0-\u017F](?![\w\u00C0-\u017F])', '', textup)
    textup = re.sub(r'[()]', '', textup)  # removes parentheses
    return textup.strip()  # Remove Leading and Trailing Whitespace

def clean_discogs_string(text):
    textup = re.sub(r'\s*\(\d+\)', '', text)  # remove the (NUMBER) pattern from the artist or label name
    return textup.strip()

def token_based_similarity(query, result, min_similarity=0.65, max_similarity=1.0, return_sim=False):
    clean_query = clean_string(query)
    clean_result = clean_string(result)

    query_tokens = set(clean_query.split())
    result_tokens = set(clean_result.split())

    len_discrepancy_penalty = 1 - np.sqrt(abs(len(query_tokens) - len(result_tokens)) / max(len(query_tokens), len(result_tokens))) * 0.02
    token_weight = min((len(query_tokens) + len(result_tokens)) / 8, 1.0)

    common_tokens = query_tokens.intersection(result_tokens)
    token_similarity = (len(common_tokens) / max(len(query_tokens), len(result_tokens)))

    sequence_similarity = SequenceMatcher(None, clean_query, clean_result).ratio()

    sim = np.mean([token_similarity, sequence_similarity]) * len_discrepancy_penalty * token_weight

    if return_sim:
        if len(query_tokens) + len(result_tokens) == 6 and sim == 6/8:
            return 1.0
        else:
            return sim

    elif len(query_tokens) <= 3:
        if max_similarity < 1:
            return sim > min(min_similarity + 0.1, 1.0) and sim < max_similarity
        else:
            return sim > min(min_similarity + 0.1, 1.0)
    else:
        if max_similarity < 1:
            return sim > min_similarity and sim < max_similarity
        else:
            return sim > min_similarity

def search_spotify_track(sp, query_title, query_artist=None, min_similarity=0.65, verbose=False):
    def get_similarity(clean_query, track):
        artists = " ".join([a["name"] for a in track["artists"] if a["name"] not in track["name"]])
        result_str = f'{artists} - {track["name"]}'
        if (any(clean_string(artist["name"]) in clean_query for artist in track["artists"]) or
                any(clean_query.split(" - ")[0] in clean_string(artist["name"]) for artist in track["artists"])):
            similarity = token_based_similarity(clean_query, result_str, return_sim=True)
        elif SequenceMatcher(None, clean_query, result_str).ratio() > 0.9:
            similarity = token_based_similarity(clean_query, result_str, return_sim=False)
        else:
            similarity = 0.0
        return similarity
    def process_results(clean_query, results, ini_track_id=None):
        best_sim = 0.0
        best_track_id = None
        best_track = None
        for track in results['tracks']['items']:
            sim = get_similarity(clean_query, track)
            if sim > best_sim and sim > min_similarity:
                best_sim = sim
                best_track_id = track['id']
                best_track = f'{" ".join([a["name"] for a in track["artists"] if a["name"] not in track["name"]])} - {track["name"]}'
            if track['id'] != ini_track_id and (sim < 0.44 or sim == 1):
                break
        if best_track and verbose:
            print(f'---> resulted in: {best_track} (certainty {best_sim*100:.2f}%)')
        return best_track_id

    if verbose:
        print(f"Search for: {query_artist+' - ' if query_artist else ''} {query_title}")

    if query_artist:
        query_artist = clean_string(query_artist)
    clean_query = f"{query_artist} - {clean_string(query_title)}" if query_artist else clean_string(query_title)
    search_query = f"artist:{query_artist} track:{query_title}" if query_artist else clean_query

    # Initial search
    result = sp.search(q=search_query, type='track', limit=1)
    if not result['tracks']['items']:
        if query_artist:  # try w/o artist(s) because title might contain artist(s)
            return search_spotify_track(sp, query_title, min_similarity=min_similarity, verbose=verbose)
        else:
            sim1 = 0.0
    else:
        track1 = result['tracks']['items'][0]
        sim1 = get_similarity(clean_query, track1)
        res1 = f'{" ".join([a["name"] for a in track1["artists"] if a["name"] not in track1["name"]])} - {track1["name"]}'
        if sim1 >= 0.9:
            if verbose:
                print(f'---> resulted in: {res1} (certainty {sim1*100:.2f}%)')
            return track1['id']

    # Extended search if the first track's similarity isn't high enough
    results_unfiltered = sp.search(q=search_query, type='track', limit=6)
    if not results_unfiltered['tracks']['items']:
        if verbose:
            print("---> resulted in: None (no matches found)")
        return None
    else:
        best_track_id = process_results(clean_query, results_unfiltered, ini_track_id=track1['id'])

        if verbose and best_track_id is None:
            if sim1 >= min_similarity:
                print(f'---> resulted in: {res1} (certainty {sim1*100:.2f}%)')
            else:
                print(f'---> resulted in: None - {res1} (certainty {sim1*100:.2f}%)')

    return best_track_id if best_track_id else (track1['id'] if sim1 >= min_similarity else None)

########################################################################################################################

##################################### Additional funcitonalities  ######################################################
def get_playlist_info(playlist_id):
    playlist = sp.playlist(playlist_id)
    print(f"Playlist Name: {playlist['name']}")
    print(f"Description: {playlist['description']}")
    print(f"Total Tracks: {playlist['tracks']['total']}")
    tracks = []
    offset = 0
    limit = 100
    while True:  # Fetch tracks in batches of 100
        response = sp.playlist_tracks(playlist_id, offset=offset, limit=limit)
        tracks.extend(response['items'])
        if response['next'] is None:
            break
        offset += limit
    for idx, item in enumerate(tracks):
        track = item['track']
        added_at = item['added_at']
        print(f"\nTrack {idx + 1}:")
        print(f"Name: {track['name']}")
        print(f"Artist(s): {', '.join([artist['name'] for artist in track['artists']])}")
        print(f"Album: {track['album']['name']}")
        print(f"Added at: {added_at}")
        print(f"Duration: {track['duration_ms'] // 60000} min {track['duration_ms'] % 60000 // 1000} sec")
########################################################################################################################