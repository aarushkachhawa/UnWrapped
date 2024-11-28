from calendar import month

import requests
from django.db.models.functions import NullIf
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
import logging
from datetime import datetime, timedelta
from openai import OpenAI
from .localSettings import OPENAI_API_KEY
import json
import os, random
from UnWrapped.models import CustomWrap
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from pydub import AudioSegment
from io import BytesIO
import base64
import librosa
import soundfile as sf
import numpy as np

logger = logging.getLogger(__name__)

# Spotify credentials from settings.py
SPOTIFY_CLIENT_ID = settings.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI
STATICFILES_DIRS = settings.STATICFILES_DIRS
SPOTIFY_SCOPE = 'user-top-read user-read-recently-played user-read-private'  # Add more scopes if needed
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1/me/top/artists"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/me/top/tracks"
SPOTIFY_BASE_URL = "https://api.spotify.com/v1/me"


def logout_view(request):
    language = request.session.get('language', 'english')
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

@login_required
def profile(request):
    if request.method == "POST" and 'language' in request.POST:
        request.session['language'] = request.POST.get('language')

    language = request.session.get('language', 'english')
    context = {
        'username': request.user.get_username(),
        'email': request.user.email,
        'language': language,
        'top_songs': request.session['top_songs'],
        'top_artist': request.session['top_artist'][0],
    }
    return render(request, 'profile.html', context)

def contactDevs(request):
    language = request.session.get('language', 'english')
    return render(request, 'contact.html', {'language': 'english'})

def register(request):
    language = request.session.get('language', 'english')
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
    return render(request, 'register.html', {'form': form, 'hideMenu': False, 'language': language})


def login_view(request):
    language = request.session.get('language', 'english')
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
    return render(request, 'login.html', {'form': form, 'hideMenu': False, 'language': language})


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
    language = request.session.get('language', 'english')
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())
    context = getStats(request)
    context['language'] = language
    return render(request, 'home.html', context)


@login_required
def getStats(request):
    if 'wrappedData' in request.session:
        return request.session[
            'wrappedData']  # the format for request.session['wrappedData'] is {'top_artists': list, 'top_songs': list, 'top_artist_year': string}

    access_token = request.session['spotify_access_token']
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    numTopTracks = 5  # change this to x top tracks you want
    response = requests.get(f"{SPOTIFY_API_URL}?time_range=long_term&limit={numTopTracks}",
                            headers=headers)  # medium_term for 6 months, short_term for 1 month, long_term for 1 year
    trackResponse = requests.get(f"{SPOTIFY_TRACK_URL}?time_range=long_term&limit={numTopTracks}", headers=headers)
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
        return {'top_artists': ["N/A"], 'top_songs': ["N/A"], 'top_artist_year': "N/A", 'top_songs_urls': ["N/A"]}

    try:
        data = response.json()
        artists = data.get('items', [])
        top_artists = [artists[i]['name'] for i in range(min(5, len(artists)))]

        top_artist_year = [
            artists[0]['name'],
            artists[0]['images'][0]['url']
        ]



        top_songs_data = trackResponse.json()
        songs = top_songs_data.get('items', [])
        print("songs in getStats():", songs)
        top_songs = [songs[i]['name'] for i in range(min(5, len(songs)))]
        top_songs_urls = [songs[i]['preview_url'] for i in range(min(5, len(songs)))]

        top_songs_artists = []
        for i in range(min(5, len(songs))):
            song = songs[i]
            if 'artists' in song:
                artist_names = [artist.get('name', "Unknown Artist") for artist in song['artists']]
                top_songs_artists.append(", ".join(artist_names))
            else:
                top_songs_artists.append("Unknown Artist")  # Fallback for missing artist info

        print("############################################################   ", top_artist_year[1])

        returnData = {
            'top_artists': top_artists,
            'top_songs': top_songs,
            'top_songs_artists': top_songs_artists,
            'top_artist_year': top_artist_year,
            'top_songs_urls': top_songs_urls
        }
        request.session['wrappedData'] = returnData
        return returnData

    except Exception as e:
        logger.error(f"Error processing Spotify data: {e}")
        messages.error(request, "An error occurred while processing Spotify data.")
        return {'top_artists': ["N/A"], 'top_songs': ["N/A"], 'top_artist_year': "N/A", 'top_songs_urls': ["N/A"]}


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
    language = request.session.get('language', 'english')
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())

    wrappedData = getStats(request)
    songContent = list(zip(wrappedData['top_songs'], wrappedData['top_songs_urls']))
    
    slides = [
        {
            'title': 'Top Artists of the Year',
            'content': wrappedData['top_artists'],
            'additionalData': None
        },
        {
            'title': 'Top Songs of the Year',
            'content': songContent,
            'additionalData': True
        },
        {
            'title': 'Top Artist This Year',
            'content': [wrappedData['top_artist_year']],
            'additionalData': None
        },
    ]

    context = {
        'slides': slides,
        'language': language
    }

    return render(request, 'stats.html', context)


