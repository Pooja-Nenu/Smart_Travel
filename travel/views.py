from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.db.models import Case, When, Value, IntegerField, Q, Sum
from django.conf import settings
from django.core.mail import send_mail
import random
from datetime import date
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg') # Use a non-interactive backend
import io
import base64
import openai
from django.conf import settings
import json
from django.contrib import messages
from .models import Trip, ChecklistItem,TripItinerary,FaceGroup, PhotoFaceRelation
import re
import json
from django.http import JsonResponse
from groq import Groq
import os
from dotenv import load_dotenv

load_dotenv()


from .forms import (
    UserRegistrationForm, UserLoginForm, TripForm,
    ItineraryForm, ChecklistForm, GroupMemberForm, ExpenseForm
)

from .models import (
    Trip, TripItinerary, ChecklistItem, GroupMember,
    Expense, CustomUser, TripPhoto, FaceGroup, PhotoFaceRelation, FaceMergeSuggestion,
    Settlement
)

from .utils import process_photo_faces


def landing_page(request):
    return render(request, 'index.html')


@login_required
def dashboard(request):
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
                login(request, login_form.get_user(), backend='django.contrib.auth.backends.ModelBackend')
                return redirect('dashboard')

        elif 'register_submit' in request.POST:
            active_view = 'register'
            register_form = UserRegistrationForm(request.POST)
            if register_form.is_valid():
                user = register_form.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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

    trips_count = Trip.objects.filter(
        Q(user=user) | Q(members=user)
    ).distinct().count()

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
                update_session_auth_hash(request, user)
                messages.success(request, "Password updated successfully!")
                return redirect('profile')

    return render(request, 'profile.html', {
        'password_form': password_form,
        'trips_count': trips_count
    })


