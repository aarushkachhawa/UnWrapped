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
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

@login_required
def profile(request):
    context = {
        'username': request.user.get_username(),
        'email': request.user.email
    }
    return render(request, 'profile.html', context)

def contactDevs(request):
    return render(request, 'contact.html', {})

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
    context = getStats(request)
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
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())

    wrappedData = getStats(request)

    # Example Spotify data in the stats page
    songContent = list(zip(wrappedData['top_songs'], wrappedData['top_songs_urls']))

    print(songContent)

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
            # top_artist_year is a single value and the slides expect a list
            'additionalData': None
        },
    ]

    context = {
        'slides': slides
    }

    return render(request, 'stats.html', context)


@login_required
def top_artist_and_songs_slide(request):
    # Fetch Spotify data (top artists and top songs)
    wrapped_data = getStats(request)

    print("top songs: ", wrapped_data['top_songs'])

    context = {
        'title': 'Top Artist and Top Songs of the Year',
        'top_artist': wrapped_data['top_artist_year'],
        'top_songs': wrapped_data['top_songs'],
        'top_songs_artists': wrapped_data['top_songs_artists'],
    }

    # Render a single template with both top artist and top songs
    return render(request, 'topArtistAndSongs.html', context)


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

    return songs_list


def calculate_ads(request):
    seconds_in_a_month = 2.628e+6

    last_50_songs = get_last_50_songs(
        request)  # we should make this only get called once when stats are calculated, for now tho we'll call it again here
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
        ads_minutes = "over 360"

    return ads_minutes


def get_most_popular_artists(request, page = "slide_2.html"):
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

    context = {
        'top_3_artists': json.dumps(top_3_artists),
        'artist1': artist1,
        'artist2': artist2,
        'artist3': artist3,
    }
    return render(request, page, context)

@login_required
def halloween_graph(request):
    return get_most_popular_artists(request, "halloween_graph.html")


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

    return songs_list


def analyze_seasonal_mood(request):
    client = OpenAI(api_key=OPENAI_API_KEY)
    songs_list = get_recent_top_songs(request)
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


    context = {
        "mood1" : mood1,
        "mood2" : mood2,
        "mood3" : mood3,
        "mood4" : mood4,
        "mood5" : mood5,
        "mood6" : mood6,
        "song_artist1" : song_artist1,
        "song_artist2" : song_artist2,
        "song_artist3" : song_artist3,
        "song_artist4" : song_artist4,
        "song_artist5" : song_artist5,
        "song_artist6" : song_artist6,
        "image" : response_json['images'][0]['url'],
        "season" : curr_season,
    }

    return render(request, 'seasonalMood.html', context)




@login_required
def llm_insights_page(request):
    contentArr = analyze_clothing(request)
    mood = contentArr[0].split(": ")[1].lower()
    if mood not in ["restless", "bitersweet", "introspective", "overjoyed", "pensive"]:
        mood = "other"
    rootDir = f"llmInsights/{mood}/"
    try:
        imageList = [file for file in os.listdir(f"{STATICFILES_DIRS[0]}/llmInsights/{mood}") if file[len(file) - 3:].lower() == "jpg"]
        songPath = rootDir + random.choice(imageList)
    except:
        songPath = "llmInsights/other/" + "2014FHD.jpg"
    context = { # send mood in separately because of how horrible django's template functionality is :)
        'content': contentArr,
        'mood': mood,
        'songPath': songPath,
    }
    return render(request, 'LLMinsights.html', context)


def analyze_clothing(request):
    client = OpenAI(api_key=OPENAI_API_KEY)
    songs = str(get_recent_top_songs(request))
    print(songs)
    print('\n\n\n\n\n')

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
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


def night_owl(request):  # combine this into one calculate stats method so we don't need to call get last 50 songs multiple times
    last_50_songs = get_last_50_songs(request)

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

    context = {
        "latest_time": f"{hour}:{'0' if latest_time['minute'] < 10 else ''}{latest_time['minute']} {'AM' if latest_time['hour'] < 12 else 'PM'}",
        'time_ranges': json.dumps(time_ranges),
        "total_minutes": total_time,
        "hour_hand_rotation": hour_hand_rotation - 90,
        "minute_hand_rotation": minute_hand_rotation - 90,
    }
    
    print(context['time_ranges'])
    return render(request, 'slide_3.html', context)


