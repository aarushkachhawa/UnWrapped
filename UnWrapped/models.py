from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import datetime

class CustomUser(AbstractUser):
    name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.name}"

    @property
    def wraps_list(self):
        return self.wraps.all()  # Accessing all wraps associated with the user

class CustomWrap(models.Model): # there can only be one wrap per day
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wraps')  # Establishing the relationship
    wrapDate = models.DateTimeField()  # Automatically set the field to now when the object is first created # auto_now_add=True
    year = models.IntegerField(default=datetime.now().year)  # Default to the current year

    top_artist = models.CharField(max_length=500, default="Unknown")
    top_songs = models.JSONField(default=list)
    image_url = models.TextField(default=None)
    top_3_artists = models.TextField(default=list)
    artist1 = models.CharField(max_length=500, default="Unknown")
    artist2 = models.CharField(max_length=500, default="Unknown")
    artist3 = models.CharField(max_length=500, default="Unknown")
    song_artist1 = models.TextField(default="Unknown")
    song_artist2 = models.TextField(default="Unknown")
    song_artist3 = models.TextField(default="Unknown")
    song_artist4 = models.TextField(default="Unknown")
    song_artist5 = models.TextField(default="Unknown")
    song_artist6 = models.TextField(default="Unknown")
    mood1 = models.CharField(max_length=500, default="Unknown")
    mood2 = models.CharField(max_length=500, default="Unknown")
    mood3 = models.CharField(max_length=500, default="Unknown")
    mood4 = models.CharField(max_length=500, default="Unknown")
    mood5 = models.CharField(max_length=500, default="Unknown")
    mood6 = models.CharField(max_length=500, default="Unknown")
    image = models.TextField(default=None)
    season = models.CharField(max_length = 20, default = "Seasonal")
    content = models.TextField(default=None)
    mood = models.CharField(max_length=500, default="Unknown")
    songPath = models.TextField(default=None)
    latest_time = models.CharField(max_length=500, default="Unknown")
    time_ranges = models.JSONField(default=dict)
    total_minutes = models.FloatField(default=0)
    hour_hand_rotation = models.FloatField(default=0)
    minute_hand_rotation = models.FloatField(default=0)
    premium = models.BooleanField(default=False)
    ads_minutes = models.FloatField(default=0)

    def save(self, *args, **kwargs):
        # Check if a wrap for the same user and year exists
        existing_wrap = CustomWrap.objects.filter(user=self.user, year=self.year).first()
        
        if existing_wrap:
            # Check if the existing wrap was created on the same date
            if existing_wrap.wrapDate.date() == datetime.now().date():
                # If it exists and the date matches, update it
                existing_wrap.top_songs = self.top_songs
                # existing_wrap.save()  # Save the existing wrap
                return  # Exit to avoid creating a new instance
        
        # If no existing wrap or date doesn't match, create a new wrap
        super().save(*args, **kwargs)

    def __str__(self):
        ret_str =  f"Wrap for {self.year} by {self.user.name}\n"
        for key, value in self.__dict__.items():
            ret_str += f"{key}: {value}\n"

        return ret_str
    
# llm_insights_data = [
#     {"Mood": "Something"},
#     {"Relationship Status": "Something"},
#     {"Favorite Color": "Something"},
#     {"Favorite Emoji", "Something"},
#     {"Description": "You are a very dark person..."},
# ]


# top_songs_data = [
#     {"song_title": "Song Title 1", "artist": "Artist 1"},
#     {"song_title": "Song Title 2", "artist": "Artist 2"},
#     {"song_title": "Song Title 3", "artist": "Artist 3"},
#     {"song_title": "Song Title 4", "artist": "Artist 4"},
#     {"song_title": "Song Title 5", "artist": "Artist 5"},
# ]

# wrap_instance = CustomWrap(user=user_instance, year=2024, top_songs=top_songs_data)
# wrap_instance.save()  # This will create a new wrap

# # If you call save again on the same date, it will update the existing wrap
# wrap_instance.top_songs = [
#     {"song_title": "Updated Song Title 1", "artist": "Updated Artist 1"},
#     {"song_title": "Updated Song Title 2", "artist": "Updated Artist 2"},
#     {"song_title": "Updated Song Title 3", "artist": "Updated Artist 3"},
#     {"song_title": "Updated Song Title 4", "artist": "Updated Artist 4"},
#     {"song_title": "Updated Song Title 5", "artist": "Updated Artist 5"},
# ]

# wrap_instance.save()  # This will update the existing wrap only if called on the same date
