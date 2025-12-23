# travel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm
from .models import Trip,TripItinerary
from .forms import TripForm,ItineraryForm

def landing_page(request):
    return render(request, 'index.html') 

@login_required
def dashboard(request):
    # Fetch user's trips, newest first
    trips = Trip.objects.filter(user=request.user)
    recent_trips = trips.order_by('-created_at')[:3]
    total_trips = trips.count()
    return render(request, 'dashboard.html', {
        'recent_trips': recent_trips,
        'total_trips': total_trips
    })

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    login_form = UserLoginForm()
    register_form = UserRegistrationForm()
    active_view = 'login'

    if request.method == 'POST':
        # Check if the POST is for Login
        if 'login_submit' in request.POST:
            login_form = UserLoginForm(request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('dashboard')
        
        # Check if the POST is for Register
        elif 'register_submit' in request.POST:
            active_view = 'register'
            register_form = UserRegistrationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user)
                return redirect('dashboard')

    return render(request, 'login.html', {
        'login_form': login_form, 
        'register_form': register_form,
        'active_view': active_view
    })

def register_view(request):
    # We handle everything in login_view now, but keep this for URL safety
    return login_view(request)

@login_required
def profile_view(request):
    user = request.user
    password_form = PasswordChangeForm(user) # Default empty form

    if request.method == 'POST':
        # --- ACTION 1: UPDATE PROFILE ---
        if 'update_profile' in request.POST:
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.country = request.POST.get('country', user.country)
            user.state = request.POST.get('state', user.state)
            
            # Note: Username/Email usually shouldn't be editable directly without validation
            # user.email = request.POST.get('email', user.email) 
            
            user.save()
            messages.success(request, "Profile details updated successfully!")
            return redirect('profile')

        # --- ACTION 2: CHANGE PASSWORD ---
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                # Important: This keeps the user logged in after password change
                update_session_auth_hash(request, user) 
                messages.success(request, "Password changed successfully!")
                return redirect('profile')
            else:
                messages.error(request, "Error changing password. Please check the fields.")

    return render(request, 'profile.html', {
        'password_form': password_form
    })

# TRIP LIST VIEW
@login_required
def trip_list(request):
    trips = Trip.objects.filter(user=request.user).order_by('-start_date')
    return render(request, 'trip_list.html', {'trips': trips})

# CREATE TRIP VIEW
@login_required
def trip_create(request):
    if request.method == 'POST':
        form = TripForm(request.POST)
        if form.is_valid():
            trip = form.save(commit=False)
            trip.user = request.user 
            trip.save()
            messages.success(request, "Trip created successfully! Now add your stops.")
            return redirect('trip_detail', pk=trip.pk)       
    else:
        form = TripForm()
    return render(request, 'trip_form.html', {'form': form, 'title': 'Create New Trip'})
# EDIT TRIP VIEW
@login_required
def trip_update(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TripForm(request.POST, instance=trip)
        if form.is_valid():
            form.save()
            messages.success(request, "Trip updated successfully!")
            return redirect('trip_list')
    else:
        form = TripForm(instance=trip)
    return render(request, 'trip_form.html', {'form': form, 'title': 'Edit Trip'})

# DELETE TRIP VIEW
@login_required
def trip_delete(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    if request.method == 'POST':
        trip.delete()
        messages.success(request, "Trip deleted successfully!")
        return redirect('trip_list')
    return render(request, 'trip_confirm_delete.html', {'trip': trip})

# --- NEW: TRIP DETAIL & ITINERARY VIEW ---
# --- NEW: TRIP DETAIL & ITINERARY VIEW ---
@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    stops = trip.itinerary.all() # Get all stops for this trip

    # Handle "Add Stop" Form
    if request.method == 'POST':
        form = ItineraryForm(request.POST)
        if form.is_valid():
            stop = form.save(commit=False)
            stop.trip = trip # Link stop to the current trip
            stop.save()
            messages.success(request, "Stop added to itinerary!")
            return redirect('trip_detail', pk=pk)
    else:
        form = ItineraryForm()

    return render(request, 'trip_detail.html', {
        'trip': trip,
        'stops': stops,
        'form': form
    })

# --- NEW: DELETE STOP VIEW ---
@login_required
def delete_stop(request, pk):
    stop = get_object_or_404(TripItinerary, pk=pk)
    trip_pk = stop.trip.pk # Remember trip ID to redirect back
    if stop.trip.user == request.user: # Security check
        stop.delete()
        messages.success(request, "Stop removed.")
    return redirect('trip_detail', pk=trip_pk)

def logout_view(request):
    logout(request)
    return redirect('login')