@login_required
def calculate_top_artist_and_songs_slide(request):
    # Fetch Spotify data (top artists and top songs)
    wrapped_data = getStats(request)

    print("top songs: ", wrapped_data['top_songs'])

    request.session['top_artist'] = wrapped_data['top_artist_year']
    request.session['top_songs'] = wrapped_data['top_songs']
    request.session['top_songs_artists'] = wrapped_data['top_songs_artists']
    request.session['image_url'] = wrapped_data['top_artist_year'][1]
    request.session['top_songs_urls'] = wrapped_data['top_songs_urls']
    request.session['top_songs_artists'] = wrapped_data['top_songs_artists']

    print("CALCULATED TOP ARTISTS")


def top_artist_and_songs_slide(request, page='topArtistAndSongs.html', extra_context=None):
    context = {
        'top_artist': request.session['top_artist'],
        'top_songs': request.session['top_songs'],
        'image': request.session['image_url'],
        'top_songs_artists': request.session['top_songs_artists'],
        'top_songs_urls': request.session['top_songs_urls'],
        'language': request.session.get('language', 'english')
    }
    
    if extra_context:
        context.update(extra_context)
    return render(request, page, context)


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
        print(response.text,
              "Error: Couldn't get last 50 songs played from Spotify & some statistics will be impacted.")
        return redirect('home')

    response_json = response.json()
    for track in response_json['items']:
        songs_list.append(track)

    request.session['songs_list'] = songs_list


def calculate_ads(request):
    seconds_in_a_month = 2.628e+6

    last_50_songs = request.session['songs_list']
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

    if ads_minutes > 360:
        ads_minutes = 360

    return ads_minutes


def calculate_get_most_popular_artists(request):
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())

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
            top_3_artists[artist].append(None)  # artist wasn't in the top artists during this time period

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

    artist1 = None
    artist2 = None
    artist3 = None
    count = 1
    for artist in top_3_artists:
        if len(top_3_artists[artist]) != 3:
            top_3_artists[artist].append(None)  # artist wasn't in the top artists during this time period
        if count == 1:
            artist1 = artist
        elif count == 2:
            artist2 = artist
        else:
            artist3 = artist
        count += 1

    # print(top_3_artists)

    request.session['top_3_artists'] = json.dumps(top_3_artists)
    request.session['artist1'] = artist1
    request.session['artist2'] = artist2
    request.session['artist3'] = artist3


def get_most_popular_artists(request, page='slide_2.html', extra_context=None):
    language = request.session.get('language', 'english')
    
    time_labels = {
        'english': [["over the", "last year"], ["over the last", "six months"], ["over the", "last month"]],
        'hindi': [["पिछले", "साल में"], ["पिछले", "छह महीने में"], ["पिछले", "महीने में"]],
        'mandarin': [["过去", "一年"], ["过去", "六个月"], ["过去", "一个月"]]
    }

    ranking_labels = {
        'english': "Ranking",
        'hindi': "स्थान",
        'mandarin': "排名"
    }

    context = {
        'top_3_artists': request.session['top_3_artists'],
        'artist1': request.session['artist1'],
        'artist2': request.session['artist2'],
        'artist3': request.session['artist3'],
        'language': language,
        'time_labels': json.dumps(time_labels[language]),
        'ranking_label': ranking_labels[language]
    }
    
    if extra_context:
        context.update(extra_context)
    return render(request, page, context)


@login_required
def halloween_graph(request):
    return get_most_popular_artists(request, "halloween_graph.html")
def christmas_graph(request):
    return get_most_popular_artists(request, "christmasGraph.html")



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

            artist_id = None
            first = True
            for artist in track["artists"]:
                if first:
                    artist_id = artist["id"]
                    first = False
                artists_list.append(artist["name"])

            songs_list.append({
                "song_name": track["name"],
                "artists": artists_list,
                "artist_id": artist_id
            })

        if response_json['next'] is None:
            break

        tracks_url = response_json['next']

    request.session['top_100_songs'] = songs_list



