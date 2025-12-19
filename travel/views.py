# travel/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
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

def logout_view(request):
    logout(request)
    return redirect('login')