from django.contrib import admin
from django.urls import path
from main.views import countries, country_detail, help_page, world_map

urlpatterns = [
    path('admin/', admin.site.urls),
    path('country/<slug:slug>/', country_detail, name='country_detail'),
    path('map/', world_map, name='map'),
    path('help/', help_page, name='help'),
    path('', countries, name='countries'),
]