def calculate_analyze_seasonal_mood(request):
    client = OpenAI(api_key=OPENAI_API_KEY)
    songs_list = request.session['top_100_songs']
    songs = str(songs_list)
    print(songs)
    print('\n\n\n\n\n')

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a music analyst."},
            {"role": "user", "content": "The following 100 songs are the songs a user listened to most frequently this season. Based on the songs listened come with 6 adjectives to describe their taste in music and for each adjective find an example song. Make sure the adjectives are 8 characters in length or smaller. Return the 6 adjectives and their respective example song and artist in the following format: Adjective1*Song Title by Artist*Adjective2*Song Title by Artist* etc. DO NOT return anything besides the 6 adjectives and their respective example song / artist."},
            {"role": "user", "content": songs}
        ]
    )
    
    description = response.choices[0].message.content

    description = description.split('*')

    mood1 = description[0]
    song_artist1 = description[1]
    mood2 = description[2]
    song_artist2 = description[3]
    mood3 = description[4]
    song_artist3 = description[5]
    mood4 = description[6]
    song_artist4 = description[7]
    mood5 = description[8]
    song_artist5 = description[9]
    mood6 = description[10]
    song_artist6 = description[11]

    print(description)

    song1 = song_artist1.split('by')[0].strip()

    print(song1)

    artist_id = None
    for song in songs_list:
        if song['song_name'] == song1:
            artist_id = song['artist_id']
            break

    print(artist_id)

    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    songs_list = []
    response = requests.get(f"https://api.spotify.com/v1/artists/{artist_id}", headers=headers)

    """if response.status_code == 401:
        refresh_token = request.session.get('spotify_refresh_token')
        new_tokens = refresh_spotify_token(refresh_token)
        access_token = new_tokens.get('access_token')
        request.session['spotify_access_token'] = access_token
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(f"{SPOTIFY_BASE_URL}/player/recently-played", headers=headers, params=parameters)
"""
    response_json = response.json()

    print(response_json['images'][0]['url'])

    current_date = datetime.now()
    month = current_date.month

    print("month", month)

    curr_season = None
    # Determine the season based on date ranges
    if (month <= 2 or month == 12):
        curr_season = "winter"
    elif (month <= 5 and month >= 3):
        curr_season = "spring"
    elif (month <= 8 and month >= 6):
        curr_season = "summer"
    else:
        curr_season = "autumn"

    request.session['mood1'] = mood1
    request.session['mood2'] = mood2
    request.session['mood3'] = mood3
    request.session['mood4'] = mood4
    request.session['mood5'] = mood5
    request.session['mood6'] = mood6

    request.session['song_artist1'] = song_artist1
    request.session['song_artist2'] = song_artist2
    request.session['song_artist3'] = song_artist3
    request.session['song_artist4'] = song_artist4
    request.session['song_artist5'] = song_artist5
    request.session['song_artist6'] = song_artist6

    request.session['image'] = response_json['images'][0]['url']
    request.session['season'] = curr_season

def analyze_seasonal_mood(request, page='seasonalMood.html', extra_context=None):
    context = {
        "mood1": request.session['mood1'],
        "mood2": request.session['mood2'],
        "mood3": request.session['mood3'],
        "mood4": request.session['mood4'],
        "mood5": request.session['mood5'],
        "mood6": request.session['mood6'],
        "song_artist1": request.session['song_artist1'],
        "song_artist2": request.session['song_artist2'],
        "song_artist3": request.session['song_artist3'],
        "song_artist4": request.session['song_artist4'],
        "song_artist5": request.session['song_artist5'],
        "song_artist6": request.session['song_artist6'],
        "image": request.session['image'],
        "season": request.session['season'],
        "language": request.session.get('language', 'english')
    }
    if extra_context:
        context.update(extra_context)
    return render(request, page, context)



def calculate_llm_insights_page(request):
    contentArr = analyze_clothing(request)
    mood = contentArr[0].split(": ")[1].lower()
    if mood not in ["restless", "bitersweet", "introspective", "overjoyed", "pensive"]:
        mood = "other"
    rootDir = f"llmInsights/{mood}/"
    imagePath = f"llmInsights/{mood}.png"
    try:
        imageList = [file for file in os.listdir(f"{STATICFILES_DIRS[0]}/llmInsights/{mood}") if
                     file[len(file) - 3:].lower() == "jpg"]
        songPath = rootDir + random.choice(imageList)
    except:
        songPath = "llmInsights/other/" + "2014FHD.jpg"
    request.session['content'] = contentArr
    request.session['mood'] = mood
    request.session['songPath'] = songPath
    request.session['imagePath'] = imagePath


@login_required
def llm_insights_page(request, page='LLMinsights.html', extra_context=None):
    context = {
        'content': request.session['content'],
        'mood': request.session['mood'],
        'songPath': request.session['songPath'],
        'imagePath': request.session['imagePath'],
        'language': request.session.get('language', 'english')
    }
    if extra_context:
        context.update(extra_context)
    return render(request, page, context)

