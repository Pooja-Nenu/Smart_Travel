from django.contrib import admin
from django.urls import path, include
from django.conf import settings               
from django.conf.urls.static import static     

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('travel.urls')),
]
if settings.DEBUG:
    # Explicitly use STATICFILES_DIRS[0] to tell Django exactly where to look
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])