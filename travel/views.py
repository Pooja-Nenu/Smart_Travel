# travel/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm

def landing_page(request):
    return render(request, 'index.html') 

def dashboard(request):
    return render(request, 'dashboard.html')

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

def logout_view(request):
    logout(request)
    return redirect('login')