def analyze_clothing(request):
    client = OpenAI(api_key=OPENAI_API_KEY)
    songs = str(request.session['top_100_songs'])
    print(songs)
    print('\n\n\n\n\n')

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a style analyst."},
            {"role": "user",
             "content": "The following 100 songs are the songs a user listened to most frequently recently. Describe their style in the following format (make sure the description is only one word!, the mood can only be Bittersweet, Pensive, Restless, Overjoyed, or Introspective): Mood: description; Relationship Status: description; Favorite Color: description; Favorite Emoji: description. Here is an example of output (make sure not to include ANY other descriptive text or any spaces after the semicolon): Mood: Black/Dark Scheme;Relationship Status: Heartbroken;Favorite Color: Black;Favorite Emoji: Skull"},
            {"role": "user", "content": songs}
        ]
    )

    description = response.choices[0].message
    print(description.content.split(";"))

    return description.content.split(";")


def calculate_night_owl(request):  # combine this into one calculate stats method so we don't need to call get last 50 songs multiple times
    last_50_songs = request.session['songs_list']

    time_list = []
    for song in last_50_songs:
        listening_time = song['played_at'].strip()  # Strip whitespace
        # Replace 'Z' with '+00:00' for UTC
        if listening_time.endswith('Z'):
            listening_time = listening_time[:-1] + '+00:00'
        
        try:
            datetime_obj = datetime.fromisoformat(listening_time)
        except ValueError as e:
            print(f"Error parsing date: {listening_time} - {e}")
            continue  # Skip this song if there's an error
    
        datetime_obj = datetime_obj - timedelta(hours=5)  # Convert from GMT to EST
        time_list.append({
            "hour": (datetime_obj.hour - 5) % 24,  # latest hour is 5 AM
            "minute": datetime_obj.minute,
            "track_length": song["track"]["duration_ms"]
        })

    latest_time = time_list[0]
    for song in time_list:
        if (song["hour"] > latest_time["hour"]) or (
                song["hour"] == latest_time["hour"] and song["minute"] > latest_time["minute"]):
            latest_time = song

    time_ranges = {
        "0-5": 0,
        "6-11": 0,
        "12-17": 0,
        "18-23": 0
    }

    total_time = 0

    for song in time_list:
        hour = song["hour"]
        total_time += song["track_length"]

        if hour + 5 >= 0 and hour + 5 <= 5:
            time_ranges["0-5"] += (song["track_length"])
        elif hour + 5 >= 6 and hour + 5 <= 11:
            time_ranges["6-11"] += (song["track_length"])
        elif hour + 5 >= 12 and hour + 5 <= 17:
            time_ranges["12-17"] += (song["track_length"])
        else:
            time_ranges["18-23"] += (song["track_length"])

    latest_time["hour"] = (latest_time["hour"] + 5) % 24
    #print("latest", latest_time)

    for key in time_ranges:
        time_ranges[key] = round(time_ranges[key] / 60000)
    #print("time per hour range:", time_ranges)

    total_time = round(total_time / 60000)
    #print("total minutes:", total_time)

    hour = latest_time['hour']
    minute = latest_time['minute']
    if hour != 12:
        hour = latest_time['hour'] if latest_time['hour'] < 12 else latest_time['hour'] - 12
        
    degrees_per_min = 360/60
    minute_hand_rotation = minute * degrees_per_min
    
    hour_hand_rotation = 360/12 * hour + 360/12/60 * minute

    print(json.dumps(time_ranges))

    request.session['latest_time'] = f"{hour}:{'0' if latest_time['minute'] < 10 else ''}{latest_time['minute']} {'AM' if latest_time['hour'] < 12 else 'PM'}"
    request.session['time_ranges'] = json.dumps(time_ranges)
    request.session['total_minutes'] = total_time
    request.session['hour_hand_rotation'] = hour_hand_rotation - 90
    request.session['minute_hand_rotation'] = minute_hand_rotation - 90

def night_owl(request):
    language = request.session.get('language', 'english')
    context = {
        "latest_time": request.session['latest_time'],
        'time_ranges': request.session['time_ranges'],
        "total_minutes": request.session['total_minutes'],
        "hour_hand_rotation": request.session['hour_hand_rotation'],
        "minute_hand_rotation": request.session['minute_hand_rotation'],
        "language": language
    }
    return render(request, 'slide_3.html', context)


@login_required
def transition_one(request):
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())
    language = request.session.get('language', 'english')
    try:
        return render(request, 'transitionOne.html', {'language': language})
    except Exception as e:
        logger.error(f"Error in transition view: {e}")
        messages.error(request, "An error occurred while loading the transition page.")
        return redirect('home')

@login_required
def transition_two(request):
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())
    try:
        return render(request, 'transitionTwo.html', {'language': request.session.get('language', 'english')})

    except Exception as e:
        logger.error(f"Error in transition view: {e}")
        messages.error(request, "An error occurred while loading the transition page.")
        return redirect('home')

