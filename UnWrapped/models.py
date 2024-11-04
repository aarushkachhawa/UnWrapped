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
    wrapDate = models.DateTimeField(auto_now_add=True)  # Automatically set the field to now when the object is first created
    year = models.IntegerField(default=datetime.now().year)  # Default to the current year
    top_songs = models.JSONField()  # Field to store top 5 songs and artists as a JSON object

    def save(self, *args, **kwargs):
        # Check if a wrap for the same user and year exists
        existing_wrap = CustomWrap.objects.filter(user=self.user, year=self.year).first()
        
        if existing_wrap:
            # Check if the existing wrap was created on the same date
            if existing_wrap.wrapDate.date() == datetime.now().date():
                # If it exists and the date matches, update it
                existing_wrap.top_songs = self.top_songs
                existing_wrap.save()  # Save the existing wrap
                return  # Exit to avoid creating a new instance
        
        # If no existing wrap or date doesn't match, create a new wrap
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Wrap for {self.year} by {self.user.name}"
