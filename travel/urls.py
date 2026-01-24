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
    path('expenses/delete/<int:pk>/', views.delete_expense, name='delete_expense'),
    
    path('trips/<int:pk>/upload-photos/', views.upload_trip_photos, name='upload_trip_photos'),
    path('photos/delete/<int:pk>/', views.delete_trip_photo, name='delete_trip_photo'),
    path('photos/suggestions/<int:suggestion_id>/<str:action>/', views.manage_face_suggestion, name='manage_face_suggestion'),
    path('face-group/rename/<int:group_id>/', views.rename_face_group, name='rename_face_group'),
    path('face-group/delete/<int:group_id>/', views.delete_face_group, name='delete_face_group'),
    path('trip/<int:pk>/pdf/', views.export_trip_pdf, name='export_trip_pdf'),
    path('settlements/delete/<int:pk>/', views.delete_settlement, name='delete_settlement'),
]
