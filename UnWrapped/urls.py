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
    path('delete/', views.delete_view, name='delete'),
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
    path('halloween_night/', views.halloween_night, name="halloween_night"),
    path('christmas_night/', views.christmas_night, name="christmas_night"),
    path('llm_insights_page/', views.llm_insights_page, name="llm_insights_page"),
    path('transition_one/', views.transition_one, name="transition_one"),
    path('ads_minutes/', views.get_account_level, name="ads_minutes"),
    path('halloween_ads/', views.halloween_ads, name="halloween_ads"),
    path('christmas_ads/', views.christmas_ads, name="christmas_ads"),
    path('profile/', views.profile, name="profile"),
    path('contact/', views.contactDevs, name="contact"),
    path('halloween_graph/', views.halloween_graph, name='halloween_graph'),
    path('christmas_graph/', views.christmas_graph, name='christmas_graph'),
    path('halloween_seasonal/', views.halloween_seasonal, name = 'halloween_seasonal'),
    path('halloween_top_artist/', views.halloween_top_artist, name='halloween_top_artist'),
    path('christmas_top_artist/', views.christmas_top_artist, name='christmas_top_artist'),
    path('halloween_llm/', views.halloween_llm, name="halloween_llm"),
    path('christmas_llm/', views.christmas_llm, name="christmas_llm"),
    path('christmas_seasonal/', views.christmas_seasonal, name = 'christmas_seasonal'),
    path('generate_wrap/', views.generate_wrap, name='generate_wrap'),
    path('reset/', views.reset, name='reset'), # For initiating the reset request (email input)
    path('past_wraps/', views.past_wraps, name='past_wraps'),
    path('game/', views.game_mix_pitch_1, name="game"),
    path('game2/', views.game_mix_pitch_2, name="game2"),
    path('wrap_id_to_session/', views.wrap_id_to_session, name='wrap_id_to_session'),
    path('transition_two/', views.transition_two, name="transition_two"),
    path('halloween_transition_two/', views.halloween_transition_two, name="halloween_transition_two"),
    path('christmas_transition_two/', views.christmas_transition_two, name="christmas_transition_two"),
    path('submit_feedback/', views.submit_feedback, name="submit_feedback"),
    path('halloween_transition_one/', views.halloween_transition_one, name="halloween_transition_one"),
    path('christmas_transition_one/', views.christmas_transition_one, name="christmas_transition_one"),
    path('set_theme_from_profile/', views.set_theme_from_profile, name='set_theme_from_profile'),
    path('summary/', views.summary, name='summary'),
    path('christmas_summary/', views.summary, name='christmas_summary'),
]