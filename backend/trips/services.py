import json
from datetime import datetime, timedelta
from math import ceil
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .india_data import CITIES, INTERESTS, corridor_waypoints, places_for_city, road_distance_km


OPEN_METEO_URL = 'https://api.open-meteo.com/v1/forecast'
OVERPASS_URL = 'https://overpass-api.de/api/interpreter'
OSRM_ROUTE_URL = 'https://router.project-osrm.org/route/v1/driving'
MAX_DAILY_DISTANCE_KM = 300
MAX_TRIP_DAYS = 21

FALLBACK_HALTS = [
    ('Hosur', 'Tamil Nadu', 12.7409, 77.8253, 'Hosur business hotel', 'Adyar Ananda Bhavan Hosur', 'Krishnagiri highway edge, fuel plazas, and clean breakfast stops.'),
    ('Krishnagiri', 'Tamil Nadu', 12.5186, 78.2137, 'Hotel Tamil Nadu Krishnagiri', 'Saravana Bhavan Krishnagiri', 'Reservoir views, granite hills, and NH44 service roads.'),
    ('Anantapur', 'Andhra Pradesh', 14.6819, 77.6006, 'Hotel Masineni Grand', 'Blue Moon Highway Restaurant', 'Dryland highway views and reliable fuel plazas.'),
    ('Kurnool', 'Andhra Pradesh', 15.8281, 78.0373, 'Triguna Clarks Inn', 'Aahar Restaurant Kurnool', 'Tungabhadra belt, Orvakal rock detour, and easy overnight access.'),
    ('Hyderabad Outer Ring Road', 'Telangana', 17.2403, 78.4294, 'Airport highway hotel', 'Paradise Biryani Shamshabad', 'ORR service plazas, wide roads, and late food options.'),
    ('Kamareddy', 'Telangana', 18.3205, 78.3370, 'Hotel Basara Kamareddy', 'Kamareddy Highway Food Plaza', 'NH44 refuel point between Hyderabad and Nizamabad.'),
    ('Nizamabad', 'Telangana', 18.6725, 78.0941, 'Hotel Vamshee International', 'Sri Sai Ram Tiffins', 'NH44 town halt with fuel, food, and manageable exit roads.'),
    ('Adilabad', 'Telangana', 19.6641, 78.5320, 'Hotel Ravi Teja', 'Suruchi Restaurant Adilabad', 'Forest-edge highway halt before the Maharashtra stretch.'),
    ('Yavatmal', 'Maharashtra', 20.3888, 78.1204, 'Hotel Varenya Inn', 'Yavatmal Highway Family Restaurant', 'Vidarbha route halt with practical fuel and food breaks.'),
    ('Hinganghat', 'Maharashtra', 20.5487, 78.8398, 'Hotel Radhika Palace', 'Highway Treat Hinganghat', 'Wardha-side highway stop with fuel plazas and practical food breaks.'),
    ('Nagpur', 'Maharashtra', 21.1458, 79.0882, 'Centre Point Hotel', 'Haldiram Nagpur', 'Zero Mile marker and central India highway rhythm.'),
    ('Betul', 'Madhya Pradesh', 21.9108, 77.9012, 'Hotel IC Inn Betul', 'MP Highway Dhaba Betul', 'Satpura-side highway pause with forested road scenery.'),
    ('Bhopal', 'Madhya Pradesh', 23.2599, 77.4126, 'Courtyard by Marriott Bhopal', 'Manohar Dairy Bhopal', 'Lake city halt with safer urban overnight options.'),
    ('Sagar', 'Madhya Pradesh', 23.8388, 78.7378, 'Hotel Deepali Sagar', 'Arihant Bhojanalaya', 'Lake-side town pause and practical highway rest.'),
    ('Gwalior', 'Madhya Pradesh', 26.2183, 78.1828, 'Radisson Gwalior', 'Indian Coffee House Gwalior', 'Fort city halt between central India and the Yamuna corridor.'),
    ('Jhansi', 'Uttar Pradesh', 25.4484, 78.5685, 'Nataraj Sarovar Portico', 'Haveli Restaurant Jhansi', 'Fort views and Bundelkhand highway breaks.'),
    ('Agra', 'Uttar Pradesh', 27.1767, 78.0081, 'Crystal Sarovar Premiere', 'Pinch of Spice', 'Yamuna Expressway plazas and Taj sunrise option.'),
    ('Delhi NCR', 'Delhi', 28.6139, 77.2090, 'Bloomrooms Janpath', 'Karim Hotel', 'City recovery night before northern highway drives.'),
    ('Karnal', 'Haryana', 29.6857, 76.9905, 'Noormahal Palace Karnal', 'Haveli Karnal', 'GT Road halt with dhabas, fuel plazas, and safer northern staging.'),
    ('Ambala', 'Haryana', 30.3782, 76.7767, 'Country Woods Ambala', 'Puran Singh Dhaba Ambala', 'Final plains halt before Chandigarh and Himachal climbs.'),
    ('Chandigarh', 'Chandigarh', 30.7333, 76.7794, 'Hotel Mountview', 'Pal Dhaba', 'Sukhna Lake, Rock Garden, and mountain staging.'),
    ('Mandi', 'Himachal Pradesh', 31.7087, 76.9320, 'Hotel Valley View', 'Mandi Treat', 'Beas river bends and safer hill-road rest.'),
    ('Kullu', 'Himachal Pradesh', 31.9579, 77.1095, 'Hotel Sandhya Palace', 'Sapna Sweets Kullu', 'Valley road, river views, and final Manali approach.'),
    ('Salem', 'Tamil Nadu', 11.6643, 78.1460, 'CJ Pallazzio', 'Selvi Mess Salem', 'Yercaud ghat detour and clean highway exits.'),
    ('Coimbatore', 'Tamil Nadu', 11.0168, 76.9558, 'Zone by The Park Coimbatore', 'Annapoorna Gowrishankar', 'Western Ghats entry roads and coconut belt views.'),
    ('Kochi', 'Kerala', 9.9312, 76.2673, 'Abad Atrium Kochi', 'Grand Hotel Restaurant', 'Coastal city pause before hill or backwater drives.'),
    ('Hubballi', 'Karnataka', 15.3647, 75.1240, 'The President Hotel', 'Basaveshwar Khanavali', 'Unkal Lake evening walk and NH48 service plazas.'),
    ('Kolhapur', 'Maharashtra', 16.7050, 74.2433, 'Sayaji Kolhapur', 'Dehati Kolhapur', 'Mahalaxmi Temple, Rankala Lake, and NH48 food stops.'),
    ('Pune', 'Maharashtra', 18.5204, 73.8567, 'The Central Park Pune', 'Vaishali FC Road', 'Expressway access, old city food, and hill-road staging.'),
    ('Nashik', 'Maharashtra', 19.9975, 73.7898, 'Ibis Nashik', 'Sadhana Restaurant', 'Vineyard roads, Panchavati temples, and highway breaks.'),
    ('Vadodara', 'Gujarat', 22.3072, 73.1812, 'Sayaji Vadodara', 'Mandap Gujarati Thali', 'Laxmi Vilas Palace and expressway access.'),
    ('Udaipur', 'Rajasthan', 24.5854, 73.7125, 'Jagat Niwas Palace', 'Natraj Dining Hall', 'Lake Pichola and Aravalli curve viewpoints.'),
    ('Ajmer', 'Rajasthan', 26.4499, 74.6399, 'Hotel LN Courtyard', 'Mango Masala Ajmer', 'Ana Sagar Lake and Pushkar side detour.'),
]


