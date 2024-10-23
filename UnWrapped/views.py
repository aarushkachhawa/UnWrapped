# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import CustomUser
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.http import JsonResponse
from .forms import CustomUserCreationForm
from django.contrib.auth.views import LoginView
from .forms import AddReviewForm

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
        print("1")
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Successfully logged in")
                return redirect('home') # readd success message when we add messages to user profile page
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            print("2")
            messages.error(request, 'Invalid username or password.')
    else:
        print("3")
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

# placeholder data until we get spotify API working
def get_top_artists():
    return ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4', 'Artist 5']


def get_top_songs():
    return ['Song 1', 'Song 2', 'Song 3', 'Song 4', 'Song 5']


def get_top_artist_by_month():
    return 'Artist of the Month'


def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    top_artists = get_top_artists()
    top_songs = get_top_songs()
    top_artist_month = get_top_artist_by_month()

    context = {
        'top_artists': top_artists,
        'top_songs': top_songs,
        'top_artist_month': top_artist_month,
    }

    return render(request, 'home.html', context)


def stats(request):
    # Dummy data for demonstration (replace with real data)
    if not request.user.is_authenticated:
        return redirect('login')
    slides = [
        {
            'title': 'Top Artists of the Year',
            'content': ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4', 'Artist 5'],
        },
        {
            'title': 'Top Songs of the Year',
            'content': ['Song 1', 'Song 2', 'Song 3', 'Song 4', 'Song 5'],
        },
        {
            'title': 'Most Listened Genre',
            'content': ['Pop', 'Rock', 'Hip Hop'],
        },
        {
            'title': 'Total Minutes Listened',
            'content': ['35,000 minutes'],
        },
    ]

    context = {
        'slides': slides
    }

    return render(request, 'stats.html', context)