def calculate_get_account_level(request):
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(f"{SPOTIFY_BASE_URL}", headers=headers)

    if response.status_code == 401:
        refresh_token = request.session.get('spotify_refresh_token')
        new_tokens = refresh_spotify_token(refresh_token)
        access_token = new_tokens.get('access_token')
        request.session['spotify_access_token'] = access_token
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        response = requests.get(f"{SPOTIFY_BASE_URL}", headers=headers)

    if response.status_code != 200:
        print(response.text, "Error: Can't get user's account status.")
        return redirect('home')
    response = response.json()
    print(response['product'])
    if 'product' in response and response['product'] == 'premium':
        request.session['premium'] = True
    else:
        request.session['premium'] = False

    request.session['ads_minutes'] = round(calculate_ads(request))

def get_account_level(request, page='ads_minutes.html', extra_context=None):
    language = request.session.get('language', 'english')
    context = {
        "premium": request.session['premium'],
        "ads_minutes": request.session['ads_minutes'],
        "language": language,
    }
    if extra_context:
        context.update(extra_context)
    return render(request, page, context)

def generate_wrap(request):
    calculate_top_artist_and_songs_slide(request)
    get_last_50_songs(request)
    calculate_get_account_level(request)
    calculate_get_most_popular_artists(request)
    get_recent_top_songs(request)
    calculate_analyze_seasonal_mood(request)
    calculate_llm_insights_page(request)
    calculate_night_owl(request)

    # save to model
    wrap = CustomWrap(
        user = request.user,
        top_artist = request.session['top_artist'],
        top_songs = request.session['top_songs'],
        image_url = request.session['image_url'],
        top_3_artists = request.session['top_3_artists'],
        artist1 = request.session['artist1'],
        artist2 = request.session['artist2'],
        artist3 = request.session['artist3'],
        mood1 = request.session['mood1'],
        mood2=request.session['mood2'],
        mood3=request.session['mood3'],
        mood4=request.session['mood4'],
        mood5=request.session['mood5'],
        mood6=request.session['mood6'],
        song_artist1 = request.session['song_artist1'],
        song_artist2=request.session['song_artist2'],
        song_artist3=request.session['song_artist3'],
        song_artist4=request.session['song_artist4'],
        song_artist5=request.session['song_artist5'],
        song_artist6=request.session['song_artist6'],
        image = request.session['image'],
        season = request.session['season'],
        content = request.session['content'],
        mood = request.session['mood'],
        songPath = request.session['songPath'],
        latest_time = request.session['latest_time'],
        time_ranges = request.session['time_ranges'],
        total_minutes = request.session['total_minutes'],
        hour_hand_rotation = request.session['hour_hand_rotation'],
        minute_hand_rotation = request.session['minute_hand_rotation'],
        premium = request.session['premium'],
        ads_minutes = request.session['ads_minutes'],
    )
    wrap.save()

    return JsonResponse({
        "done": True
    })

def reset(request):
    language = request.session.get('language', 'english')
    if request.method == 'POST':
        username = request.POST.get('username')
        new_password = request.POST.get('new_password')
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            user.password = make_password(new_password)
            user.save()
            messages.success(request, 'Your password has been reset successfully.')
            return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'Username not found.')
            return render(request, 'reset.html', {'hideMenu': False, 'language': language})
    return render(request, 'reset.html', {'hideMenu': False, 'language': language})

def halloween_ads(request):
    context = {'language': request.session.get('language', 'english')}
    return get_account_level(request, 'halloween_ads.html', context)

def halloween_top_artist(request):
    context = {'language': request.session.get('language', 'english')}
    return top_artist_and_songs_slide(request, 'halloweenone.html', context)

def christmas_top_artist(request):
    context = {'language': request.session.get('language', 'english')}
    return top_artist_and_songs_slide(request, 'christmasone.html', context)

def halloween_seasonal(request):
    context = {'language': request.session.get('language', 'english')}
    return analyze_seasonal_mood(request, 'halloween_seasonal.html', context)

def halloween_llm(request):
    context = {'language': request.session.get('language', 'english')}
    return llm_insights_page(request, 'halloween_llm.html', context)

def christmas_seasonal(request):
    context = {'language': request.session.get('language', 'english')}
    return analyze_seasonal_mood(request, 'christmas_seasonal.html', context)

def christmas_llm(request):
    context = {'language': request.session.get('language', 'english')}
    return llm_insights_page(request, 'christmas_llm.html', context)

def past_wraps(request):
    month_to_word_dict = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }

    wraps = CustomWrap.objects.filter(user=request.user)
    wrap_list = []
    for wrap in wraps:
        date_string = ""
        date = wrap.wrapDate.date()
        date_string += month_to_word_dict[date.month]
        date_string += f" {date.day}, {date.year}"

        wrap_list.append(
            {
                'id': wrap.id,
                'words': date_string,
            }
        )

    context = {
        "wrap_list": wrap_list,
        "num_wraps": len(wrap_list),
    }

    return render(request, 'past_wraps.html', context)