def fallback_point_from_tuple(halt):
    name, state, lat, lon, hotel, food, scenic = halt
    return {
        'slug': f'fallback-{name.lower().replace(" ", "-")}',
        'name': name,
        'state': state,
        'lat': lat,
        'lon': lon,
        'hotel_avg': 2600,
        'food_avg': 800,
        'fuel_price': 100,
        'scenic': scenic,
        'food': food,
        'hotel': hotel,
        'kind': 'highway',
    }


def _get_json(url, timeout=8):
    request = Request(url, headers={'User-Agent': 'RoadNova-Django/1.0'})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode('utf-8'))


def parse_trip_dates(start_date, end_date):
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    if end < start:
        start, end = end, start
    days = min((end - start).days + 1, MAX_TRIP_DAYS)
    return start, days


def generated_waypoint(origin, destination, slot, days, used_names=None):
    progress = slot / days
    target_lat = origin['lat'] + (destination['lat'] - origin['lat']) * progress
    target_lon = origin['lon'] + (destination['lon'] - origin['lon']) * progress
    used_names = used_names or set()
    available_halts = [halt for halt in FALLBACK_HALTS if halt[0] not in used_names] or FALLBACK_HALTS
    chosen = min(
        available_halts,
        key=lambda halt: abs(halt[2] - target_lat) + abs(halt[3] - target_lon),
    )
    point = fallback_point_from_tuple(chosen)
    point['fuel_price'] = origin['fuel_price']
    return point


