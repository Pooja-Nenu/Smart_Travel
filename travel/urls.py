# travel/urls.py
from django.urls import path
from . import views
from django.contrib.auth import views as auth_views # Import built-in auth views

urlpatterns = [
    # Custom Login/Register
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),
    
    
    
    # --- PASSWORD RESET URLS ---
    path('reset_password/', 
         auth_views.PasswordResetView.as_view(template_name="password_reset.html"), 
         name="reset_password"),

    path('reset_password_sent/', 
         auth_views.PasswordResetDoneView.as_view(template_name="password_reset_sent.html"), 
         name="password_reset_done"),

    path('reset/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(template_name="password_reset_form.html"), 
         name="password_reset_confirm"),

    path('reset_password_complete/', 
         auth_views.PasswordResetCompleteView.as_view(template_name="password_reset_done.html"), 
         name="password_reset_complete"),
    
    path('trips/', views.trip_list, name='trip_list'),
    path('trips/create/', views.trip_create, name='trip_create'),
    path('trips/edit/<int:pk>/', views.trip_update, name='trip_update'),
    path('trips/delete/<int:pk>/', views.trip_delete, name='trip_delete'),
    path('trips/<int:pk>/', views.trip_detail, name='trip_detail'), # View Trip + Itinerary
    path('trips/stop/delete/<int:pk>/', views.delete_stop, name='delete_stop'),
    
    path('checklist/toggle/<int:pk>/', views.checklist_toggle, name='checklist_toggle'),
    path('checklist/delete/<int:pk>/', views.checklist_delete, name='checklist_delete'),
    path('checklists/', views.checklist_dashboard, name='checklist_dashboard'),
    path('members/delete/<int:pk>/', views.delete_member, name='delete_member'),
]