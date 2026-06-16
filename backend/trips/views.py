import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .india_data import CITIES, INTERESTS, city_options
from .models import Stop, Trip
from .services import build_plan, osm_pois, weather_for_city, weather_for_point


def home(request):
    return render(
        request,
        'trips/home.html',
        {
            'cities': city_options(),
            'city_json': city_options(),
            'interests': INTERESTS,
            'emergency_numbers': {
                'National emergency': '112',
                'Police': '100',
                'Fire brigade': '101',
                'Ambulance': '108',
                'Road accident helpline': '1033',
            },
        },
    )


def trip_detail(request, pk):
    trip = get_object_or_404(Trip.objects.prefetch_related('stops'), pk=pk)
    return render(request, 'trips/detail.html', {'trip': trip})


@require_POST
def plan_trip(request):
    try:
        payload = json.loads(request.body.decode('utf-8'))
        interests = payload.get('interests') or ['heritage', 'food', 'nature']
        plan = build_plan(
            payload.get('origin'),
            payload.get('destination'),
            payload.get('start_date'),
            payload.get('end_date'),
            interests,
            payload.get('travelers', 4),
            payload.get('mileage', 14),
        )
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        return JsonResponse({'error': str(error)}, status=400)
    return JsonResponse(plan)


def weather(request, city_slug):
    try:
        return JsonResponse(weather_for_city(city_slug, request.GET.get('days', 7)))
    except Exception as error:
        return JsonResponse({'city': CITIES.get(city_slug, {}).get('name', city_slug), 'error': str(error)}, status=502)


def weather_point(request):
    try:
        name = request.GET.get('name') or 'Route stop'
        lat = float(request.GET.get('lat'))
        lon = float(request.GET.get('lon'))
        return JsonResponse(weather_for_point(name, lat, lon, request.GET.get('days', 7)))
    except Exception as error:
        return JsonResponse({'city': request.GET.get('name', 'Route stop'), 'error': str(error)}, status=502)


def pois(request):
    city_slug = request.GET.get('city', 'bangalore')
    category = request.GET.get('category', 'restaurants')
    try:
        return JsonResponse(osm_pois(city_slug, category))
    except Exception as error:
        return JsonResponse({'city': CITIES.get(city_slug, {}).get('name', city_slug), 'category': category, 'pois': [], 'error': str(error)})


@require_POST
def quick_plan(request):
    title = request.POST.get('title', 'Fresh RoadNova Route').strip() or 'Fresh RoadNova Route'
    origin = request.POST.get('origin', 'Your city').strip() or 'Your city'
    destination = request.POST.get('destination', 'Open road').strip() or 'Open road'
    days = max(1, min(int(request.POST.get('days', 3) or 3), 21))
    distance = max(80, days * 240)
    trip = Trip.objects.create(
        title=title,
        origin=origin,
        destination=destination,
        tagline='A new route draft ready for stops, stays, and detours.',
        mood=request.POST.get('mood', 'coastal') or 'coastal',
        start_date=request.POST.get('start_date') or '2026-06-01',
        days=days,
        distance_km=distance,
        budget=days * 115,
        cover_color='#2563eb',
    )
    Stop.objects.bulk_create(
        [
            Stop(trip=trip, order=1, name=origin, note='Pack, fuel up, and roll out early.', drive_time='Start', overnight=False),
            Stop(trip=trip, order=2, name='Scenic midpoint', note='Add a lunch stop, photo break, and route check.', drive_time='3h 20m', overnight=days > 1),
            Stop(trip=trip, order=3, name=destination, note='Arrive with a saved place list and flexible evening plan.', drive_time='3h 45m', overnight=True),
        ]
    )
    return redirect(trip)

# Create your views here.
