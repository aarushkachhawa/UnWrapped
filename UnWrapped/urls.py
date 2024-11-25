from django.contrib import admin
from django.urls import path
from . import views
from django.shortcuts import redirect

app_name = 'UnWrapped'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('login', permanent=True)),  # Redirect root to login
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('top_artist/', views.top_artist_and_songs_slide, name='top_artist'),
    path('spotify_callback/', views.spotify_callback, name='spotify_callback'),  # Spotify OAuth callback
    path('slide_2/', views.get_most_popular_artists, name="slide_2"),
    path('slide_3/', views.night_owl, name="slide_3"),
    path('calculate_ads/', views.calculate_ads, name='calculate_ads'),
    path('top_artists/', views.get_most_popular_artists, name="top_artists"),
    path('analyze_seasonal_mood/', views.analyze_seasonal_mood, name="analyze_seasonal_mood"),
    path('analyze_clothing/', views.analyze_clothing, name="analyze_clothing"),
    path('night_owl/', views.night_owl, name="night_owl"),
    path('llm_insights_page/', views.llm_insights_page, name="llm_insights_page"),
    path('transition_one/', views.transition_one, name="transition_one"),
    path('ads_minutes/', views.get_account_level, name="ads_minutes"),
    path('profile/', views.profile, name="profile"),
    path('contact/', views.contactDevs, name="contact"),
    path('halloween_graph/', views.halloween_graph, name='halloween_graph'),
    path('christmas_graph/', views.christmas_graph, name='christmas_graph'),
    path('halloween_seasonal/', views.halloween_seasonal, name = 'halloween_seasonal'),
    path('halloween_top_artist/', views.halloween_top_artist, name='halloween_top_artist'),
    path('christmas_top_artist/', views.christmas_top_artist, name='christmas_top_artist'),
    path('halloween_llm/', views.halloween_llm, name="halloween_llm"),
    path('generate_wrap/', views.generate_wrap, name='generate_wrap'),
    path('reset/', views.reset, name='reset'), # For initiating the reset request (email input)
]