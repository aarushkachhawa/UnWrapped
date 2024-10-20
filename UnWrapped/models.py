from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomWrap(models.Model):
    wrapDate = models.DateTimeField(auto_now_add=True)  # Automatically set the field to now when the object is first created

class CustomUser(AbstractUser):
    name = models.CharField(max_length=200)

    # contact info
    phone_number = models.CharField(max_length=10, null=True, blank=True)

    def __str__(self):
        return f"{self.name}"
