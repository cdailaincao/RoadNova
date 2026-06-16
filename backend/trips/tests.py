from datetime import date

from django.test import TestCase
from django.urls import reverse

from .models import Stop, Trip
from .services import build_plan


class TripViewsTests(TestCase):
    def setUp(self):
        self.trip = Trip.objects.create(
            title='Test Route',
            origin='Austin',
            destination='Marfa',
            tagline='A testable desert route.',
            mood='wild',
            start_date=date(2026, 6, 1),
            days=3,
            distance_km=640,
            budget=450,
        )
        Stop.objects.create(trip=self.trip, order=1, name='Austin', note='Start here.', drive_time='Start')

    def test_home_loads(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, 'RoadNova')
        self.assertContains(response, 'Bangalore')

    def test_plan_trip_api_creates_detailed_india_plan(self):
        response = self.client.post(
            reverse('plan_trip'),
            data={
                'origin': 'bangalore',
                'destination': 'goa',
                'start_date': '2026-06-01',
                'end_date': '2026-06-04',
                'travelers': 4,
                'mileage': 14,
                'interests': ['beaches', 'temples', 'food'],
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['origin'], 'Bangalore')
        self.assertEqual(payload['destination'], 'Goa')
        self.assertEqual(payload['days'], 4)
        self.assertIn('fuel', payload['costs'])
        self.assertGreaterEqual(len(payload['itinerary']), 4)
        self.assertIn('Drive', payload['itinerary'][0]['title'])
        self.assertIn('Fuel stop', [block['label'] for block in payload['itinerary'][0]['drive_blocks']])

    def test_plan_trip_rejects_unsafe_daily_distance(self):
        response = self.client.post(
            reverse('plan_trip'),
            data={
                'origin': 'bangalore',
                'destination': 'manali',
                'start_date': '2026-06-01',
                'end_date': '2026-06-05',
                'travelers': 4,
                'mileage': 14,
                'interests': ['nature'],
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('300 km per day', response.json()['error'])

    def test_long_trip_generates_when_enough_days_are_selected(self):
        response = self.client.post(
            reverse('plan_trip'),
            data={
                'origin': 'bangalore',
                'destination': 'manali',
                'start_date': '2026-06-01',
                'end_date': '2026-06-14',
                'travelers': 4,
                'mileage': 14,
                'interests': ['nature'],
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['days'], 14)
        self.assertEqual(len(payload['itinerary']), 14)
        self.assertTrue(all(leg['distance_km'] <= 300 for leg in payload['legs']))
        self.assertFalse(any('Route Halt' in point['name'] for point in payload['route']))

    def test_long_trip_uses_varied_actual_halt_distances(self):
        payload = build_plan(
            'bangalore',
            'manali',
            '2026-06-01',
            '2026-06-14',
            ['nature'],
            4,
            14,
        )
        distances = [leg['distance_km'] for leg in payload['legs']]
        self.assertGreater(len(set(distances)), 3)
        self.assertFalse(any('Route Halt' in point['name'] for point in payload['route']))

    def test_weather_point_endpoint_accepts_stop_coordinates(self):
        response = self.client.get(reverse('weather_point'), {'name': 'Jhansi', 'lat': '25.4484', 'lon': '78.5685', 'days': '1'})
        self.assertIn(response.status_code, {200, 502})

    def test_trip_detail_loads(self):
        response = self.client.get(self.trip.get_absolute_url())
        self.assertContains(response, 'A testable desert route.')

    def test_quick_plan_creates_trip(self):
        response = self.client.post(
            reverse('quick_plan'),
            {
                'title': 'Weekend Loop',
                'origin': 'Boston',
                'destination': 'Portland',
                'days': '2',
                'mood': 'coastal',
                'start_date': '2026-06-10',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Trip.objects.filter(title='Weekend Loop').exists())
