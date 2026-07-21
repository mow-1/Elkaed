from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('api/auth/', include('apps.users.urls')),
    path('api/courses/', include('apps.courses.urls')),
    path('api/quizzes/', include('apps.quizzes.urls')),
    path('api/commerce/', include('apps.commerce.urls')),
    path('api/videos/', include('apps.videos.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/audit/', include('apps.audit.urls')),
    path('api/attendance/', include('apps.attendance.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
