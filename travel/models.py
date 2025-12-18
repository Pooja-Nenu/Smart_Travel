from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # FIELDS ALREADY INCLUDED IN ABSTRACTUSER:
    # - first_name
    # - last_name
    # - email
    # - password (stored as a hash)
    # - username
    
    # YOUR CUSTOM FIELDS:
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    
    # TIMESTAMPS
    created_at = models.DateTimeField(auto_now_add=True)  # Set once when created
    updated_at = models.DateTimeField(auto_now=True)      # Updates every time you save
    
    def __str__(self):
        return self.username