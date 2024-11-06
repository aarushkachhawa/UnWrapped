import requests
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
import logging

logger = logging.getLogger(__name__)

# Spotify credentials from settings.py
SPOTIFY_CLIENT_ID = settings.SPOTIFY_CLIENT_ID
SPOTIFY_CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
SPOTIFY_REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI
SPOTIFY_SCOPE = 'user-top-read'  # Add more scopes if needed
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_API_URL = "https://api.spotify.com/v1/me/top/artists"
SPOTIFY_TRACK_URL = "https://api.spotify.com/v1/me/top/tracks"

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
    context = getStats(request)
    return render(request, 'home.html', context)

@login_required
def getStats(request):

    if 'wrappedData' in request.session:
        return request.session['wrappedData'] # the format for request.session['wrappedData'] is {'top_artists': list, 'top_songs': list, 'top_artist_year': string}

    access_token = request.session['spotify_access_token']
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    numTopTracks = 5 # change this to x top tracks you want
    response = requests.get(f"{SPOTIFY_API_URL}?time_range=long_term&limit={numTopTracks}", headers=headers) # medium_term for 6 months, short_term for 1 month, long_term for 1 year
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
        return {'top_artists': ["N/A"], 'top_songs': ["N/A"], 'top_artist_year': "N/A"}

    try:
        data = response.json()
        artists = data.get('items', [])
        top_artists = [artists[i]['name'] for i in range(min(5, len(artists)))]
        top_songs_data = trackResponse.json()
        songs = top_songs_data.get('items', [])
        top_songs = [songs[i]['name'] for i in range(min(5, len(songs)))]

        returnData = {
            'top_artists': top_artists,
            'top_songs': top_songs,
            'top_artist_year': top_artists[0] if top_artists else "Unknown",
        }
        request.session['wrappedData'] = returnData
        return returnData
    except Exception as e:
        logger.error(f"Error processing Spotify data: {e}")
        messages.error(request, "An error occurred while processing Spotify data.")
        return {'top_artists': ["N/A"], 'top_songs': ["N/A"], 'top_artist_year': "N/A"}


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

    slides = [
        {
            'title': 'Top Artists of the Year',
            'content': wrappedData['top_artists'],
        },
        {
            'title': 'Top Songs of the Year',
            'content': wrappedData['top_songs'],
        },
        {
            'title': 'Top Artist This Year',
            'content': [wrappedData['top_artist_year']], # top_artist_year is a single value and the slides expect a list
        },
    ]

    context = {
        'slides': slides
    }

    return render(request, 'stats.html', context)