def fallback_route_points(origin, destination, days):
    required_stops = days - 1
    if required_stops <= 0:
        return []

    lat_span = destination['lat'] - origin['lat']
    lon_span = destination['lon'] - origin['lon']
    span_sq = lat_span ** 2 + lon_span ** 2 or 1
    candidates = []
    for halt in FALLBACK_HALTS:
        point = fallback_point_from_tuple(halt)
        projection = ((point['lat'] - origin['lat']) * lat_span + (point['lon'] - origin['lon']) * lon_span) / span_sq
        if 0.02 < projection < 0.98:
            point['projection'] = projection
            point['fuel_price'] = origin['fuel_price']
            candidates.append(point)

    candidates.sort(key=lambda point: point['projection'])
    if len(candidates) < required_stops:
        return [generated_waypoint(origin, destination, slot, days, set()) for slot in range(1, days)]

    # Dynamic programming chooses the requested number of stopovers while minimizing the worst day distance.
    dp = {}
    parent = {}
    for index, point in enumerate(candidates):
        distance = road_distance_km(origin, point)
        dp[(1, index)] = distance
        parent[(1, index)] = None

    for count in range(2, required_stops + 1):
        for index, point in enumerate(candidates):
            best = None
            best_prev = None
            for prev_index in range(index):
                prev_key = (count - 1, prev_index)
                if prev_key not in dp:
                    continue
                leg_distance = road_distance_km(candidates[prev_index], point)
                score = max(dp[prev_key], leg_distance)
                if best is None or score < best:
                    best = score
                    best_prev = prev_index
            if best is not None:
                dp[(count, index)] = best
                parent[(count, index)] = best_prev

    best_final = None
    best_index = None
    for index, point in enumerate(candidates):
        key = (required_stops, index)
        if key not in dp:
            continue
        final_leg = road_distance_km(point, destination)
        score = max(dp[key], final_leg)
        if best_final is None or score < best_final:
            best_final = score
            best_index = index

    if best_index is None:
        return [generated_waypoint(origin, destination, slot, days, set()) for slot in range(1, days)]

    selected = []
    count = required_stops
    index = best_index
    while index is not None and count > 0:
        selected.append(candidates[index])
        index = parent[(count, index)]
        count -= 1
    selected.reverse()
    return selected


def osrm_leg_distances(stop_points):
    if len(stop_points) < 2:
        return []
    coordinates = ';'.join(f"{point['lon']},{point['lat']}" for point in stop_points)
    params = urlencode({'overview': 'false', 'geometries': 'geojson'})
    data = _get_json(f'{OSRM_ROUTE_URL}/{coordinates}?{params}', timeout=8)
    route = (data.get('routes') or [{}])[0]
    return [round(leg.get('distance', 0) / 1000) for leg in route.get('legs', [])]