def game_mix_pitch_1(request):
    language = request.session.get('language', 'english')
    access_token = request.session.get('spotify_access_token')

    if not access_token:
        return render(request, 'game_mix_pitch.html', {'error': 'Spotify access token not found. Please log in again.'})

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Fetch the user's top tracks
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=50"
    response = requests.get(top_tracks_url, headers=headers)

    if response.status_code != 200:
        return render(request, 'game_mix_pitch.html', {'error': 'Failed to fetch top tracks from Spotify. Please try again later.'})

    top_tracks = response.json().get('items', [])

    if len(top_tracks) < 12:
        return render(request, 'game_mix_pitch.html', {'error': 'Not enough top tracks to play the game. Listen to more songs on Spotify!'})

    # Step 2: Pick two random tracks for mixing
    try:
        track1, track2 = random.sample(top_tracks, 2)
        track1_name = track1.get('name')
        track2_name = track2.get('name')
        track1_preview_url = track1.get('preview_url')
        track2_preview_url = track2.get('preview_url')

        if not track1_preview_url or not track2_preview_url:
            return render(request, 'game_mix_pitch.html', {'error': 'One or both tracks are missing preview URLs. Please try again.'})

        # Step 3: Select 8 additional unique tracks for multiple-choice options
        additional_tracks = random.sample([track for track in top_tracks if track != track1 and track != track2], 10)
        additional_names = [track.get('name') for track in additional_tracks]

        # Ensure the correct songs are included in the choices
        song_choices = [track1_name, track2_name] + additional_names
        random.shuffle(song_choices)  # Shuffle the order of options

        # Step 4: Process audio
        sr = 22050
        audio1, _ = librosa.load(BytesIO(requests.get(track1_preview_url).content), sr=sr, mono=True)
        audio2, _ = librosa.load(BytesIO(requests.get(track2_preview_url).content), sr=sr, mono=True)

        chroma1 = librosa.feature.chroma_cqt(y=audio1, sr=sr)
        chroma2 = librosa.feature.chroma_cqt(y=audio2, sr=sr)

        chroma_mean1 = np.mean(chroma1, axis=1)
        chroma_mean2 = np.mean(chroma2, axis=1)

        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key1_index = np.argmax(chroma_mean1)
        key2_index = np.argmax(chroma_mean2)
        key1 = notes[key1_index]
        key2 = notes[key2_index]

        semitone_shift = key2_index - key1_index

        # Adjust the pitch of audio1 to match audio2's key
        audio1_adjusted = librosa.effects.pitch_shift(audio1, sr=sr, n_steps=semitone_shift)

        # Make the volume of audio1 20% louder after pitch shifting
        if semitone_shift < 0:
            audio1_adjusted = audio1_adjusted * 1.2
        else:
            audio1_adjusted = audio1_adjusted * 0.9

        # Calculate RMS to match overall volume levels
        rms1 = np.sqrt(np.mean(audio1_adjusted**2))
        rms2 = np.sqrt(np.mean(audio2**2))
        if rms1 > 0:
            audio1_adjusted = audio1_adjusted * (rms2 / rms1)

        # Align lengths and mix tracks
        min_length = min(len(audio1_adjusted), len(audio2))
        mixed_audio = (audio1_adjusted[:min_length] + audio2[:min_length]) / 2

        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed_audio))
        if max_val > 0:
            mixed_audio = mixed_audio / max_val

        # Save the mixed audio to a buffer
        mixed_audio_buffer = BytesIO()
        sf.write(mixed_audio_buffer, mixed_audio, sr, format='WAV')
        mixed_audio_buffer.seek(0)
        mixed_audio_base64 = base64.b64encode(mixed_audio_buffer.read()).decode('utf-8')

    except Exception as e:
        return render(request, 'game_mix_pitch.html', {'error': f'Error during audio processing: {e}'})

    # Step 5: Render the template
    context = {
        'mixed_audio': mixed_audio_base64,

        'song_choices': song_choices,
        'correct_songs': [track1_name, track2_name],
        'language': language
    }
    return render(request, 'game_mix_pitch.html', context)


