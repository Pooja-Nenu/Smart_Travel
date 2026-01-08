from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.db.models import Case, When, Value, IntegerField, Q
from .forms import UserRegistrationForm, UserLoginForm
from .models import Trip, TripItinerary, ChecklistItem, GroupMember, Expense, CustomUser
from .forms import TripForm, ItineraryForm, ChecklistForm, GroupMemberForm, ExpenseForm
import random
from django.conf import settings
from django.core.mail import send_mail

def landing_page(request):
    return render(request, 'index.html') 

@login_required
def dashboard(request):
    # You will see your own trips and all trips where you are a member.
    trips = Trip.objects.filter(
        Q(user=request.user) | Q(members=request.user)
    ).distinct()
    
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
        if 'login_submit' in request.POST:
            login_form = UserLoginForm(request.POST)
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                return redirect('dashboard')
        
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
    return login_view(request)

@login_required
def profile_view(request):
    user = request.user
    password_form = PasswordChangeForm(user)
    trips_count = Trip.objects.filter(Q(user=user) | Q(members=user)).distinct().count()

    if request.method == 'POST':
        if 'update_profile' in request.POST:
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.country = request.POST.get('country', user.country)
            user.state = request.POST.get('state', user.state)
            user.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')

        elif 'change_password' in request.POST:
            password_form = PasswordChangeForm(user, request.POST)
            if password_form.is_valid():
                user = password_form.save()
                messages.success(request, "Password updated successfully!")
                return redirect('login')

    return render(request, 'profile.html', {
        'password_form': password_form,
        'trips_count': trips_count
    })

@login_required
def trip_list(request):
    # members show trips where the user is added as a collaborator
    trips = Trip.objects.filter(
        Q(user=request.user) | Q(members=request.user)
    ).distinct().order_by('-start_date')
    return render(request, 'trip_list.html', {'trips': trips})

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

@login_required
def trip_delete(request, pk):
    trip = get_object_or_404(Trip, pk=pk, user=request.user)
    if request.method == 'POST':
        trip.delete()
        return redirect('trip_list')
    return render(request, 'trip_confirm_delete.html', {'trip': trip})

@login_required
def trip_detail(request, pk):
    trip = get_object_or_404(Trip, Q(user=request.user) | Q(members=request.user), pk=pk)
    stops = trip.itinerary.all()
    members = trip.companions.all() # GroupMember list
    
    checklist_items = trip.checklist.all().annotate(
        priority_val=Case(
            When(priority='High', then=Value(1)),
            When(priority='Medium', then=Value(2)),
            When(priority='Low', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by('priority_val', 'is_done')

    total_items = checklist_items.count()
    completed_items = checklist_items.filter(is_done=True).count()
    progress = int((completed_items / total_items) * 100) if total_items > 0 else 0

    expenses = trip.expenses.all().order_by('-date')
    total_expense = sum(e.amount for e in expenses)

    form = ItineraryForm()
    checklist_form = ChecklistForm()
    member_form = GroupMemberForm()
    expense_form = ExpenseForm()
    expense_form.fields['paid_by'].queryset = members

    if request.method == 'POST':
        # --- 1. MEMBER FORM ---
        if 'add_member' in request.POST:
            member_form = GroupMemberForm(request.POST)
            if member_form.is_valid():
                name = member_form.cleaned_data['name']
                contact = member_form.cleaned_data['contact']

                if GroupMember.objects.filter(trip=trip, contact=contact).exists():
                    messages.error(request, f"Email {contact} is already added.")
                    return redirect('trip_detail', pk=pk)

                verification_code = str(random.randint(100000, 999999))
                request.session['pending_member'] = {
                    'name': name, 'contact': contact, 'trip_id': trip.pk, 'code': verification_code
                }

                try:
                    send_mail("Trip Verification Code", f"Code: {verification_code}", settings.EMAIL_HOST_USER, [contact])
                    messages.success(request, f"Code sent to {contact}")
                except Exception:
                    if settings.DEBUG: messages.warning(request, f"DEBUG: Code is {verification_code}")
                return redirect('trip_detail', pk=pk)

        # --- 2. VERIFY CODE ---
        elif 'verify_code' in request.POST:
            entered_code = request.POST.get('code')
            pending_data = request.session.get('pending_member')

            if pending_data and entered_code == pending_data['code']:
                # GroupMember add
                GroupMember.objects.create(trip=trip, name=pending_data['name'], contact=pending_data['contact'])
                
                # Add existing CustomUser to ManyToMany list to display trips.
                try:
                    reg_user = CustomUser.objects.get(email__iexact=pending_data['contact'])
                    trip.members.add(reg_user)
                except CustomUser.DoesNotExist:
                    pass

                del request.session['pending_member']
                messages.success(request, "Member verified and added!")
                return redirect('trip_detail', pk=pk)

        # --- 3. CHECKLIST FORM ---
        elif 'add_checklist_item' in request.POST:
            checklist_form = ChecklistForm(request.POST)
            if checklist_form.is_valid():
                item = checklist_form.save(commit=False)
                item.trip = trip
                item.save()
                return redirect('trip_detail', pk=pk)
        
        # --- 4. ITINERARY FORM ---
        elif 'location' in request.POST or 'stop_id' in request.POST: 
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

        # --- 5. EXPENSE FORM ---
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
        'trip': trip, 'stops': stops, 'members': members, 'form': form,
        'checklist_items': checklist_items, 'checklist_form': checklist_form,
        'member_form': member_form, 'progress': progress, 'expenses': expenses,
        'expense_form': expense_form, 'total_expense': total_expense
    })
    
@login_required
def delete_member(request, pk):
    member = get_object_or_404(GroupMember, pk=pk)
    trip = member.trip
    if trip.user == request.user:
        try:
            u = CustomUser.objects.get(email__iexact=member.contact)
            trip.members.remove(u)
        except CustomUser.DoesNotExist:
            pass
        member.delete()
    return redirect('trip_detail', pk=trip.pk)
    
@login_required
def checklist_toggle(request, pk):
    item = get_object_or_404(ChecklistItem, pk=pk)
    trip = item.trip
    if request.user == trip.user or request.user in trip.members.all():
        item.is_done = not item.is_done
        item.save()
    return redirect('trip_detail', pk=trip.pk)

@login_required
def checklist_delete(request, pk):
    item = get_object_or_404(ChecklistItem, pk=pk)
    if item.trip.user == request.user:
        item.delete()
    return redirect('trip_detail', pk=item.trip.pk)

@login_required
def checklist_dashboard(request):
    trips = Trip.objects.filter(Q(user=request.user) | Q(members=request.user)).distinct().order_by('start_date')
    for trip in trips:
        total = trip.checklist.count()
        done = trip.checklist.filter(is_done=True).count()
        trip.progress = int((done / total) * 100) if total > 0 else 0
    urgent_items = ChecklistItem.objects.filter(Q(trip__user=request.user) | Q(trip__members=request.user), priority='High', is_done=False).distinct()
    return render(request, 'checklist_dashboard.html', {'trips': trips, 'urgent_items': urgent_items})

@login_required
def delete_stop(request, pk):
    stop = get_object_or_404(TripItinerary, pk=pk)
    if stop.trip.user == request.user: stop.delete()
    return redirect('trip_detail', pk=stop.trip.pk)

@login_required
def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if expense.trip.user == request.user: expense.delete()
    return redirect('trip_detail', pk=expense.trip.pk)

def logout_view(request):
    logout(request)
    return redirect('login')