def build_legs(stop_points):
    legs = []
    total_distance = 0
    for index in range(len(stop_points) - 1):
        start_city = stop_points[index]
        end_city = stop_points[index + 1]
        distance = road_distance_km(start_city, end_city)
        if distance > MAX_DAILY_DISTANCE_KM:
            return None, distance, start_city, end_city
        total_distance += distance
        legs.append(
            {
                'from': start_city['name'],
                'to': end_city['name'],
                'from_slug': start_city['slug'],
                'to_slug': end_city['slug'],
                'distance_km': distance,
                'drive_hours': round(distance / 62, 1),
                'toll_estimate': round(distance * 1.65),
            }
        )
    return (legs, total_distance), None, None, None


def apply_routed_distances(stop_points, legs):
    try:
        routed_distances = osrm_leg_distances(stop_points)
    except Exception:
        routed_distances = []
    if len(routed_distances) != len(legs):
        return legs, sum(leg['distance_km'] for leg in legs)

    total_distance = 0
    updated_legs = []
    for leg, distance in zip(legs, routed_distances):
        if distance <= 0:
            distance = leg['distance_km']
        if distance > MAX_DAILY_DISTANCE_KM:
            raise ValueError(
                f"The {leg['from']} to {leg['to']} leg is {distance} km by routed road distance, above the "
                f"{MAX_DAILY_DISTANCE_KM} km daily limit. Increase the trip days so RoadNova can add safer overnight stops."
            )
        updated_leg = {
            **leg,
            'distance_km': distance,
            'drive_hours': round(distance / 58, 1),
            'toll_estimate': round(distance * 1.65),
            'distance_source': 'OSRM routed road distance',
        }
        total_distance += distance
        updated_legs.append(updated_leg)
    return updated_legs, total_distance


def point_places(point):
    if point.get('kind') == 'highway':
        return [
            {'name': point['name'], 'type': 'Route halt', 'note': point['scenic']},
            {'name': point['food'], 'type': 'Food', 'note': 'Use this as the main driver-rest meal stop.'},
            {'name': point['hotel'], 'type': 'Stay', 'note': 'Overnight halt to keep the road day sane.'},
        ]
    return places_for_city(point['slug'], [])


def point_hotels(point):
    return [point['hotel']] if point.get('kind') == 'highway' else point['hotels']


def point_restaurants(point):
    return [point['food']] if point.get('kind') == 'highway' else point['restaurants']


def point_road_notes(point):
    if point.get('kind') == 'highway':
        return {
            'fuel': f"Use the main fuel plaza before entering {point['name']} town traffic.",
            'scenic': point['scenic'],
            'break': f"Keep the halt practical: fuel, washrooms, food, and overnight at {point['hotel']}.",
        }
    return point['road_notes']


