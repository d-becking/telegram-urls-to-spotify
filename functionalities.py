import os
import re
import json
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from shazamio import Shazam
from difflib import SequenceMatcher
import numpy as np
import requests
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
    for playlist in playlists['items']:# Check if the playlist already exists
        if playlist['name'] == playlist_name:
            print(f"Playlist '{playlist_name}' already exists.")
            return playlist['id']
    # Create a new playlist if it doesn't exist
    new_playlist = sp.user_playlist_create(user_id, playlist_name, public=False)
    print(f"Created new playlist '{playlist_name}'.")
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

def add_tracks_to_playlist(sp, playlist_id, track_ids):
    existing_track_ids = get_all_playlist_tracks(sp, playlist_id)
    # Filter out track IDs that are already in the playlist
    new_tracks = [track_id for track_id in track_ids if track_id not in existing_track_ids]
    if new_tracks:
        batch_size = 100
        for i in range(0, len(new_tracks), batch_size):
            batch = new_tracks[i:i + batch_size]
            sp.playlist_add_items(playlist_id, batch)
            print(f"Added {len(batch)} new tracks to the playlist.")
    else:
        print("No new tracks to add; all tracks are already in the playlist.")

def collect_all_tracks_from_playlists(sp, user_id, playlist_names):
    all_track_ids = []
    for playlist_name in playlist_names:
        playlist_id = create_or_get_playlist(sp, user_id, playlist_name)
        offset = 0
        while True:
            # Fetch tracks in batches of 100
            results = sp.playlist_tracks(playlist_id, offset=offset, limit=100)
            tracks = results['items']
            if not tracks:
                break  # If no more tracks are returned, exit the loop
            for track in tracks:
                track_id = track['track']['id']
                if track_id:
                    all_track_ids.append(track_id)
            offset += 100  # Increase the offset to get the next batch
    return all_track_ids

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

    for i in range(0, len(video_ids), 50):  # YouTube API allows max 50 IDs per request
        request = youtube.videos().list(part='snippet', id=','.join(video_ids[i:i + 50]))
        response = request.execute()
        for item in response['items']:
            video_id = item['id']
            if " - " in item['snippet']['title'] or ' – ' in item['snippet']['title']:
                title = item['snippet']['title']
            elif 'tags' in item['snippet'] and len(item['snippet']['tags']) >= 1:
                title = item['snippet']['tags'][0] + ' - ' + item['snippet']['title']
            video_titles[video_id] = title

    return video_titles

### Shazam
def extract_shazam_ids(link):
    # This regex matches "/track/" followed by a sequence of digits (at least 1 digit, no upper limit)
    match = re.search(r'/track/(\d+)', link)
    if match:
        shazam_id = match.group(1)  # Extract the track ID (sequence of digits)
        return shazam_id
    return None
async def get_shazam_track_info(track_id):
    shazam = Shazam()
    result = await shazam.track_about(track_id)  # Await the result from the Shazam API
    return result['title'], result['subtitle']

async def process_shazam_links(shazam_links):
    track_ids = []
    for shazam_link in shazam_links:
        shid = extract_shazam_ids(shazam_link)
        title, artist = await get_shazam_track_info(shid)  # Await the track info
        spotify_track_id = search_spotify_track(sp, query_title=title, query_artist=artist, min_similarity=0.7)
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

def process_bandcamp_links(links):
    track_ids = []
    for link in links:
        if not "/track/" in link:
            continue
        title, artist = scrape_bandcamp_track_info(link)
        if title or artist:
            spotify_track_id = search_spotify_track(sp, query_title=title, query_artist=artist, min_similarity=0.7)
            if spotify_track_id:
                track_ids.append(spotify_track_id)
    return track_ids

### Soundcloud
def scrape_soundcloud_track_info(link):
    try:
        response = requests.get(link)
        response.raise_for_status()  # Raise an error for bad responses (e.g., 404)
        soup = BeautifulSoup(response.text, 'html.parser')
        # 1. Try to extract from <meta> tags
        artist_tag = soup.find('meta', {'property': 'og:audio:artist'})
        if artist_tag:
            artist = artist_tag['content']
        else:
            # 2. Try extracting from <span> or <a> tags
            artist_tag = soup.find('span', {'class': 'soundTitle__username'})
            if artist_tag:
                artist = artist_tag.text.strip()
            else:
                # 3. Try extracting from Twitter or other <meta> tags
                artist_tag = soup.find('meta', {'name': 'twitter:audio:artist_name'})
                if artist_tag:
                    artist = artist_tag['content']
                else:
                    # 4. As a last resort, use the <title> tag
                    full_title = soup.find('title').text
                    if " by " in full_title:
                        artist = full_title.split(" by ")[1].split(" | ")[0].strip()
                    else:
                        artist = None
        # Extract the track title from <meta> or fallback to <title>
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

def process_soundcloud_links(links):
    track_ids = []
    for link in links:
        title, artist = scrape_soundcloud_track_info(link)
        if title or artist:
            spotify_track_id = search_spotify_track(sp, query_title=title, query_artist=artist, min_similarity=0.65)
            if spotify_track_id:
                track_ids.append(spotify_track_id)
    return track_ids

########################################################################################################################


############################################### Search engine #########################################################

