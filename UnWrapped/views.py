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
        top_songs_data = trackResponse.json()
        songs = top_songs_data.get('items', [])
        top_songs = [songs[i]['name'] for i in range(min(5, len(songs)))]
        top_songs_urls = [songs[i]['preview_url'] for i in range(min(5, len(songs)))]

        returnData = {
            'top_artists': top_artists,
            'top_songs': top_songs,
            'top_artist_year': top_artists[0] if top_artists else "Unknown",
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

    # Prepare context with both top artist and top songs
    context = {
        'title': 'Top Artist and Top Songs of the Year',
        'top_artist': wrapped_data['top_artist_year'],
        'top_songs': wrapped_data['top_songs']
    }

    request.session['top_artist'] = wrapped_data['top_artist_year']
    request.session['top_songs'] = wrapped_data['top_songs']
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
    return HttpResponse(ads_minutes)


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

    request.session['top_3_artists'] = json.dumps(top_3_artists)
    request.session['artist1'] = artist1
    request.session['artist2'] = artist2
    request.session['artist3'] = artist3
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
            {"role": "user",
             "content": "The following 100 songs are the songs a user listened to most frequently this season. Describe the music they listened to using 6 adjectives and give an example song for each adjective from their top 100 songs. Follow this format for all 6 adjectives/moods: Mood: Song Title by Artist"},
            {"role": "user", "content": songs}
        ]
    )

    description = response.choices[0].message
    print(description)

    return json.dumps(description)


@login_required
def llm_insights_page(request):
    contentArr = analyze_clothing(request)
    mood = contentArr[0].split(": ")[1].lower()
    if mood not in ["restless", "bitersweet", "introspective", "overjoyed", "pensive"]:
        mood = "other"
    rootDir = f"llmInsights/{mood}/"
    try:
        imageList = [file for file in os.listdir(f"/home/pkadekodi/UnWrapped/static/llmInsights/{mood}") if file[len(file) - 3:].lower() == "jpg"]
        songPath = rootDir + random.choice(imageList)
    except:
        songPath = rootDir + "2014FHD.jpg"
    context = { # send mood in separately because of how horrible django's template functionality is :)
        'content': contentArr,
        'mood': mood,
        'songPath': songPath,
    }
    request.session['content'] = contentArr
    request.session['mood'] = mood
    request.session['songPath'] = songPath

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

    request.session['latest_time'] = context['latest_time']
    request.session['time_ranges'] = json.dumps(time_ranges)
    request.session['total_minutes'] = total_time
    request.session['hour_hand_rotation'] = hour_hand_rotation - 90
    request.sesion['minute_hand_rotation'] = minute_hand_rotation - 90
    
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
