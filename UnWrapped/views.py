import requests
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
import logging
from datetime import datetime
from openai import OpenAI
from .localSettings import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Spotify credentials from settings.py
SPOTIFY_CLIENT_ID = settings.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI
SPOTIFY_SCOPE = 'user-top-read user-read-recently-played'  # Add more scopes if needed
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1/me/top/artists"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/me/top/tracks"
SPOTIFY_BASE_URL = "https://api.spotify.com/v1/me"

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('login')
        else:
            print(form.errors)
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Successfully logged in")
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


# Helper function to get Spotify tokens
def get_spotify_tokens(code):
    data = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': SPOTIFY_REDIRECT_URI,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    try:
        return response.json()
    except:
        return {}


# Helper function to refresh the Spotify token (if needed)
def refresh_spotify_token(refresh_token):
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': SPOTIFY_CLIENT_ID,
        'client_secret': SPOTIFY_CLIENT_SECRET,
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    response = requests.post(SPOTIFY_TOKEN_URL, data=data, headers=headers)
    return response.json()


# Spotify authorization URL
def spotify_auth_url():
    auth_url = (
        f"https://accounts.spotify.com/authorize?client_id={SPOTIFY_CLIENT_ID}&response_type=code"
        f"&redirect_uri={SPOTIFY_REDIRECT_URI}&scope={SPOTIFY_SCOPE}"
    )
    return auth_url

@login_required
def home(request):
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())

    access_token = request.session['spotify_access_token']
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    numTopTracks = 5 # change this to x top tracks you want
    response = requests.get(SPOTIFY_API_URL, headers=headers)
    trackResponse = requests.get(f"{SPOTIFY_TRACK_URL}?time_range=short_term&limit={numTopTracks}", headers=headers)
    if response.status_code == 401 or trackResponse.status_code == 401:
        refresh_token = request.session.get('spotify_refresh_token')
        new_tokens = refresh_spotify_token(refresh_token)
        access_token = new_tokens.get('access_token')
        request.session['spotify_access_token'] = access_token
        headers["Authorization"] = f"Bearer {access_token}"
        response = requests.get(SPOTIFY_API_URL, headers=headers)

    if response.status_code != 200 or trackResponse.status_code != 200:
        logger.error(f"Spotify API request failed: {response.status_code} - {response.text}")
        messages.error(request, "Failed to retrieve data from Spotify.")
        return render(request, 'home.html', {'top_artists': ["N/A"], 'top_songs': ["N/A"], 'top_artist_month': "N/A"})


    try:
        data = response.json()
        artists = data.get('items', [])
        top_artists = [artists[i]['name'] for i in range(min(5, len(artists)))]
        top_songs_data = trackResponse.json()
        songs = top_songs_data.get('items', [])
        top_songs = [songs[i]['name'] for i in range(min(5, len(songs)))]

        context = {
            'top_artists': top_artists,
            'top_songs': top_songs,
            'top_artist_month': top_artists[0] if top_artists else "Unknown",
        }
        return render(request, 'home.html', context)
    except Exception as e:
        logger.error(f"Error processing Spotify data: {e}")
        messages.error(request, "An error occurred while processing Spotify data.")
        return render(request, 'home.html', {'top_artists': ["N/A"], 'top_songs': ["N/A"], 'top_artist_month': "N/A"})



def spotify_callback(request):
    # After user authorizes Spotify, they are redirected back to this view with a code
    code = request.GET.get('code')
    tokens = get_spotify_tokens(code)

    # Store access and refresh tokens in the session
    if tokens != {}:
        request.session['spotify_access_token'] = tokens.get('access_token')
        request.session['spotify_refresh_token'] = tokens.get('refresh_token')

    return redirect('home')


@login_required
def stats(request):
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())

    # Example Spotify data in the stats page
    top_artists = request.session.get('spotify_top_artists', [])
    top_songs = request.session.get('spotify_top_songs', [])

    slides = [
        {
            'title': 'Top Artists of the Year',
            'content': top_artists,
        },
        {
            'title': 'Top Songs of the Year',
            'content': top_songs,
        },
    ]

    context = {
        'slides': slides
    }

    return render(request, 'stats.html', context)


@login_required
def get_last_50_songs(request):
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    parameters = {
        "limit": 50
    }

    songs_list = []
    response = requests.get(f"{SPOTIFY_BASE_URL}/player/recently-played", headers=headers, params=parameters)

    if response.status_code == 401:
        refresh_token = request.session.get('spotify_refresh_token')
        new_tokens = refresh_spotify_token(refresh_token)
        access_token = new_tokens.get('access_token')
        request.session['spotify_access_token'] = access_token
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(f"{SPOTIFY_BASE_URL}/player/recently-played", headers=headers, params=parameters)

    if response.status_code != 200:
        print(response.text, "Error: Couldn't get last 50 songs played from Spotify & some statistics will be impacted.")
        return redirect('home')

    response_json = response.json()
    for track in response_json['items']:
        songs_list.append(track)

    return songs_list


def calculate_ads(request):
    seconds_in_a_month = 2.628e+6

    last_50_songs = get_last_50_songs(request) # we should make this only get called once when stats are calculated, for now tho we'll call it again here
    oldest_time = datetime.fromisoformat(last_50_songs[-1]['played_at'][:-1])
    newest_time = datetime.fromisoformat(last_50_songs[0]['played_at'][:-1])
    time_dif = newest_time - oldest_time
    print(oldest_time, newest_time)
    multiplier = seconds_in_a_month / time_dif.total_seconds()

    total_listening_time = 0
    for song in last_50_songs:
        total_listening_time += song['track']['duration_ms']

    print(total_listening_time)

    total_listening_hours = total_listening_time / 3.6e+6
    listening_hours_for_a_month = total_listening_hours * multiplier
    ads_minutes = listening_hours_for_a_month * 3

    print(ads_minutes)
    return redirect('home')

