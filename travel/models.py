from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
import pickle

class CustomUser(AbstractUser):
    country = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

class Trip(models.Model):
    # Owner of the trip
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_trips'
    )

    # Members associated with the trip
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='shared_trips',
        blank=True
    )

    name = models.CharField(max_length=200, verbose_name="Trip Name")
    destination = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    description = models.TextField(blank=True, null=True)
    
    # બજેટ ફિલ્ડ અહીં જ રાખવું
    budget = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.destination}"

    @property
    def days_left(self):
        from datetime import date
        delta = self.start_date - date.today()
        if delta.days < 0:
            return "Completed"
        elif delta.days == 0:
            return "Today!"
        return f"{delta.days} days left"


class TripItinerary(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='itinerary'
    )
    location = models.CharField(max_length=255)
    date = models.DateField()
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['date']

    def __str__(self):
        return f"{self.location} on {self.date}"


class ChecklistItem(models.Model):
    PRIORITY_CHOICES = [
        ('High', 'High'),
        ('Medium', 'Medium'),
        ('Low', 'Low'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='checklist'
    )
    item_name = models.CharField(max_length=200)
    is_done = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='Medium'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.item_name} ({self.priority})"


class GroupMember(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='companions'
    )
    name = models.CharField(max_length=100)
    contact = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Email"
    )

    def __str__(self):
        return self.name


class Expense(models.Model):
    CATEGORY_CHOICES = [
        ('Food', 'Food'),
        ('Travel', 'Travel'),
        ('Stay', 'Stay'),
        ('Shopping', 'Shopping'),
        ('Other', 'Other'),
    ]

    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='expenses'
    )
    title = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_by = models.ForeignKey(
        GroupMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses'
    )
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='Other'
    )
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"


class TripPhoto(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='photos'
    )
    image = models.ImageField(upload_to='trip_photos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Photo for {self.trip.name}"


class FaceGroup(models.Model):
    trip = models.ForeignKey(
        Trip,
        on_delete=models.CASCADE,
        related_name='face_groups'
    )
    name = models.CharField(max_length=100, default="Unknown Person")
    thumbnail = models.ImageField(upload_to='face_thumbnails/', null=True, blank=True)
    representative_encoding = models.BinaryField()

    def __str__(self):
        return f"{self.name} in {self.trip.name}"


class PhotoFaceRelation(models.Model):
    photo = models.ForeignKey(
        TripPhoto,
        on_delete=models.CASCADE,
        related_name='faces'
    )
    face_group = models.ForeignKey(
        FaceGroup,
        on_delete=models.CASCADE,
        related_name='tagged_photos'
    )


class FaceMergeSuggestion(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='merge_suggestions')
    group_a = models.ForeignKey(FaceGroup, on_delete=models.CASCADE, related_name='suggestions_as_a')
    group_b = models.ForeignKey(FaceGroup, on_delete=models.CASCADE, related_name='suggestions_as_b')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group_a', 'group_b')

    def __str__(self):
        return f"Suggest merge: {self.group_a.name} & {self.group_b.name}"