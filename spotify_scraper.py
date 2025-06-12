import requests
import base64
import time

# --- API CONSTANTS ---
SPOTIFY_API_URL = 'https://api.spotify.com/v1'
SPOTIFY_TOKEN_URL = 'https://accounts.spotify.com/api/token'

# --- In-memory cache for the access token ---
_cached_token = None
_token_expiry_time = 0

def get_spotify_access_token(client_id, client_secret):
    """
    Retrieves a Spotify API access token, using a cache if possible.
    """
    global _cached_token, _token_expiry_time

    # Return cached token if it's still valid
    if _cached_token and time.time() < _token_expiry_time:
        return _cached_token

    # --- Request a new token ---
    auth_header = base64.b64encode(f"{client_id}:{client_secret}".encode('ascii')).decode('ascii')
    headers = {'Authorization': f'Basic {auth_header}'}
    payload = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post(SPOTIFY_TOKEN_URL, headers=headers, data=payload)
        response.raise_for_status()  # Raise an exception for bad status codes
        token_data = response.json()

        # Cache the new token and calculate its expiry time (with a 60s buffer)
        _cached_token = token_data['access_token']
        _token_expiry_time = time.time() + token_data['expires_in'] - 60
        
        return _cached_token

    except requests.exceptions.RequestException as e:
        print(f"Error getting Spotify access token: {e}")
        return None

def get_all_tracks(artist_url, client_id, client_secret):
    """
    Gets all tracks for a given artist using the Spotify API.

    Args:
        artist_url (str): The URL of the Spotify artist page.
        client_id (str): Your Spotify client ID.
        client_secret (str): Your Spotify client secret.

    Returns:
        list: A list of tuples, where each tuple contains (track_name, track_url).
              Returns an empty list if an error occurs.
    """
    # 1. Get Access Token
    token = get_spotify_access_token(client_id, client_secret)
    if not token:
        return []

    # 2. Extract Artist ID from URL
    try:
        artist_id = artist_url.split('/artist/')[1].split('?')[0]
    except IndexError:
        print(f"Invalid Spotify Artist URL: {artist_url}")
        return []

    # 3. Fetch Artist's most recent albums and singles
    headers = {'Authorization': f'Bearer {token}'}
    api_url = f'{SPOTIFY_API_URL}/artists/{artist_id}/albums'
    params = {
        'include_groups': 'album,single',
        'limit': 20 # Check the 20 most recent releases
    }
    
    recent_albums = []
    try:
        response = requests.get(api_url, headers=headers, params=params)
        response.raise_for_status()
        album_data = response.json()
        recent_albums = album_data.get('items', [])
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching artist albums: {e}")
        return []

    # 4. Fetch the tracks for each of those recent releases
    all_tracks = []
    processed_track_urls = set() # Avoid duplicates if a track appears on a single and an album

    for album in recent_albums:
        album_id = album.get('id')
        if not album_id:
            continue
        
        tracks_api_url = f'{SPOTIFY_API_URL}/albums/{album_id}/tracks'
        try:
            response = requests.get(tracks_api_url, headers=headers)
            response.raise_for_status()
            tracks_data = response.json()

            for track in tracks_data.get('items', []):
                track_url = track.get('external_urls', {}).get('spotify')
                track_name = track.get('name')

                if track_name and track_url and track_url not in processed_track_urls:
                    all_tracks.append((track_name, track_url))
                    processed_track_urls.add(track_url)

        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching tracks for album {album_id}: {e}")
            continue # Move to the next album

    return all_tracks
