from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings

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
    
class Trip(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips')
    
    name = models.CharField(max_length=200, verbose_name="Trip Name")
    destination = models.CharField(max_length=255)  # We store the Google Maps result here
    
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.destination}"
        
    @property
    def days_left(self):
        from datetime import date
        delta = self.start_date - date.today()
        if delta.days < 0: return "Completed"
        elif delta.days == 0: return "Today!"
        return f"{delta.days} days left"
    
class TripItinerary(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='itinerary')
    location = models.CharField(max_length=255) # Uses the same Google/Photon logic
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['date'] # Orders stops by date automatically

    def __str__(self):
        return f"{self.location} on {self.date}"
    
class ChecklistItem(models.Model):
    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='checklist')
    item_name = models.CharField(max_length=200)
    is_done = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} ({self.priority})"
    
class GroupMember(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='members')
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100, blank=True, null=True, help_text="Email")
    
    def __str__(self):
        return self.name