from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('django-admin/', admin.site.urls),
    path('', include('Remote_User.urls')),
    path('admin/', include('Service_Provider.urls')),
]
