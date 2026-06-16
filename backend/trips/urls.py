from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('api/plan/', views.plan_trip, name='plan_trip'),
    path('api/weather/<slug:city_slug>/', views.weather, name='weather'),
    path('api/weather-point/', views.weather_point, name='weather_point'),
    path('api/pois/', views.pois, name='pois'),
    path('trips/<int:pk>/', views.trip_detail, name='trip_detail'),
    path('quick-plan/', views.quick_plan, name='quick_plan'),
]
