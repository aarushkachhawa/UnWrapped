# views.py
from django.shortcuts import render

# placeholder data until we get spotify API working
def get_top_artists():
    return ['Artist 1', 'Artist 2', 'Artist 3', 'Artist 4', 'Artist 5']


def get_top_songs():
    return ['Song 1', 'Song 2', 'Song 3', 'Song 4', 'Song 5']


def get_top_artist_by_month():
    return 'Artist of the Month'


def home(request):
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
