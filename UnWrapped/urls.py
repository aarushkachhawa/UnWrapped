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
    path('profile/', views.profile, name="profile"),
    path('contact/', views.contactDevs, name="contact"),
    path('spotify_callback/', views.spotify_callback, name='spotify_callback'),  # Spotify OAuth callback

    path('top_artist/', views.top_artist_and_songs_slide, name='top_artist'),
    path('slide_2/', views.get_most_popular_artists, name="slide_2"),
    path('top_artists/', views.get_most_popular_artists, name="top_artists"),
    path('analyze_seasonal_mood/', views.analyze_seasonal_mood, name="analyze_seasonal_mood"),
    path('analyze_clothing/', views.analyze_clothing, name="analyze_clothing"),
    path('night_owl/', views.night_owl, name="night_owl"),
    path('llm_insights_page/', views.llm_insights_page, name="llm_insights_page"),
    path('transition_one/', views.transition_one, name="transition_one"),
    path('ads_minutes/', views.get_account_level, name="ads_minutes"),

    path('halloween_ads/', views.halloween_ads, name='halloween_ads'),

]

'''
path('halloween_top_artist/', views.halloween_top_artist, name='halloween_top_artist'),
path('halloween_graph/', views.halloween_graph, name='halloween_graph'),
path('halloween_ads/', views.halloween_ads, name='halloween_ads'),
path('halloween_seasonal_mood/', views.halloween_seasonal_mood, name='halloween_seasonal_mood'),
path('halloween_night_owl/', views.halloween_night_owl, name='halloween_night_owl'),
path('halloween_llm_insights/', views.halloween_llm_insights, name='halloween_llm_insights'),
path('halloween_transition_one/', views.halloween_transition_one, name='halloween_transition_one'),

path('christmas_top_artist/', views.christmas_top_artist, name='christmas_top_artist'),
path('christmas_graph/', views.christmas_graph, name='christmas_graph'),
path('christmas_ads/', views.christmas_ads, name='christmas_ads'),
path('christmas_seasonal_mood/', views.christmas_seasonal_mood, name='christmas_seasonal_mood'),
path('christmas_night_owl/', views.christmas_night_owl, name='christmas_night_owl'),
path('christmas_llm_insights/', views.christmas_llm_insights, name='christmas_llm_insights'),
path('christmas_transition_one/', views.christmas_transition_one, name='christmas_transition_one'),
'''