def get_most_popular_artists(request):
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    parameters = {
        "limit": 3,
        "time_range": "long_term"
    }

    top_3_artists = {}
    response = requests.get(f"{SPOTIFY_BASE_URL}/top/artists", headers=headers, params=parameters)

    if response.status_code == 401:
        refresh_token = request.session.get('spotify_refresh_token')
        new_tokens = refresh_spotify_token(refresh_token)
        access_token = new_tokens.get('access_token')
        request.session['spotify_access_token'] = access_token
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(f"{SPOTIFY_BASE_URL}/top/artists", headers=headers, params=parameters)

    if response.status_code != 200:
        print(response.text, "Error: Couldn't get top artists from Spotify & some statistics will be impacted.")
        return redirect('home')

    response_json = response.json()
    count = 1
    for artist in response_json['items']:
        top_3_artists[artist["name"]] = [count]
        count += 1

    # get the top 3 overall artists' positions in the last ~6 months
    num_found = 0
    parameters["time_range"] = "medium_term"
    parameters["limit"] = 50
    medium_url = f"{SPOTIFY_BASE_URL}/top/artists"

    while num_found < 3 and medium_url is not None:
        response = requests.get(medium_url, headers=headers, params=parameters)

        if response.status_code == 401:
            refresh_token = request.session.get('spotify_refresh_token')
            new_tokens = refresh_spotify_token(refresh_token)
            access_token = new_tokens.get('access_token')
            request.session['spotify_access_token'] = access_token
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.get(medium_url, headers=headers, params=parameters)

        if response.status_code != 200:
            print(response.text, "Error: Couldn't get top artists from Spotify & some statistics will be impacted.")
            return redirect('home')

        response_json = response.json()
        count = 1
        for artist in response_json['items']:
            if artist['name'] in top_3_artists.keys():
                top_3_artists[artist['name']].append(count)
                num_found += 1
            count += 1

            if num_found == 3:
                break

        medium_url = response_json["next"]

    for artist in top_3_artists:
        if len(top_3_artists[artist]) != 2:
            top_3_artists[artist].append(None) # artist wasn't in the top artists during this time period

    # get the rankings of the artists in the last ~1 month
    num_found = 0
    parameters["time_range"] = "short_term"
    parameters["limit"] = 50
    short_url = f"{SPOTIFY_BASE_URL}/top/artists"

    while num_found < 3 and short_url is not None:
        response = requests.get(short_url, headers=headers, params=parameters)

        if response.status_code == 401:
            refresh_token = request.session.get('spotify_refresh_token')
            new_tokens = refresh_spotify_token(refresh_token)
            access_token = new_tokens.get('access_token')
            request.session['spotify_access_token'] = access_token
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.get(short_url, headers=headers, params=parameters)

        if response.status_code != 200:
            print(response.text, "Error: Couldn't get top artists from Spotify & some statistics will be impacted.")
            return redirect('home')

        response_json = response.json()
        count = 1
        for artist in response_json['items']:
            if artist['name'] in top_3_artists.keys():
                top_3_artists[artist['name']].append(count)
                num_found += 1
            count += 1

            if num_found == 3:
                break

        short_url = response_json["next"]

    for artist in top_3_artists:
        if len(top_3_artists[artist]) != 3:
            top_3_artists[artist].append(None)  # artist wasn't in the top artists during this time period

    print(top_3_artists)
    return JsonResponse(top_3_artists)

# used for your seasonal mood (get top 100 songs in the last ~1 month), gets top 100 songs and the artists
def get_recent_top_songs(request):
    tracks_url = f"{SPOTIFY_BASE_URL}/top/tracks"
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    parameters = {
        "limit": 50
    }

    songs_list = []

    for i in range(2):
        response = requests.get(tracks_url, headers=headers, params=parameters)

        if response.status_code == 401:
            refresh_token = request.session.get('spotify_refresh_token')
            new_tokens = refresh_spotify_token(refresh_token)
            access_token = new_tokens.get('access_token')
            request.session['spotify_access_token'] = access_token
            headers = {
                "Authorization": f"Bearer {access_token}"
            }
            response = requests.get(tracks_url, headers=headers, params=parameters)

        if response.status_code != 200:
            print(response.text,
                  "Error: Couldn't get top 100 songs from Spotify & some statistics will be impacted.")
            return redirect('home')

        response_json = response.json()
        for track in response_json['items']:
            artists_list = []
            for artist in track["artists"]:
                artists_list.append(artist["name"])
            songs_list.append({
                "song_name": track["name"],
                "artists": artists_list,
            })

        if response_json['next'] is None:
            break

        tracks_url = response_json['next']

    return songs_list

def analyze_seasonal_mood(request):
    client = OpenAI(api_key=OPENAI_API_KEY)
    songs = str(get_recent_top_songs(request))
    print(songs)
    print('\n\n\n\n\n')

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a music analyst."},
            {"role": "user", "content": "The following 100 songs are the songs a user listened to most frequently this season. Describe the music they listened to using 6 adjectives and give an example song for each adjective from their top 100 songs. Follow this format for all 6 adjectives/moods: Mood: Song Title by Artist"},
            {"role": "user", "content": songs}
        ]
    )
    
    description = response.choices[0].message
    print(description)

    return HttpResponse(description)