@login_required
def trip_list(request):
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
    # 1. Fetch the trip and related data
    trip = get_object_or_404(
        Trip.objects.filter(Q(user=request.user) | Q(members=request.user)).distinct(),
        pk=pk
    )

    stops = trip.itinerary.all()
    
    # Ensure owner is also a member for expense tracking
    GroupMember.objects.get_or_create(
        trip=trip, 
        contact=trip.user.email,
        defaults={'name': f"{trip.user.first_name} (Owner)" if trip.user.first_name else f"{trip.user.username} (Owner)"}
    )
    
    members = trip.companions.all()
    # Only show face groups that actually have photos attached
    face_groups = trip.face_groups.filter(tagged_photos__isnull=False).distinct().prefetch_related('tagged_photos__photo')
    all_photos = trip.photos.all().order_by('-uploaded_at')

    # 2. Checklist Progress Logic
    group_items = trip.checklist.filter(is_personal=False).annotate(
        priority_val=Case(
            When(priority='High', then=Value(1)),
            When(priority='Medium', then=Value(2)),
            When(priority='Low', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by('priority_val', 'is_done')

    personal_items = trip.checklist.filter(is_personal=True, user=request.user).annotate(
        priority_val=Case(
            When(priority='High', then=Value(1)),
            When(priority='Medium', then=Value(2)),
            When(priority='Low', then=Value(3)),
            default=Value(4),
            output_field=IntegerField(),
        )
    ).order_by('priority_val', 'is_done')

    # Clean item names by removing priority in parentheses
    for item in group_items:
        item.cleaned_name = item.item_name.split(' (')[0] if ' (' in item.item_name else item.item_name

    for item in personal_items:
        item.cleaned_name = item.item_name.split(' (')[0] if ' (' in item.item_name else item.item_name

    # For progress, usually we count group items or all visible items. Let's count group items for trip progress.
    total_items = group_items.count()
    completed_items = group_items.filter(is_done=True).count()
    progress = int((completed_items / total_items) * 100) if total_items else 0

    # 3. Basic Expense Data
    expenses = trip.expenses.order_by('-date')
    total_expense = sum(e.amount for e in expenses)
    settlements_list = trip.settlements.order_by('-date')

    current_member = GroupMember.objects.filter(trip=trip, contact=request.user.email).first()
    pending_settlement = request.session.get('pending_settlement')

    # --- START: MODULE 7 & 8 (REPORTS & FUTURE PREDICTION) ---
    category_totals = {}
    for exp in expenses:
        cat = exp.category if exp.category else "Other"
        category_totals[cat] = category_totals.get(cat, 0) + exp.amount
    
    report_labels = list(category_totals.keys())
    report_data = [float(amount) for amount in category_totals.values()]

    # Future Prediction Calculation
    today = date.today()
    total_trip_days = (trip.end_date - trip.start_date).days + 1
    
    if today < trip.start_date:
        days_passed = 0
        days_remaining = total_trip_days
    elif today > trip.end_date:
        days_passed = total_trip_days
        days_remaining = 0
    else:
        days_passed = (today - trip.start_date).days + 1
        days_remaining = total_trip_days - days_passed

    daily_avg = 0
    projected_total = 0
    safe_daily_limit = 0
    budget_status = "No Budget Set"

    # Daily Spending Rate
    if days_passed > 0:
        daily_avg = total_expense / days_passed
        projected_total = daily_avg * total_trip_days
    
    # Budget Analysis
    if trip.budget > 0:
        remaining_budget = trip.budget - total_expense
        if days_remaining > 0:
            safe_daily_limit = remaining_budget / days_remaining
        
        if projected_total > trip.budget:
            budget_status = "Likely to Exceed Budget"
        else:
            budget_status = "On Track"
    # --- END: MODULE 7 & 8 ---

    # --- START: EXPENSE SPLITTER LOGIC (Module 6) ---
    num_members = members.count()
    share_per_person = total_expense / num_members if num_members > 0 else 0
    
    member_balances = []
    debtors = []   
    creditors = [] 

    for m in members:
        amount_paid_by_m = sum(e.amount for e in expenses if e.paid_by == m)
        
        # Add payments made by m
        payments_made = sum(s.amount for s in settlements_list if s.payer == m)
        # Subtract payments received by m
        payments_received = sum(s.amount for s in settlements_list if s.payee == m)
        
        adjusted_paid = amount_paid_by_m + payments_made - payments_received
        balance = adjusted_paid - share_per_person
        
        member_balances.append({
            'member': m,
            'paid': amount_paid_by_m,
            'adjusted_paid': adjusted_paid,
            'balance': balance,
            'abs_balance': abs(balance) 
        })

        if balance < -0.01: 
            debtors.append({'name': m.name, 'amount': abs(balance)})
        elif balance > 0.01: 
            creditors.append({'name': m.name, 'amount': balance})

    settlements = []
    d_idx, c_idx = 0, 0
    temp_debtors = [dict(d) for d in debtors]
    temp_creditors = [dict(c) for c in creditors]

    while d_idx < len(temp_debtors) and c_idx < len(temp_creditors):
        d = temp_debtors[d_idx]
        c = temp_creditors[c_idx]
        settle_amount = min(d['amount'], c['amount'])
        if settle_amount > 0.01:
            settlements.append({
                'from': d['name'],
                'to': c['name'],
                'amount': settle_amount
            })
        d['amount'] -= settle_amount
        c['amount'] -= settle_amount
        if d['amount'] <= 0: d_idx += 1
        if c['amount'] <= 0: c_idx += 1
    # --- END: EXPENSE SPLITTER LOGIC ---

    # 4. Form Initializations
    form = ItineraryForm()
    checklist_form = ChecklistForm()
    checklist_form.fields['stop'].queryset = TripItinerary.objects.filter(trip=trip)
    
    member_form = GroupMemberForm()
    expense_form = ExpenseForm()
    expense_form.fields['paid_by'].queryset = GroupMember.objects.filter(trip=trip)

    # 5. Handle POST requests
    if request.method == 'POST':
        if 'add_member' in request.POST:
            member_form = GroupMemberForm(request.POST)
            if member_form.is_valid():
                name = member_form.cleaned_data['name']
                contact = member_form.cleaned_data['contact']
                if GroupMember.objects.filter(trip=trip, contact=contact).exists():
                    messages.error(request, "Member already added.")
                    return redirect('trip_detail', pk=pk)
                code = str(random.randint(100000, 999999))
                request.session['pending_member'] = {'name': name, 'contact': contact, 'trip_id': trip.pk, 'code': code}
                try:
                    send_mail("Trip Verification Code", f"Your verification code is {code}", settings.EMAIL_HOST_USER, [contact])
                    messages.success(request, f"Code sent to {contact}")
                except Exception:
                    if settings.DEBUG: messages.warning(request, f"DEBUG CODE: {code}")
                return redirect('trip_detail', pk=pk)

        elif 'verify_code' in request.POST:
            entered = request.POST.get('code')
            pending = request.session.get('pending_member')
            if pending and entered == pending['code']:
                member = GroupMember.objects.create(trip=trip, name=pending['name'], contact=pending['contact'])
                try:
                    user = CustomUser.objects.get(email__iexact=pending['contact'])
                    trip.members.add(user)
                except CustomUser.DoesNotExist: pass
                del request.session['pending_member']
            else:
                messages.error(request, "Invalid verification code.")
            return redirect('trip_detail', pk=pk)

        elif 'add_checklist_item' in request.POST:
            item_id = request.POST.get('checklist_item_id')
            instance = get_object_or_404(ChecklistItem, pk=item_id, trip=trip) if item_id else None

            checklist_form = ChecklistForm(request.POST, instance=instance)

            if checklist_form.is_valid():
                item = checklist_form.save(commit=False)
                item.trip = trip

                if not instance:
                    item.user = request.user

                # ✅ THIS IS THE MAIN FIX
                item.is_personal = request.POST.get('is_personal') == 'on'

                item.save()

            return redirect('trip_detail', pk=pk)

        elif 'stop_id' in request.POST or 'location' in request.POST:
            # 1. Add stop only Trip Owner
            if trip.user != request.user:
                messages.error(request, "Only the trip owner can manage itinerary stops.")
                return redirect('trip_detail', pk=pk)
                
            stop_id = request.POST.get('stop_id')
            instance = get_object_or_404(TripItinerary, pk=stop_id, trip=trip) if stop_id else None
            form = ItineraryForm(request.POST, instance=instance)
            if form.is_valid():
                stop = form.save(commit=False); stop.trip = trip; stop.save()
            return redirect('trip_detail', pk=pk)

        elif 'add_expense' in request.POST:
            expense_id = request.POST.get('expense_id')
            instance = get_object_or_404(Expense, pk=expense_id, trip=trip) if expense_id else None
            expense_form = ExpenseForm(request.POST, instance=instance)
            if expense_form.is_valid():
                expense = expense_form.save(commit=False); expense.trip = trip; expense.save()
            return redirect('trip_detail', pk=pk)

        elif 'record_payment' in request.POST:
            payer_name = request.POST.get('from_name')
            payee_name = request.POST.get('to_name')
            amount = request.POST.get('amount')
            
            payer = get_object_or_404(GroupMember, trip=trip, name=payer_name)
            payee = get_object_or_404(GroupMember, trip=trip, name=payee_name)
            
            if not payee.contact:
                messages.error(request, f"Cannot verify payment. {payee_name} has no contact info.")
                return redirect('trip_detail', pk=pk)

            code = str(random.randint(100000, 999999))
            request.session['pending_settlement'] = {
                'from_name': payer_name,
                'to_name': payee_name,
                'amount': amount,
                'code': code,
                'trip_id': trip.pk
            }
            
            try:
                send_mail(
                    "Payment Verification Code",
                    f"{payer_name} wants to record a payment of ${amount} to you. Verification code: {code}",
                    settings.EMAIL_HOST_USER,
                    [payee.contact]
                )
                messages.success(request, f"Verification code sent to {payee_name} ({payee.contact})")
            except Exception:
                if settings.DEBUG: messages.warning(request, f"DEBUG SETTLEMENT CODE: {code}")
            
            return redirect('trip_detail', pk=pk)

        elif 'verify_payment' in request.POST:
            entered = request.POST.get('code')
            pending = request.session.get('pending_settlement')
            
            if pending and pending['trip_id'] == trip.pk and entered == pending['code']:
                payer = get_object_or_404(GroupMember, trip=trip, name=pending['from_name'])
                payee = get_object_or_404(GroupMember, trip=trip, name=pending['to_name'])
                
                Settlement.objects.create(
                    trip=trip,
                    payer=payer,
                    payee=payee,
                    amount=pending['amount'],
                    date=date.today()
                )
                messages.success(request, f"Payment of ${pending['amount']} verified and recorded!")
                del request.session['pending_settlement']
            else:
                messages.error(request, "Invalid verification code.")
            return redirect('trip_detail', pk=pk)

        elif 'cancel_settlement' in request.POST:
            if 'pending_settlement' in request.session:
                del request.session['pending_settlement']
            return redirect('trip_detail', pk=pk)

    # 6. Fetch active merge suggestions
    suggestions = trip.merge_suggestions.filter(is_active=True)

    # 7. Final Context Rendering
    return render(request, 'trip_detail.html', {
        'trip': trip,
        'stops': stops,
        'members': members,
        'form': form,
        'group_items': group_items,
        'personal_items': personal_items,
        'checklist_form': checklist_form,
        'member_form': member_form,
        'progress': progress,
        'expenses': expenses,
        'expense_form': expense_form,
        'total_expense': total_expense,
        # Reports & Prediction Context:
        'category_totals': category_totals,
        'report_labels': report_labels,
        'report_data': report_data,
        'daily_avg': daily_avg,
        'projected_total': projected_total, 
        'safe_daily_limit': safe_daily_limit,
        'budget_status': budget_status,
        'days_remaining': days_remaining,
        # Splitter Context:
        'share_per_person': share_per_person,
        'member_balances': member_balances,
        'settlements': settlements,
        # Photos & Suggestions
        'face_groups': face_groups,
        'all_photos': all_photos,
        'suggestions': suggestions,
        'settlements_list': settlements_list,
        'current_member': current_member,
        'pending_settlement': pending_settlement,
    })
    
@login_required
def upload_trip_photos(request, pk):
    trip = get_object_or_404(
        Trip.objects.filter(Q(user=request.user) | Q(members=request.user)).distinct(),
        pk=pk
    )
    images = request.FILES.getlist('images')
    for img in images:
        photo = TripPhoto.objects.create(trip=trip, image=img)
        process_photo_faces(photo.id)
    messages.success(request, f"{len(images)} photos uploaded!")
    return redirect('trip_detail', pk=pk)


@login_required
def delete_trip_photo(request, pk):
    photo = get_object_or_404(TripPhoto, pk=pk)
    trip = photo.trip
    if request.user == trip.user or request.user in trip.members.all():
        photo.delete()
        # Automatically clean up any face groups that no longer have any associated photos
        FaceGroup.objects.filter(trip=trip, tagged_photos__isnull=True).delete()
        messages.success(request, "Photo removed.")
    return redirect('trip_detail', pk=trip.pk)


@login_required
def rename_face_group(request, group_id):
    group = get_object_or_404(
        FaceGroup.objects.filter(Q(trip__user=request.user) | Q(trip__members=request.user)).distinct(),
        id=group_id
    )
    if request.method == 'POST':
        new_name = request.POST.get('folder_name')
        if new_name:
            group.name = new_name
            group.save()
            messages.success(request, "Folder renamed!")
    return redirect('trip_detail', pk=group.trip.pk)


@login_required
def delete_face_group(request, group_id):
    group = get_object_or_404(
        FaceGroup.objects.filter(Q(trip__user=request.user) | Q(trip__members=request.user)).distinct(),
        id=group_id
    )
    trip_pk = group.trip.pk
    # Deleting the group also removes all PhotoFaceRelation records due to models.CASCADE
    group.delete()
    messages.success(request, "Person profile removed.")
    return redirect('trip_detail', pk=trip_pk)


@login_required
def delete_member(request, pk):
    member = get_object_or_404(GroupMember, pk=pk)
    trip = member.trip
    if trip.user == request.user:
        try:
            user = CustomUser.objects.get(email__iexact=member.contact)
            trip.members.remove(user)
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
    trip_pk = item.trip.pk
    if item.trip.user == request.user:
        item.delete()
    return redirect('trip_detail', pk=trip_pk)


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


@login_required
def delete_settlement(request, pk):
    settlement = get_object_or_404(Settlement, pk=pk)
    trip_pk = settlement.trip.pk
    if settlement.trip.user == request.user:
        settlement.delete()
        messages.success(request, "Settlement record removed.")
    return redirect('trip_detail', pk=trip_pk)


@login_required
def checklist_dashboard(request):
    trips = Trip.objects.filter(
        Q(user=request.user) | Q(members=request.user)
    ).distinct().order_by('start_date')

    for trip in trips:
        total = trip.checklist.count()
        done = trip.checklist.filter(is_done=True).count()
        trip.progress = int((done / total) * 100) if total else 0

    urgent_items = ChecklistItem.objects.filter(
        Q(trip__user=request.user) | Q(trip__members=request.user),
        priority='High',
        is_done=False
    ).distinct()

    return render(request, 'checklist_dashboard.html', {
        'trips': trips,
        'urgent_items': urgent_items
    })


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def manage_face_suggestion(request, suggestion_id, action):
    suggestion = get_object_or_404(FaceMergeSuggestion, id=suggestion_id)
    trip = suggestion.trip
    
    # Permission check
    if request.user != trip.user and request.user not in trip.members.all():
        return redirect('trip_detail', pk=trip.pk)
    
    if action == 'merge':
        group_a = suggestion.group_a # Destination (often the named one)
        group_b = suggestion.group_b # Source (often the new 'unknown' one)
        
        # Move all photos from B to A
        relations_to_move = PhotoFaceRelation.objects.filter(face_group=group_b)
        for rel in relations_to_move:
            # Only move if photo isn't already in A
            if not PhotoFaceRelation.objects.filter(photo=rel.photo, face_group=group_a).exists():
                rel.face_group = group_a
                rel.save()
            else:
                rel.delete() # Duplicate link
        
        # Delete the redundant group
        group_b.delete()
        messages.success(request, f"Profiles merged successfully!")
        
    elif action == 'dismiss':
        suggestion.is_active = False
        suggestion.save()
        messages.info(request, "Suggestion dismissed.")
        
    return redirect('trip_detail', pk=trip.pk)

@login_required
def export_trip_pdf(request, pk):
    trip = get_object_or_404(Trip, pk=pk)
    
    expenses = trip.expenses.all()
    members = trip.companions.all()
    stops = trip.itinerary.all()
    checklist = trip.checklist.all()
    
    total_expense = sum(e.amount for e in expenses)
    num_members = members.count()
    share = total_expense / num_members if num_members > 0 else 0
    
    # --- Visual Analytics Logic Start ---
    chart_url = None
    if expenses.exists():
        # Expense by Category Data Preparation
        category_data = trip.expenses.values('category').annotate(total=Sum('amount'))
        labels = [item['category'] for item in category_data]
        values = [float(item['total']) for item in category_data]

        # Pie Chart Creation
        plt.figure(figsize=(4, 3))
        explode = [0.05] * len(values) 

        plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=140, 
                shadow=True, explode=explode, colors=['#10b981', '#3b82f6', '#f59e0b', '#ef4444'])        
        plt.title('Expense by Category')

        # Chart to PNG Conversion
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', bbox_inches='tight')
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close() # Close the plot to free memory

        graphic = base64.b64encode(image_png).decode('utf-8')
        chart_url = f"data:image/png;base64,{graphic}"
    # --- Visual Analytics Logic End ---

    member_balances = []
    for m in members:
        paid = sum(e.amount for e in expenses if e.paid_by == m)
        member_balances.append({'name': m.name, 'paid': paid, 'diff': paid - share})

    context = {
        'trip': trip,
        'expenses': expenses,
        'total_expense': total_expense,
        'members': members,
        'stops': stops,
        'checklist': checklist,
        'share': share,
        'member_balances': member_balances,
        'chart_url': chart_url, 
    }

    template = get_template('trip_pdf.html')
    html = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Trip_Report_{trip.name}.pdf"'
    
    pisa_status = pisa.CreatePDF(html, dest=response)
    
    if pisa_status.err:
        return HttpResponse('We had some errors <pre>' + html + '</pre>')
    return response


from django.views.decorators.csrf import csrf_exempt
import json
import numpy as np
import pickle 
import faiss                       
from PIL import Image, ImageOps

@csrf_exempt
def search_photos_by_face(request, pk):
    if request.method != 'POST':
        return HttpResponse(status=405)

    trip = get_object_or_404(Trip, pk=pk)
    uploaded_file = request.FILES.get('image')
    
    if not uploaded_file:
        return HttpResponse(json.dumps({'error': 'No image provided'}), content_type="application/json", status=400)


    try:
        pil_image = Image.open(uploaded_file)
        pil_image = ImageOps.exif_transpose(pil_image)
        pil_image = pil_image.convert('RGB')
        
        # --- NEW: Maximum Sharpness Boost ---
        # Webcam images are usually grainy, auto-contrast and high sharpness will fix this
        pil_image = ImageOps.autocontrast(pil_image)
        enhancer = ImageEnhance.Sharpness(pil_image)
        pil_image = enhancer.enhance(4.0) # Maximum sharpness

        image = np.ascontiguousarray(np.array(pil_image), dtype=np.uint8)
        
        # Increase upsampling to catch fine details
        face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=2, model="hog")
        
        if not face_locations:
            return HttpResponse(json.dumps({'error': 'Face not detected. Please ensure your face is well-lit and directly facing the camera.'}), content_type="application/json")
            
        # Multi-jittering to stabilize the webcam face capture
        face_encodings = face_recognition.face_encodings(image, face_locations, model="large", num_jitters=5)

        if not face_encodings:
             return HttpResponse(json.dumps({'error': 'Could not extract features.'}), content_type="application/json")

        uploaded_face_encoding = face_encodings[0]
        face_groups = list(FaceGroup.objects.filter(trip=trip).exclude(representative_encoding=None))
        matching_photo_ids = set()

        if face_groups:
            dimension = 128
            index = faiss.IndexFlatL2(dimension)
            db_encodings, valid_groups = [], []
            for group in face_groups:
                try:
                    encoding = pickle.loads(group.representative_encoding)
                    db_encodings.append(encoding)
                    valid_groups.append(group)
                except: continue
            
            if db_encodings:
                index.add(np.array(db_encodings).astype('float32'))
                query_vector = np.array([uploaded_face_encoding]).astype('float32')
                
                # Check top 5 matches
                distances, indices = index.search(query_vector, k=min(5, len(valid_groups)))
                
                for dist, idx in zip(distances[0], indices[0]):
                    if idx == -1: continue
                    
                    actual_distance = np.sqrt(dist)
                    accuracy_percent = max(0, (1 - actual_distance) * 100)

                    # IMPORTANT: Check your VS Code terminal for this output!
                    print(f"DEBUG SEARCH: Group {valid_groups[idx].id} | Distance: {actual_distance:.4f} | Accuracy: {accuracy_percent:.2f}%")

                    # --- BALANCED THRESHOLD (0.55) ---
                    # 0.55 is loose enough to find you in a webcam photo, 
                    # but still strict enough to keep most others out.
                    if actual_distance <= 0.55: 
                        matched_group = valid_groups[idx]
                        photos = matched_group.tagged_photos.values_list('photo_id', flat=True)
                        matching_photo_ids.update(photos)
                        print(f"SUCCESS: Match confirmed at {accuracy_percent:.2f}%")
                        break # We take the single best match only

        return HttpResponse(json.dumps({'photo_ids': list(matching_photo_ids)}), content_type="application/json")

    except Exception as e:
        print(f"Error in search_photos_by_face: {e}")
        return HttpResponse(json.dumps({'error': 'Server Error'}), status=500)
        
@login_required
def generate_ai_packing(request, trip_id):

    if request.method != "POST":
        return JsonResponse({
            'status': 'failed',
            'message': 'Invalid request method'
        }, status=400)

    try:
        # Get Trip
        trip = get_object_or_404(Trip, id=trip_id)

        # Get is_personal from request
        data = json.loads(request.body)
        is_personal = data.get('is_personal', False)

        # Delete previous AI items (so no duplicates)
        ChecklistItem.objects.filter(
            trip=trip,
            user=request.user,
            is_personal=is_personal
        ).delete()

        # Get itinerary stops
        stops = trip.itinerary.all()
        stops_list = ", ".join([s.location for s in stops])

        # AI Prompt
        prompt = f"""
        Generate a travel packing list for a trip to {trip.destination}.
        Dates: From {trip.start_date} to {trip.end_date}.
        Itinerary Stops: {stops_list if stops_list else 'No specific stops'}.

        Respond with ONLY a comma-separated list of essential packing items, each with a priority in parentheses.
        Priorities: High (essential items), Medium (useful items), Low (optional items).
        Format: Item (Priority), Item (Priority)
        Example: Passport (High), Phone Charger (Medium), Extra Socks (Low)
        """

        # Call Llama API
        if not settings.GROQ_API_KEY:
            return JsonResponse({
                'status': 'failed',
                'message': 'GROQ_API_KEY not configured'
            }, status=500)

        client = Groq(api_key=settings.GROQ_API_KEY)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "user", "content": prompt}
            ],
        )

        # Process response
        ai_text = response.choices[0].message.content.strip()

        # Parse items with priorities
        items_with_priorities = []
        for part in ai_text.split(','):
            part = part.strip()
            if '(' in part and ')' in part:
                # Extract item and priority
                last_paren = part.rfind('(')
                item_name = part[:last_paren].strip()
                priority_part = part[last_paren:].strip('()').strip()
                # Normalize priority
                if priority_part.lower() in ['high', 'essential']:
                    priority = 'High'
                elif priority_part.lower() in ['medium', 'useful']:
                    priority = 'Medium'
                elif priority_part.lower() in ['low', 'optional']:
                    priority = 'Low'
                else:
                    priority = 'Medium'  # default
                if item_name:
                    items_with_priorities.append((item_name, priority))
            else:
                # No priority, assume Medium
                if part:
                    items_with_priorities.append((part, 'Medium'))

        # Save AI items
        created_count = 0

        for item_name, priority in items_with_priorities[:20]:  # Limit to 20
            ChecklistItem.objects.create(
                trip=trip,
                user=request.user,
                item_name=item_name[:200],
                priority=priority,
                is_personal=is_personal
            )
            created_count += 1

        return JsonResponse({
            'status': 'success',
            'items_added': created_count
        })

    except Exception as e:
        return JsonResponse({
            'status': 'failed',
            'message': str(e)
        }, status=500)


# ======================================================
# Fetch Packing Items (Personal + AI Separately)
# ======================================================
@login_required
def get_packing_items(request, trip_id):

    try:
        trip = get_object_or_404(Trip, id=trip_id)

        # Personal items
        personal_items = ChecklistItem.objects.filter(
            trip=trip,
            user=request.user,
            is_personal=True
        ).values(
            'id',
            'item_name',
            'priority'
        )

        # AI items
        ai_items = ChecklistItem.objects.filter(
            trip=trip,
            user=request.user,
            is_personal=False
        ).values(
            'id',
            'item_name',
            'priority'
        )

        return JsonResponse({
            'status': 'success',
            'personal_items': list(personal_items),
            'ai_items': list(ai_items)
        })

    except Exception as e:
        return JsonResponse({
            'status': 'failed',
            'message': str(e)
        }, status=500)
