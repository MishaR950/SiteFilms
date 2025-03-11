from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('movies.urls', namespace='movies')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('movies/', include('movies.urls')),
    path('logout/', LogoutView.as_view(next_page='movies:login'), name='logout'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
