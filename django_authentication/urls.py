from django.contrib import admin
from django.urls import path, include
from accounts.admin import CustomAdminSite
admin_site = CustomAdminSite(name='admin')

urlpatterns = [
    path('admin/', admin_site.urls),
    path('api/', include("accounts.urls"))
]
