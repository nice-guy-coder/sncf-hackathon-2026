"""Itinéraire IGN piéton depuis la gare géographiquement la plus proche."""
import json
import math
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from .attractions import distance_km, stations

SOURCE_URL = 'https://cartes.gouv.fr/aide/fr/guides-utilisateur/utiliser-les-services-de-la-geoplateforme/calcul-itineraire/'
CACHE_FILE = Path(__file__).resolve().parent.parent / 'data/walking_routes.json'
_lock = threading.Lock()
_next_request = 0.0
_cache = {}
_loaded = False


def closest_station(item):
    if item.get('latitude') is None or item.get('longitude') is None:
        return None
    return min(stations(), key=lambda station: distance_km(item, station))


def cache_key(item, station):
    return f"{station['id']}:{station['latitude']},{station['longitude']}:{item['latitude']},{item['longitude']}"


def reserve_request():
    global _next_request
    with _lock:
        now = time.monotonic()
        delay = max(0, _next_request - now)
        _next_request = max(_next_request, now) + 0.25
    if delay:
        time.sleep(delay)


def walking_route(item, use_cache=True):
    global _loaded
    station = closest_station(item)
    result = {'closest_station': station['name'] if station else None, 'estimated_walking_minutes': None,
              'walking_distance_m': None, 'status': 'missing_coordinates', 'source_url': SOURCE_URL,
              'notice': 'Coordonnées du lieu manquantes : temps de marche indisponible.'}
    if not station:
        return result
    key = cache_key(item, station)
    with _lock:
        if not _loaded:
            if CACHE_FILE.exists():
                try:
                    _cache.update(json.loads(CACHE_FILE.read_text()))
                except (OSError, ValueError):
                    pass
            _loaded = True
        cached = _cache.get(key)
        if cached and use_cache:
            return dict(cached)
    result.update(status='unavailable', notice='Le calcul de l’itinéraire piéton est indisponible. Réessayez.')
    try:
        reserve_request()
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            response = client.get('https://data.geopf.fr/navigation/itineraire', params={
                'resource': 'bdtopo-osrm', 'start': f"{station['longitude']},{station['latitude']}",
                'end': f"{item['longitude']},{item['latitude']}", 'profile': 'pedestrian',
                'optimization': 'fastest', 'distanceUnit': 'meter', 'timeUnit': 'minute', 'getSteps': 'false',
            })
            response.raise_for_status()
            data = response.json()
        duration, distance = data['duration'], data['distance']
        if (data.get('profile') != 'pedestrian' or data.get('timeUnit') != 'minute' or data.get('distanceUnit') != 'meter'
                or isinstance(duration, bool) or isinstance(distance, bool)
                or not math.isfinite(duration) or not math.isfinite(distance) or duration < 0 or distance < 0):
            raise ValueError('Réponse IGN invalide')
        # Rejeter un recalage cartographique trop éloigné des coordonnées connues.
        for name, point in [('start', station), ('end', item)]:
            longitude, latitude = map(float, data[name].split(','))
            if distance_km(point, {'latitude': latitude, 'longitude': longitude}) > 0.3:
                raise ValueError('Point trop éloigné du réseau piéton')
        result.update(status='calculated', estimated_walking_minutes=math.ceil(duration), walking_distance_m=round(distance),
                      resource_version=data.get('resourceVersion'), calculated_at=datetime.now(timezone.utc).isoformat(),
                      notice='Estimation IGN sur itinéraire piéton ; prévoir une marge pour le groupe et vérifier le parcours sur place.')
        with _lock:
            _cache[key] = dict(result)
    except (httpx.HTTPError, ValueError, TypeError, KeyError, OverflowError):
        pass
    return result