def build_plan(origin_slug, destination_slug, start_date, end_date, interests, travelers=4, mileage=14):
    if origin_slug == destination_slug:
        raise ValueError('Choose two different cities.')
    if origin_slug not in CITIES or destination_slug not in CITIES:
        raise ValueError('Choose cities from the RoadNova India list.')

    travelers = max(1, min(int(travelers or 1), 12))
    mileage = max(6, min(float(mileage or 14), 28))
    start, days = parse_trip_dates(start_date, end_date)
    direct_distance = road_distance_km(CITIES[origin_slug], CITIES[destination_slug])
    minimum_days = ceil((direct_distance * 1.35) / MAX_DAILY_DISTANCE_KM)
    if minimum_days > days:
        raise ValueError(
            f"{CITIES[origin_slug]['name']} to {CITIES[destination_slug]['name']} is about {direct_distance} km by road. "
            f"At RoadNova's safe limit of {MAX_DAILY_DISTANCE_KM} km per day, choose at least {minimum_days} trip days."
        )

    origin_point = {**CITIES[origin_slug], 'slug': origin_slug, 'kind': 'city'}
    destination_point = {**CITIES[destination_slug], 'slug': destination_slug, 'kind': 'city'}
    stop_points = [
        origin_point,
        *[{**stop, 'kind': 'highway'} for stop in corridor_waypoints(origin_slug, destination_slug, days)],
        destination_point,
    ]
    built, unsafe_distance, unsafe_start, unsafe_end = build_legs(stop_points)

    if built is None:
        stop_points = [origin_point, *fallback_route_points(origin_point, destination_point, days), destination_point]
        built, unsafe_distance, unsafe_start, unsafe_end = build_legs(stop_points)

    if built is None:
        raise ValueError(
            f"The {unsafe_start['name']} to {unsafe_end['name']} leg is {unsafe_distance} km, above the "
            f"{MAX_DAILY_DISTANCE_KM} km daily limit. Increase the trip days so RoadNova can add safer overnight stops."
        )

    legs, total_distance = built
    legs, total_distance = apply_routed_distances(stop_points, legs)
    route_cities = stop_points

    destination = CITIES[destination_slug]
    fuel_price = CITIES[origin_slug]['fuel_price']
    fuel_litres = total_distance / mileage
    fuel_cost = round(fuel_litres * fuel_price)
    toll_cost = sum(leg['toll_estimate'] for leg in legs)
    hotel_cost = round(sum(point['hotel_avg'] for point in stop_points[1:]) or destination['hotel_avg'])
    food_cost = round(sum(point['food_avg'] for point in stop_points) / len(stop_points) * travelers * days)
    total_cost = fuel_cost + toll_cost + hotel_cost + food_cost

    itinerary = []
    for day in range(days):
        leg = legs[day]
        if leg:
            from_city = stop_points[day]
            to_city = stop_points[day + 1]
            from_notes = point_road_notes(from_city)
            to_notes = point_road_notes(to_city)
            to_hotels = point_hotels(to_city)
            to_restaurants = point_restaurants(to_city)
            fuel_km = min(max(round(leg['distance_km'] * 0.38), 70), max(80, leg['distance_km'] - 40))
            scenic_km = min(max(round(leg['distance_km'] * 0.58), 110), max(120, leg['distance_km'] - 25))
            meal_km = min(max(round(leg['distance_km'] * 0.72), 130), max(140, leg['distance_km'] - 15))
            travel_title = f"Drive {leg['distance_km']} km from {from_city['name']} to {to_city['name']}"
            drive_blocks = [
                {
                    'label': 'Start',
                    'distance': '0 km',
                    'text': f"Leave {from_city['name']} by 6:30 AM with tyres checked, FASTag balance ready, offline maps saved, and water/snacks packed.",
                },
                {
                    'label': 'Fuel stop',
                    'distance': f"{fuel_km} km",
                    'text': f"Travel {fuel_km} km to the {from_city['name']}-{to_city['name']} highway fuel plaza, then refuel or top up. {from_notes['fuel']}",
                },
                {
                    'label': 'Scenic halt',
                    'distance': f"{scenic_km} km",
                    'text': f"At around {scenic_km} km, pull into a safe viewpoint or service road shoulder for a 25-minute scenery break. {to_notes['scenic']}",
                },
                {
                    'label': 'Food break',
                    'distance': f"{meal_km} km",
                    'text': f"Pause near the {meal_km} km mark at a highway food court or dhaba for a proper meal and driver rest. Try {to_restaurants[day % len(to_restaurants)]} after arrival if highway options look weak.",
                },
                {
                    'label': 'Arrive',
                    'distance': f"{leg['distance_km']} km",
                    'text': f"Reach {to_city['name']}, park at {to_hotels[day % len(to_hotels)]}, and stop driving for the day.",
                },
            ]
        city = to_city
        date = start + timedelta(days=day)
        places = point_places(city)
        morning = places[0]
        afternoon = places[min(1, len(places) - 1)]
        evening = places[min(2, len(places) - 1)]
        hotels = point_hotels(city)
        restaurants = point_restaurants(city)
        notes = point_road_notes(city)
        itinerary.append(
            {
                'day': day + 1,
                'date': date.isoformat(),
                'city': city['name'],
                'state': city['state'],
                'title': travel_title,
                'drive_blocks': drive_blocks,
                'hotel': hotels[day % len(hotels)],
                'restaurant': restaurants[day % len(restaurants)],
                'morning': f"{morning['name']} - {morning['note']}",
                'afternoon': f"{afternoon['name']} - {afternoon['note']}",
                'evening': f"{evening['name']} - {evening['note']}",
                'drive_note': f"{round(leg['drive_hours'], 1)} driving hours planned. {notes['break']}",
            }
        )

    return {
        'origin': CITIES[origin_slug]['name'],
        'destination': CITIES[destination_slug]['name'],
        'days': days,
        'travelers': travelers,
        'interests': [INTERESTS.get(item, item.title()) for item in interests],
        'route': route_cities,
        'legs': legs,
        'costs': {
            'fuel': fuel_cost,
            'tolls': toll_cost,
            'hotels': hotel_cost,
            'food': food_cost,
            'total': total_cost,
            'per_person': round(total_cost / travelers),
            'fuel_litres': round(fuel_litres, 1),
        },
        'itinerary': itinerary,
        'emergency': {
            'primary': '112',
            'police': '100',
            'fire': '101',
            'ambulance': '108',
            'road_help': '1033',
        },
    }