@login_required
def transition_one(request):
    """
    Renders the transition page with music player animation.
    """
    if 'spotify_access_token' not in request.session:
        return redirect(spotify_auth_url())

    try:
        return render(request, 'transitionOne.html')

    except Exception as e:
        logger.error(f"Error in transition view: {e}")
        messages.error(request, "An error occurred while loading the transition page.")
        return redirect('home')

def get_account_level(request):
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
    if response['product'] == 'premium':
        premium = True
    else:
        premium = False

    #print(premium)

    context = {
        "premium": premium,
        "ads_minutes": round(calculate_ads(request)),
    }

    return render(request, 'ads_minutes.html', context)


def reset(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        new_password = request.POST.get('new_password')

        # Use get_user_model() to get the custom user model
        User = get_user_model()

        try:
            # Find user by username
            user = User.objects.get(username=username)

            # Update the password and hash it
            user.password = make_password(new_password)
            user.save()

            # Redirect or show success message
            messages.success(request, 'Your password has been reset successfully.')
            return redirect('login')  # Redirect to login page after resetting password

        except User.DoesNotExist:
            # Handle case where the username is not found
            messages.error(request, 'Username not found.')
            return render(request, 'reset.html')

    return render(request, 'reset.html')


def remove_vocals_phase_inversion(audio, sr):
    """
    Attempts to remove vocals from a stereo audio signal using phase inversion.

    Parameters:
    - audio: numpy array with shape (2, n_samples)
    - sr: sample rate

    Returns:
    - accompaniment: numpy array with shape (n_samples,)
    """
    if audio.ndim != 2 or audio.shape[0] != 2:
        raise ValueError("Audio must be a stereo signal with shape (2, n_samples).")

    left_channel = audio[0]
    right_channel = audio[1]

    # Invert the right channel
    inverted_right = -right_channel

    # Combine channels to remove vocals
    accompaniment = left_channel + inverted_right

    # Normalize the accompaniment to prevent clipping
    max_val = np.max(np.abs(accompaniment))
    if max_val > 0:
        accompaniment = accompaniment / max_val

    return accompaniment


def game(request):
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Fetch the user's top tracks
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=10"
    response = requests.get(top_tracks_url, headers=headers)

    if response.status_code != 200:
        return redirect('home')

    top_tracks = response.json().get('items', [])

    if len(top_tracks) < 2:
        return redirect('home')

    # Step 2: Pick two random tracks from the top 10
    track1, track2 = random.sample(top_tracks, 2)

    track1_preview_url = track1.get('preview_url')
    track2_preview_url = track2.get('preview_url')

    if not track1_preview_url or not track2_preview_url:
        return redirect('home')

    # Step 3: Download the preview audio for the selected tracks
    track1_audio_resp = requests.get(track1_preview_url)
    track2_audio_resp = requests.get(track2_preview_url)

    if track1_audio_resp.status_code != 200 or track2_audio_resp.status_code != 200:
        return redirect('home')

    try:
        # Define a common sample rate
        common_sr = 22050  # You can choose 44100 or another standard rate if preferred

        # Load audio data as stereo with a common sample rate
        audio1, sr1 = librosa.load(BytesIO(track1_audio_resp.content), sr=common_sr, mono=False)
        audio2, sr2 = librosa.load(BytesIO(track2_audio_resp.content), sr=common_sr, mono=False)

        # Ensure audio has two channels
        if audio1.ndim != 2 or audio1.shape[0] != 2:
            raise ValueError("Track 1 audio is not stereo.")
        if audio2.ndim != 2 or audio2.shape[0] != 2:
            raise ValueError("Track 2 audio is not stereo.")

        # Remove vocals using phase inversion
        accompaniment1 = remove_vocals_phase_inversion(audio1, sr1)
        accompaniment2 = remove_vocals_phase_inversion(audio2, sr2)

        # Analyze tempos of accompaniments
        tempo1, _ = librosa.beat.beat_track(y=accompaniment1, sr=sr1)
        tempo2, _ = librosa.beat.beat_track(y=accompaniment2, sr=sr2)

        # Ensure tempos are scalar floats
        if isinstance(tempo1, np.ndarray):
            tempo1 = float(tempo1)
        if isinstance(tempo2, np.ndarray):
            tempo2 = float(tempo2)

        print(f"Track 1 Tempo: {tempo1} BPM")
        print(f"Track 2 Tempo: {tempo2} BPM")

        # Set the target tempo to match the higher tempo
        target_tempo = max(tempo1, tempo2)
        print(f"Target Tempo: {target_tempo} BPM")

        # Calculate time stretching factors
        if tempo1 < target_tempo:
            stretch_factor1 = target_tempo / tempo1
        else:
            stretch_factor1 = 1.0

        if tempo2 < target_tempo:
            stretch_factor2 = target_tempo / tempo2
        else:
            stretch_factor2 = 1.0

        # Ensure stretch factors are scalar floats
        stretch_factor1 = float(stretch_factor1)
        stretch_factor2 = float(stretch_factor2)

        print(f"Stretch Factor for Track 1: {stretch_factor1}")
        print(f"Stretch Factor for Track 2: {stretch_factor2}")

        # Apply time stretching to match tempos
        accompaniment1_stretched = librosa.effects.time_stretch(accompaniment1, rate=stretch_factor1)
        accompaniment2_stretched = librosa.effects.time_stretch(accompaniment2, rate=stretch_factor2)

        # After time stretching, sample rates remain the same (common_sr)

        # Align the lengths by truncating to the minimum length
        min_len = min(len(accompaniment1_stretched), len(accompaniment2_stretched))
        accompaniment1_aligned = accompaniment1_stretched[:min_len]
        accompaniment2_aligned = accompaniment2_stretched[:min_len]

        # Mix the two accompaniment signals
        mixed_accompaniment = (accompaniment1_aligned + accompaniment2_aligned) / 2

        # Normalize the final mix to prevent clipping
        max_val = np.max(np.abs(mixed_accompaniment))
        if max_val > 0:
            final_mix_normalized = mixed_accompaniment / max_val
        else:
            final_mix_normalized = mixed_accompaniment

        # Save the final mixed audio to a buffer
        mixed_audio_buffer = BytesIO()
        sf.write(mixed_audio_buffer, final_mix_normalized, common_sr, format='WAV')
        mixed_audio_buffer.seek(0)

        # Encode the mixed audio to Base64
        mixed_audio_base64 = base64.b64encode(mixed_audio_buffer.read()).decode('utf-8')

    except Exception as e:
        print(f"Error during audio processing: {e}")  # For debugging purposes
        return redirect('home')

    # Step 5: Render the game template and pass the mixed audio and track names
    context = {
        'track1_name': track1.get('name'),
        'track2_name': track2.get('name'),
        'mixed_audio': mixed_audio_base64,  # Pass Base64 encoded audio
    }

    return render(request, 'game.html', context)



def split_vocals_instrumentals(audio, sr):
    """
    Splits the input audio into vocals and instrumental components.

    Parameters:
    - audio: numpy array with shape (n_samples,)
    - sr: sample rate

    Returns:
    - vocals: numpy array with shape (n_samples,)
    - instrumental: numpy array with shape (n_samples,)
    """
    # Apply HPSS (Harmonic/Percussive Source Separation) to split vocals and instrumentals
    harmonic, percussive = librosa.effects.hpss(audio)

    # Assuming vocals are more present in the harmonic component and instrumental in the percussive component
    vocals = harmonic
    instrumental = percussive

    return vocals, instrumental


def game_split_vocals(request):
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Fetch the user's top tracks
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=10"
    response = requests.get(top_tracks_url, headers=headers)

    if response.status_code != 200:
        return redirect('home')

    top_tracks = response.json().get('items', [])

    if len(top_tracks) == 0:
        return redirect('home')

    # Step 2: Pick one track from the top 10
    track = random.choice(top_tracks)
    track_preview_url = track.get('preview_url')

    if not track_preview_url:
        return redirect('home')

    # Step 3: Download the preview audio for the selected track
    track_audio_resp = requests.get(track_preview_url)

    if track_audio_resp.status_code != 200:
        return redirect('home')

    try:
        # Define a sample rate
        sr = 22050  # You can choose 44100 or another standard rate if preferred

        # Load audio data as mono with the given sample rate
        audio, _ = librosa.load(BytesIO(track_audio_resp.content), sr=sr, mono=True)

        # Split the audio into vocals and instrumental parts
        vocals, instrumental = split_vocals_instrumentals(audio, sr)

        # Save the vocals and instrumental audio to buffers
        vocals_buffer = BytesIO()
        instrumental_buffer = BytesIO()

        sf.write(vocals_buffer, vocals, sr, format='WAV')
        sf.write(instrumental_buffer, instrumental, sr, format='WAV')

        # Encode the vocals and instrumental audio to Base64
        vocals_buffer.seek(0)
        instrumental_buffer.seek(0)

        vocals_base64 = base64.b64encode(vocals_buffer.read()).decode('utf-8')
        instrumental_base64 = base64.b64encode(instrumental_buffer.read()).decode('utf-8')

    except Exception as e:
        print(f"Error during audio processing: {e}")  # For debugging purposes
        return redirect('home')

    # Step 5: Render the game template and pass the vocals and instrumental audio and track name
    context = {
        'track_name': track.get('name'),
        'vocals_audio': vocals_base64,  # Pass Base64 encoded vocals
        'instrumental_audio': instrumental_base64,  # Pass Base64 encoded instrumental
    }

    return render(request, 'game_split_vocals.html', context)



def game_adjust_pitch(request):
    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Fetch the user's top tracks
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=10"
    response = requests.get(top_tracks_url, headers=headers)

    if response.status_code != 200:
        return redirect('home')

    top_tracks = response.json().get('items', [])

    if len(top_tracks) == 0:
        return redirect('home')

    # Step 2: Pick one track from the top 10
    track = random.choice(top_tracks)
    track_preview_url = track.get('preview_url')

    if not track_preview_url:
        return redirect('home')

    # Step 3: Download the preview audio for the selected track
    track_audio_resp = requests.get(track_preview_url)

    if track_audio_resp.status_code != 200:
        return redirect('home')

    try:
        # Define a sample rate
        sr = 22050  # You can choose 44100 or another standard rate if preferred

        # Load audio data as mono with the given sample rate
        audio, _ = librosa.load(BytesIO(track_audio_resp.content), sr=sr, mono=True)

        # Step 4: Determine the key of the song
        chroma = librosa.feature.chroma_cqt(y=audio, sr=sr)
        chroma_mean = np.mean(chroma, axis=1)
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        original_key_index = np.argmax(chroma_mean)
        original_key = notes[original_key_index]

        # Step 5: Adjust the pitch of the audio based on user input (via a form)
        pitch_shift_steps = int(request.GET.get('pitch_shift_steps', 0))  # Default is 0 semitones if not specified
        audio_pitch_shifted = librosa.effects.pitch_shift(audio, sr=sr, n_steps=pitch_shift_steps)

        # Save the pitch-shifted audio to a buffer
        pitch_shifted_buffer = BytesIO()
        sf.write(pitch_shifted_buffer, audio_pitch_shifted, sr, format='WAV')
        pitch_shifted_buffer.seek(0)

        # Encode the pitch-shifted audio to Base64
        pitch_shifted_base64 = base64.b64encode(pitch_shifted_buffer.read()).decode('utf-8')

    except Exception as e:
        print(f"Error during audio processing: {e}")  # For debugging purposes
        return redirect('home')

    # Step 6: Render the game template and pass the pitch-shifted audio, track name, and original key
    context = {
        'track_name': track.get('name'),
        'original_key': original_key,
        'pitch_shifted_audio': pitch_shifted_base64,  # Pass Base64 encoded pitch-shifted audio
        'pitch_shift_steps': pitch_shift_steps,  # Display how much the pitch was shifted
    }

    return render(request, 'game_adjust_pitch.html', context)



def game_mix_pitch(request):

    access_token = request.session.get('spotify_access_token')

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    # Step 1: Fetch the user's top tracks
    top_tracks_url = "https://api.spotify.com/v1/me/top/tracks?limit=50"
    response = requests.get(top_tracks_url, headers=headers)

    if response.status_code != 200:
        return redirect('home')

    top_tracks = response.json().get('items', [])

    if len(top_tracks) < 2:
        return redirect('home')

    # Step 2: Pick two random tracks from the top 10
    track1, track2 = random.sample(top_tracks, 2)
    track1_preview_url = track1.get('preview_url')
    track2_preview_url = track2.get('preview_url')

    if not track1_preview_url or not track2_preview_url:
        return redirect('home')

    # Step 3: Download the preview audio for the selected tracks
    track1_audio_resp = requests.get(track1_preview_url)
    track2_audio_resp = requests.get(track2_preview_url)

    if track1_audio_resp.status_code != 200 or track2_audio_resp.status_code != 200:
        return redirect('home')

    try:
        # Define a sample rate
        sr = 22050  # You can choose 44100 or another standard rate if preferred

        # Load audio data as mono with the given sample rate
        audio1, _ = librosa.load(BytesIO(track1_audio_resp.content), sr=sr, mono=True)
        audio2, _ = librosa.load(BytesIO(track2_audio_resp.content), sr=sr, mono=True)

        # Step 4: Determine the key of each song
        chroma1 = librosa.feature.chroma_cqt(y=audio1, sr=sr)
        chroma2 = librosa.feature.chroma_cqt(y=audio2, sr=sr)

        chroma_mean1 = np.mean(chroma1, axis=1)
        chroma_mean2 = np.mean(chroma2, axis=1)

        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key1_index = np.argmax(chroma_mean1)
        key2_index = np.argmax(chroma_mean2)
        key1 = notes[key1_index]
        key2 = notes[key2_index]

        # Step 5: Determine how many semitones to shift to match keys
        semitone_shift = key2_index - key1_index

        # Step 6: Adjust the pitch of one of the songs to match the other key
        audio1_adjusted = librosa.effects.pitch_shift(audio1, sr=sr, n_steps=semitone_shift)

        # Step 7: Make the volume of both songs the same
        rms1 = np.sqrt(np.mean(audio1_adjusted**2))
        rms2 = np.sqrt(np.mean(audio2**2))

        if rms1 > 0:
            audio1_adjusted = audio1_adjusted * (rms2 / rms1)

        # Step 8: Align the lengths of the two audio clips by truncating to the minimum length
        min_length = min(len(audio1_adjusted), len(audio2))
        audio1_aligned = audio1_adjusted[:min_length]
        audio2_aligned = audio2[:min_length]

        # Step 9: Mix the two audio tracks together
        mixed_audio = (audio1_aligned + audio2_aligned) / 2

        # Normalize the final mix to prevent clipping
        max_val = np.max(np.abs(mixed_audio))
        if max_val > 0:
            final_mix_normalized = mixed_audio / max_val
        else:
            final_mix_normalized = mixed_audio

        # Save the final mixed audio to a buffer
        mixed_audio_buffer = BytesIO()
        sf.write(mixed_audio_buffer, final_mix_normalized, sr, format='WAV')
        mixed_audio_buffer.seek(0)

        # Encode the mixed audio to Base64
        mixed_audio_base64 = base64.b64encode(mixed_audio_buffer.read()).decode('utf-8')

    except Exception as e:
        print(f"Error during audio processing: {e}")  # For debugging purposes
        return redirect('home')

    # Step 10: Render the game template and pass the mixed audio, track names, and original keys
    context = {
        'track1_name': track1.get('name'),
        'track2_name': track2.get('name'),
        'key1': key1,
        'key2': key2,
        'mixed_audio': mixed_audio_base64,  # Pass Base64 encoded mixed audio
    }

    return render(request, 'game_mix_pitch.html', context)