def game_mix_pitch_2(request):
    language = request.session.get('language', 'english')
    access_token = request.session.get('spotify_access_token')

    if not access_token:
        return render(request, 'game_mix_pitch.html', {'error': 'Spotify access token not found. Please log in again.'})

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Fetch the user's top tracks
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=50"
    response = requests.get(top_tracks_url, headers=headers)

    if response.status_code != 200:
        return render(request, 'game_mix_pitch.html', {'error': 'Failed to fetch top tracks from Spotify. Please try again later.'})

    top_tracks = response.json().get('items', [])

    # **Change 1:** Update minimum number of top tracks to accommodate three correct songs + decoys
    num_correct = 3
    decoy_count = 13  # To maintain 16 total choices
    required_tracks = num_correct + decoy_count

    if len(top_tracks) < required_tracks:
        return render(request, 'game_mix_pitch.html', {'error': 'Not enough top tracks to play the game. Listen to more songs on Spotify!'})

    # Step 2: Pick three unique tracks for mixing
    try:
        # **Change 2:** Select three unique tracks
        selected_tracks = random.sample(top_tracks, num_correct)
        base_track, pitch_track_up, pitch_track_down = selected_tracks

        base_track_name = base_track.get('name')
        pitch_track_up_name = pitch_track_up.get('name')
        pitch_track_down_name = pitch_track_down.get('name')

        base_preview_url = base_track.get('preview_url')
        pitch_preview_url_up = pitch_track_up.get('preview_url')
        pitch_preview_url_down = pitch_track_down.get('preview_url')

        # **Change 3:** Ensure all three tracks have preview URLs
        if not base_preview_url or not pitch_preview_url_up or not pitch_preview_url_down:
            return render(request, 'game_mix_pitch.html', {'error': 'One or more tracks are missing preview URLs. Please try again.'})

        # Step 3: Select 13 additional unique tracks for multiple-choice options
        remaining_tracks = [track for track in top_tracks if track not in selected_tracks]
        decoy_tracks = random.sample(remaining_tracks, decoy_count)
        decoy_song_names = [track.get('name') for track in decoy_tracks]

        # **Change 4:** Include three correct song names in choices
        song_choices = [base_track_name, pitch_track_up_name, pitch_track_down_name] + decoy_song_names
        random.shuffle(song_choices)  # Shuffle the order of options

        # Step 4: Process audio
        sr = 22050  # Sampling rate

        # **Change 5:** Load all three audio tracks
        audio_base, _ = librosa.load(BytesIO(requests.get(base_preview_url).content), sr=sr, mono=True)
        audio_up, _ = librosa.load(BytesIO(requests.get(pitch_preview_url_up).content), sr=sr, mono=True)
        audio_down, _ = librosa.load(BytesIO(requests.get(pitch_preview_url_down).content), sr=sr, mono=True)

        # Extract chroma features to determine the key of each track
        chroma_base = librosa.feature.chroma_cqt(y=audio_base, sr=sr)
        chroma_up = librosa.feature.chroma_cqt(y=audio_up, sr=sr)
        chroma_down = librosa.feature.chroma_cqt(y=audio_down, sr=sr)

        chroma_mean_base = np.mean(chroma_base, axis=1)
        chroma_mean_up = np.mean(chroma_up, axis=1)
        chroma_mean_down = np.mean(chroma_down, axis=1)

        notes = ['C', 'C#', 'D', 'D#', 'E', 'F',
                 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key_base_index = np.argmax(chroma_mean_base)
        key_up_index = np.argmax(chroma_mean_up)
        key_down_index = np.argmax(chroma_mean_down)
        key_base = notes[key_base_index]
        key_up = notes[key_up_index]
        key_down = notes[key_down_index]

        # Step 4.1: Set the base key as the target key
        target_key_index = key_base_index
        target_key = key_base

        # Calculate the semitone shifts needed for pitch_track_up and pitch_track_down to match the base key
        semitone_shift_up = target_key_index - key_up_index
        semitone_shift_down = target_key_index - key_down_index

        # **Change 6:** Pitch one song up and one song down to match the base key
        audio_up_adjusted = librosa.effects.pitch_shift(audio_up, sr=sr, n_steps=semitone_shift_up)
        audio_down_adjusted = librosa.effects.pitch_shift(audio_down, sr=sr, n_steps=semitone_shift_down)
        audio_base_adjusted = librosa.effects.pitch_shift(audio_base, sr=sr, n_steps=12)  # No shift needed for base track

        # **Change 7:** Adjust volumes
        # Increase volume slightly for pitched-down song and decrease volume slightly for pitched-up song
        volume_increase_factor = 1.4  # 5% increase
        volume_decrease_factor = 0.9  # 5% decrease

        audio_down_adjusted *= volume_increase_factor
        audio_up_adjusted *= volume_decrease_factor
        audio_base *= 0.8
        # audio_base_adjusted remains unchanged

        # Step 4.2: Normalize the volume of all tracks to prevent clipping and ensure balance
        def normalize_audio(audio):
            rms = np.sqrt(np.mean(audio**2))
            if rms > 0:
                return audio / rms
            return audio

        audio_base_normalized = normalize_audio(audio_base_adjusted)
        audio_up_normalized = normalize_audio(audio_up_adjusted)
        audio_down_normalized = normalize_audio(audio_down_adjusted)

        # Step 4.3: Align lengths by padding shorter audios with zeros
        max_length = max(len(audio_base_normalized),
                         len(audio_up_normalized),
                         len(audio_down_normalized))

        def pad_audio(audio, target_length):
            if len(audio) < target_length:
                return np.pad(audio, (0, target_length - len(audio)), 'constant')
            return audio[:target_length]

        audio_base_padded = pad_audio(audio_base_normalized, max_length)
        audio_up_padded = pad_audio(audio_up_normalized, max_length)
        audio_down_padded = pad_audio(audio_down_normalized, max_length)

        # Step 4.4: Mix all three tracks together by averaging
        mixed_audio = (audio_base_padded + audio_up_padded + audio_down_padded) / 3

        # Normalize to prevent clipping
        max_val = np.max(np.abs(mixed_audio))
        if max_val > 0:
            mixed_audio = mixed_audio / max_val

        # **Optional:** Use only a snippet of the mixed audio (e.g., 15 seconds)
        snippet_duration_seconds = 15  # Duration of the snippet in seconds
        snippet_length = int(snippet_duration_seconds * sr)
        if len(mixed_audio) > snippet_length:
            start = random.randint(0, len(mixed_audio) - snippet_length)
            mixed_audio = mixed_audio[start:start + snippet_length]

        # **Change 8:** Save the mixed audio to a buffer
        mixed_audio_buffer = BytesIO()
        sf.write(mixed_audio_buffer, mixed_audio, sr, format='WAV')
        mixed_audio_buffer.seek(0)
        mixed_audio_base64 = base64.b64encode(
            mixed_audio_buffer.read()).decode('utf-8')

    except Exception as e:
        return render(request, 'game_mix_pitch.html', {'error': f'Error during audio processing: {e}'})

    # Step 5: Render the template
    context = {
        'mixed_audio': mixed_audio_base64,
        'song_choices': song_choices,
        'correct_songs': [base_track_name, pitch_track_up_name, pitch_track_down_name],
        'random_key': target_key,
        'language': language
    }
    return render(request, 'game_mix_pitch.html', context)


def wrap_id_to_session(request):
    body = json.loads(request.body)
    wrap_id = body['wrap_id']
    wrap = CustomWrap.objects.filter(id=wrap_id).first()
    print('\n\n\n\n', wrap)

    without_brackets = wrap.top_artist[1:-1]
    print(without_brackets)

    without_brackets = without_brackets.split(', ')
    without_brackets[0] = without_brackets[0][1:-1]
    without_brackets[1] = without_brackets[1][1:-1]
    print(type(without_brackets))
    request.session['top_artist'] = without_brackets
    request.session['top_songs'] = wrap.top_songs
    request.session['image_url'] = wrap.image_url
    request.session['top_3_artists'] = wrap.top_3_artists
    request.session['artist1'] = wrap.artist1
    request.session['artist2'] = wrap.artist2
    request.session['artist3'] = wrap.artist3
    request.session['mood1'] = wrap.mood1
    request.session['mood2'] = wrap.mood2
    request.session['mood3'] = wrap.mood3
    request.session['mood4'] = wrap.mood4
    request.session['mood5'] = wrap.mood5
    request.session['mood6'] = wrap.mood6
    request.session['song_artist1'] = wrap.song_artist1
    request.session['song_artist2'] = wrap.song_artist2
    request.session['song_artist3'] = wrap.song_artist3
    request.session['song_artist4'] = wrap.song_artist4
    request.session['song_artist5'] = wrap.song_artist5
    request.session['song_artist6'] = wrap.song_artist6
    request.session['image'] = wrap.image
    request.session['season'] = wrap.season

    content_without_brackets = wrap.content[1:-1]
    print(content_without_brackets)

    content_without_brackets = content_without_brackets.split(', ')
    content_without_brackets[0] = content_without_brackets[0][1:-1]
    content_without_brackets[1] = content_without_brackets[1][1:-1]
    content_without_brackets[2] = content_without_brackets[2][1:-1]
    content_without_brackets[3] = content_without_brackets[3][1:-1]
    print(type(content_without_brackets))

    request.session['content'] = content_without_brackets
    request.session['mood'] = wrap.mood
    request.session['songPath'] = wrap.songPath
    request.session['latest_time'] = wrap.latest_time
    request.session['time_ranges'] = wrap.time_ranges
    request.session['total_minutes'] = wrap.total_minutes
    request.session['hour_hand_rotation'] = wrap.hour_hand_rotation
    request.session['minute_hand_rotation'] = wrap.minute_hand_rotation
    request.session['premium'] = wrap.premium
    request.session['ads_minutes'] = wrap.ads_minutes
    return JsonResponse({})
