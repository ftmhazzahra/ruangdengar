# ruangdengar/urls.py

from django.contrib import admin
from django.urls import path, include  # Pastikan 'include' ada di sini
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),  # Google OAuth URLs
    
    # Baris ini sudah benar, ia mengarahkan URL 'auth/'
    # ke file 'users/urls.py'
    path('', include('users.urls')),
]

if settings.DEBUG:
    # Serve static & media in development
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)