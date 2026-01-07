# travel/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db.models import Case, When, Value, IntegerField
from .forms import UserRegistrationForm, UserLoginForm
from .models import Trip, TripItinerary, ChecklistItem, GroupMember, Expense
from .forms import TripForm, ItineraryForm, ChecklistForm, GroupMemberForm, ExpenseForm
import random
from django.conf import settings
from django.core.mail import send_mail

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
    trips_count = Trip.objects.filter(user=user).count()

    if request.method == 'POST':
        # --- ACTION 1: UPDATE PROFILE ---
        if 'update_profile' in request.POST:
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.country = request.POST.get('country', user.country)
            user.state = request.POST.get('state', user.state)
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')

        # --- ACTION 2: CHANGE PASSWORD ---
        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                messages.success(request, "Password updated successfully! Please log in with your new password.")
                return redirect('login')
            else:
                # Specific errors will be shown next to the fields in the form
                pass

    return render(request, 'profile.html', {
        'password_form': password_form,
        'trips_count': trips_count
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
            return redirect('trip_detail', pk=trip.pk) 
    else:
        form = TripForm(instance=trip)
    return render(request, 'trip_form.html', {'form': form, 'title': 'Edit Trip'})

# DELETE TRIP VIEW
@login_required
def trip_delete(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    if request.method == 'POST':
        trip.delete()
        return redirect('trip_list')
    return render(request, 'trip_confirm_delete.html', {'trip': trip})

# --- TRIP DETAIL & ITINERARY VIEW ---
@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    stops = trip.itinerary.all()
    members = trip.members.all() # Fetch members
    
    # Checklist Logic
    checklist_items = trip.checklist.all().annotate(
        priority_val=Case(
            When(priority='High', then=Value(1)),
            When(priority='Medium', then=Value(2)),
            When(priority='Low', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by('priority_val', 'is_done')

    # Progress Calculation
    total_items = checklist_items.count()
    completed_items = checklist_items.filter(is_done=True).count()
    progress = int((completed_items / total_items) * 100) if total_items > 0 else 0

    # Expense Logic
    expenses = trip.expenses.all().order_by('-date')
    total_expense = sum(e.amount for e in expenses)

    # Initialize Forms
    form = ItineraryForm()
    checklist_form = ChecklistForm()
    member_form = GroupMemberForm()
    expense_form = ExpenseForm()
    # Limit paid_by choices to members of this trip
    expense_form.fields['paid_by'].queryset = GroupMember.objects.filter(trip=trip)

    if request.method == 'POST':
        # --- 1. MEMBER FORM ---
        if 'add_member' in request.POST:
            member_form = GroupMemberForm(request.POST)
            if member_form.is_valid():
                name = member_form.cleaned_data['name']
                contact = member_form.cleaned_data['contact']

                # Duplicate check
                if GroupMember.objects.filter(trip=trip, contact=contact).exists():
                    messages.error(request, f"Member with email {contact} is already part of this trip.")
                    return redirect('trip_detail', pk=pk)

                # Generate Verification Code
                verification_code = str(random.randint(100000, 999999))

                # Store in Session
                request.session['pending_member'] = {
                    'name': name,
                    'contact': contact,
                    'trip_id': trip.pk,
                    'code': verification_code
                }

                # Send Email
                try:
                    subject = "Your Trip Verification Code"
                    message = f"Hello {name},\n\nYour Trip Verification Code is: {verification_code}\n\nPlease enter this on the website to join the trip."
                    from_email = settings.EMAIL_HOST_USER
                    recipient_list = [contact]
                    send_mail(subject, message, from_email, recipient_list)
                    
                    messages.success(request, f"Verification code sent to {contact}")
                except Exception as e:
                    print(f"Email Error: {e}")
                    if settings.DEBUG:
                        messages.warning(request, f"Email failed but you are in DEBUG mode. Your code is: {verification_code}")
                
                return redirect('trip_detail', pk=pk)

        # --- NEW: VERIFY CODE FORM ---
        elif 'verify_code' in request.POST:
            entered_code = request.POST.get('code')
            pending_data = request.session.get('pending_member')

            if pending_data and entered_code == pending_data['code']:
                GroupMember.objects.create(
                    trip=trip,
                    name=pending_data['name'],
                    contact=pending_data['contact']
                )
                del request.session['pending_member']
                messages.success(request, f"Member {pending_data['name']} verified and added!")
                return redirect('trip_detail', pk=pk)
            else:
                messages.error(request, "Invalid verification code.")
                return redirect('trip_detail', pk=pk)

        # --- NEW: CANCEL VERIFICATION ---
        elif 'cancel_verification' in request.POST:
            if 'pending_member' in request.session:
                del request.session['pending_member']
            return redirect('trip_detail', pk=pk)

        # --- 2. CHECKLIST FORM ---
        elif 'add_checklist_item' in request.POST:
            item_id = request.POST.get('checklist_item_id')
            if item_id:
                item_instance = get_object_or_404(ChecklistItem, pk=item_id, trip=trip)
                checklist_form = ChecklistForm(request.POST, instance=item_instance)
            else:
                checklist_form = ChecklistForm(request.POST)

            if checklist_form.is_valid():
                item = checklist_form.save(commit=False)
                item.trip = trip
                item.save()
                return redirect('trip_detail', pk=pk)
        
        # --- 3. ITINERARY FORM ---
        elif 'stop_id' in request.POST or 'location' in request.POST: 
            stop_id = request.POST.get('stop_id')
            if stop_id:
                stop_instance = get_object_or_404(TripItinerary, pk=stop_id, trip=trip)
                form = ItineraryForm(request.POST, instance=stop_instance)
            else:
                form = ItineraryForm(request.POST)

            if form.is_valid():
                stop = form.save(commit=False)
                stop.trip = trip 
                stop.save()
                return redirect('trip_detail', pk=pk)

        # --- 4. EXPENSE FORM ---
        elif 'add_expense' in request.POST:
            expense_id = request.POST.get('expense_id')
            if expense_id:
                expense_instance = get_object_or_404(Expense, pk=expense_id, trip=trip)
                expense_form = ExpenseForm(request.POST, instance=expense_instance)
            else:
                expense_form = ExpenseForm(request.POST)

            if expense_form.is_valid():
                expense = expense_form.save(commit=False)
                expense.trip = trip
                expense.save()
                return redirect('trip_detail', pk=pk)

    return render(request, 'trip_detail.html', {
        'trip': trip,
        'stops': stops,
        'members': members,
        'form': form,
        'checklist_items': checklist_items,
        'checklist_form': checklist_form,
        'member_form': member_form,
        'progress': progress,
        'expenses': expenses,
        'expense_form': expense_form,
        'total_expense': total_expense
    })
    
@login_required
def delete_member(request, pk):
    member = get_object_or_404(GroupMember, pk=pk)
    trip_pk = member.trip.pk
    if member.trip.user == request.user:
        member.delete()
    return redirect('trip_detail', pk=trip_pk)
    
@login_required
def checklist_toggle(request, pk):
    item = get_object_or_404(ChecklistItem, pk=pk)
    if item.trip.user == request.user:
        item.is_done = not item.is_done
        item.save()
    return redirect('trip_detail', pk=item.trip.pk)

@login_required
def checklist_delete(request, pk):
    item = get_object_or_404(ChecklistItem, pk=pk)
    trip_pk = item.trip.pk
    if item.trip.user == request.user:
        item.delete()
    return redirect('trip_detail', pk=trip_pk)

@login_required
def checklist_dashboard(request):
    trips = Trip.objects.filter(user=request.user).order_by('start_date')
    
    for trip in trips:
        total = trip.checklist.count()
        done = trip.checklist.filter(is_done=True).count()
        if total > 0:
            trip.progress = int((done / total) * 100)
        else:
            trip.progress = 0

    urgent_items = ChecklistItem.objects.filter(
        trip__user=request.user, 
        priority='High', 
        is_done=False
    ).select_related('trip')

    return render(request, 'checklist_dashboard.html', {
        'trips': trips,
        'urgent_items': urgent_items
    })

@login_required
def delete_stop(request, pk):
    stop = get_object_or_404(TripItinerary, pk=pk)
    trip_pk = stop.trip.pk 
    if stop.trip.user == request.user: 
        stop.delete()
    return redirect('trip_detail', pk=trip_pk)

@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    trip_pk = expense.trip.pk
    if expense.trip.user == request.user:
        expense.delete()
    return redirect('trip_detail', pk=trip_pk)

def logout_view(request):
    logout(request)
    return redirect('login')