def clean_string(text):
    # Lowercase the string and remove extra characters such as '[WSNF093]' or other common tags
    textup = text.lower()
    textup = re.sub(r'original mix', '', textup)
    textup = re.sub(r'original', '', textup)
    textup = re.sub(r'premiere', '', textup)
    textup = re.sub(r'remaster', '', textup)
    textup = re.sub(r'live version', '', textup)
    textup = re.sub(r'\(ft\..*?\)', '', textup)
    textup = re.sub(r'\(feat\..*?\)', '', textup)
    textup = re.sub(r'\(featuring.*?\)', '', textup)
    textup = re.sub(r'\[.*?\]', '', textup)  # Remove anything inside square brackets
    textup = re.sub(r'\((?!.*?\b(mix|remix|version|edit)\b).*?\)', '', textup)
    textup = re.sub(r'[^a-zA-Z0-9\s\-\u00C0-\u017F]', '', textup) # Keep alphanumeric characters (including accented letters), spaces, and hyphens
    return textup.strip()

def token_based_similarity(query, result, min_similarity=0.65, max_similarity=1.0):
    clean_query = clean_string(query)
    clean_result = clean_string(result)

    query_tokens = set(clean_query.split())
    result_tokens = set(clean_result.split())

    common_tokens = query_tokens.intersection(result_tokens)
    token_similarity = len(common_tokens) / max(len(query_tokens), len(result_tokens))

    sequence_similarity = SequenceMatcher(None, clean_query, clean_result).ratio()

    sim = np.mean([token_similarity, sequence_similarity])
    if len(query_tokens) <= 3:
        if max_similarity < 1:
            return sim > min(min_similarity + 0.1, 1.0) and sim < max_similarity
        else:
            return sim > min(min_similarity + 0.1, 1.0)
    else:
        if max_similarity < 1:
            return sim > min_similarity and sim < max_similarity
        else:
            return sim > min_similarity

def search_spotify_track(sp, query_title, query_artist=None, min_similarity=0.65, max_similarity=1.0):

    if query_artist is None:
        clean_query = clean_string(query_title)
        result = sp.search(q=clean_query, type='track', limit=1)
        listid = 0
        prelim_artist = result['tracks']['items'][0]['artists'][0]['name'].lower()
        prelim_title = result['tracks']['items'][0]['name'].lower()

        if result['tracks']['items']:
            if (not (prelim_artist in clean_query and prelim_title.split(' ')[0] in clean_query) or
                    ("remix" in result['tracks']['items'][0]['name'].lower() and "remix" not in clean_query)):
                result = sp.search(q=clean_query, type='track', limit=5)
                index = []
                for i, track_info in enumerate(result['tracks']['items']):  # Take the first artist
                    if ("remix" in track_info['name'].lower() and "remix" not in clean_query):
                        continue
                    if track_info['artists'][0]['name'].lower() in clean_query and track_info['name'].lower() in clean_query:
                        if i == 0:
                            break
                        else:
                            if len(index) < 1:
                                index.append(i)
                            else:
                                index[0] = i
                    elif track_info['artists'][0]['name'].lower() in clean_query:
                        index.append(i)

                if len(index) > 0:
                    listid = index[0]

            track_info = result['tracks']['items'][listid]
            result_title = track_info['name']
            result_artist = track_info['artists'][0]['name']  # Take the first artist

            # result_album = track_info['album']['name']
            # if len(track_info['artists']) > 1 and track_info['artists'][1]['name'].lower() in clean_query and track_info['artists'][1]['name'].lower() not in result_title.lower():
            #     result_artist += ' ' + track_info['artists'][1]['name']
            # if clean_string(result_album.split(',')[0]) in clean_query and clean_string(result_album.split(',')[0]) not in result_title.lower():
            #     mixed_result = result_artist + " - " + result_title + " - " + result_album.split(',')[0]
            # else:

            mixed_result = result_artist + " - " + result_title
            if token_based_similarity(query_title, mixed_result, min_similarity=min_similarity, max_similarity=max_similarity):
                return track_info['id']
    else:
        query = f"artist:{query_artist} track:{query_title}"
        result = sp.search(q=query,  type='track', limit=1)

        listid = 0
        if result['tracks']['items']:
            if (not (result['tracks']['items'][0]['artists'][0]['name'].lower() in query_artist.lower()) or
                    ("remix" in result['tracks']['items'][0]['name'].lower() and "remix" not in query_title.lower())):
                result = sp.search(q=query, type='track', limit=5)
                index = []
                for i, track_info in enumerate(result['tracks']['items']):  # Take the first artist
                    if ("remix" in track_info['name'].lower() and "remix" not in query_title.lower()):
                        continue
                    if track_info['artists'][0]['name'].lower() in query_artist.lower() and track_info[
                        'name'].lower() in query_title.lower():
                        if i == 0:
                            break
                        else:
                            if len(index) < 1:
                                index.append(i)
                            else:
                                index[0] = i
                    elif track_info['artists'][0]['name'].lower() in query_artist.lower():
                        index.append(i)

                if len(index) > 0:
                    listid = index[0]

            track_info = result['tracks']['items'][listid]
            result_title = track_info['name']
            result_artist = track_info['artists'][0]['name']  # Take the first artist

            # result_album = track_info['album']['name']
            # if len(track_info['artists']) > 1 and track_info['artists'][1]['name'].lower() in query.lower() and track_info['artists'][1]['name'].lower() not in result_title.lower():
            #     result_artist += ' ' + track_info['artists'][1]['name']
            # if clean_string(result_album.split(',')[0]) in query.lower() and clean_string(result_album.split(',')[0]) not in result_title.lower():
            #     mixed_result = result_artist + " - " + result_title + " - " + result_album.split(',')[0]
            # else:

            mixed_result = result_artist + " - " + result_title
            mixed_title = query_artist + " - " + query_title
            if token_based_similarity(mixed_title, mixed_result, min_similarity=min_similarity, max_similarity=max_similarity):
                return track_info['id']
        else:
            return search_spotify_track(sp, query_title)

    return None
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

    # Fetch tracks in batches of 100
    while True:
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