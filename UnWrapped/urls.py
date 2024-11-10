from django.contrib import admin
from django.urls import path
from . import views
from django.shortcuts import redirect

app_name = 'UnWrapped'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('UnWrapped:login', permanent=True)),  # Updated with namespace
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('login/', views.login_view, name='login'),
    path('home/', views.home, name='home'),
    path('stats/', views.stats, name='stats'),
    path('spotify_callback/', views.spotify_callback, name='spotify_callback'),
]