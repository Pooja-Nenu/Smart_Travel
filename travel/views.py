from django.shortcuts import render

def landing_page(request):
    return render(request, 'index.html') 

def dashboard(request):
    return render(request, 'dashboard.html')