def weather_for_point(name, lat, lon, days=7):
    params = urlencode(
        {
            'latitude': lat,
            'longitude': lon,
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
            'timezone': 'Asia/Kolkata',
            'forecast_days': max(1, min(int(days or 7), 16)),
        }
    )
    data = _get_json(f'{OPEN_METEO_URL}?{params}')
    daily = data.get('daily', {})
    forecast = []
    for index, day in enumerate(daily.get('time', [])):
        forecast.append(
            {
                'date': day,
                'max_c': daily.get('temperature_2m_max', [None])[index],
                'min_c': daily.get('temperature_2m_min', [None])[index],
                'rain_pct': daily.get('precipitation_probability_max', [0])[index],
                'code': daily.get('weather_code', [None])[index],
            }
        )
    return {'city': name, 'forecast': forecast}


def weather_for_city(city_slug, days=7):
    city = CITIES[city_slug]
    return weather_for_point(city['name'], city['lat'], city['lon'], days)


def osm_pois(city_slug, category):
    city = CITIES[city_slug]
    tags = {
        'hotels': '["tourism"="hotel"]',
        'restaurants': '["amenity"="restaurant"]',
        'temples': '["amenity"="place_of_worship"]',
        'beaches': '["natural"="beach"]',
    }
    tag = tags.get(category, tags['restaurants'])
    query = f"""
    [out:json][timeout:8];
    (
      node(around:18000,{city['lat']},{city['lon']}){tag};
      way(around:18000,{city['lat']},{city['lon']}){tag};
    );
    out center 8;
    """
    params = urlencode({'data': query})
    data = _get_json(f'{OVERPASS_URL}?{params}', timeout=10)
    pois = []
    for item in data.get('elements', [])[:8]:
        tags_data = item.get('tags', {})
        name = tags_data.get('name')
        if not name:
            continue
        pois.append(
            {
                'name': name,
                'lat': item.get('lat') or item.get('center', {}).get('lat'),
                'lon': item.get('lon') or item.get('center', {}).get('lon'),
                'kind': category,
            }
        )
    return {'city': city['name'], 'category': category, 'pois': pois}
