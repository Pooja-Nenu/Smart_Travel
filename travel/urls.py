# travel/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Change this line: Make the empty path '' point to login_view
    path('', views.login_view, name='login'),
    
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('logout/', views.logout_view, name='logout'),
    
    # You can move the old landing page to a different URL if you still want to keep it
    path('home/', views.landing_page, name='landing'),
]