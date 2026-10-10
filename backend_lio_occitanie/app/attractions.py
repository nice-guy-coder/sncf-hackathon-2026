"""Catalogue de visites indépendant des hébergements ; aucune disponibilité inventée."""
import json
from math import asin, cos, radians, sin, sqrt
import re
from functools import lru_cache
from pathlib import Path
from .llm.date_utils import strip_accents
from .llm.pedagogical import THEMES


def normalize(value):
    return re.sub(r'[^a-z0-9]+', ' ', strip_accents(value.lower())).strip()


def canonical_theme(value):
    low = normalize(value)
    for theme, keywords in THEMES.items():
        if low == normalize(theme) or any(normalize(word) in low for word in keywords):
            return theme
    return None


@lru_cache(maxsize=1)
def catalogue():
    path = Path(__file__).resolve().parent.parent / 'data/known_destinations_catalog.json'
    return json.loads(path.read_text())


def attraction_by_id(identifier):
    return next((item for item in catalogue() if item['id'] == identifier), None)


@lru_cache(maxsize=1)
def stations():
    path = Path(__file__).resolve().parent.parent / 'data/stations_occitanie.json'
    return json.loads(path.read_text())


def station_key(value):
    value = normalize(value)
    value = re.sub(r'^(?:gare (?:de |d )?|sncf )', '', value)
    return value.replace('saint ', 'st ')


def find_station(query):
    key = station_key(query)
    if key == 'albi ville':
        key = 'albi'
    exact = next((item for item in stations() if station_key(item['name']) == key or item['id'] == query), None)
    if exact:
        return exact
    # Une ville ambiguë doit être précisée plutôt que géocodée arbitrairement.
    matches = [item for item in stations() if station_key(item['commune']) == key]
    return matches[0] if len(matches) == 1 else None


def distance_km(first, second):
    lat1, lat2 = radians(first['latitude']), radians(second['latitude'])
    delta_lat = lat2 - lat1
    delta_lon = radians(second['longitude'] - first['longitude'])
    return 6371.0088 * 2 * asin(sqrt(min(1, sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lon / 2) ** 2)))


def search_attractions(station=None, theme=None, commune=None, department=None, radius_km=5):
    requested_station = find_station(station) if station else None
    if station and not requested_station:
        raise ValueError('Gare inconnue ou ville ambiguë : choisissez une gare dans la liste proposée.')
    results = []
    for original in catalogue():
        item = dict(original)
        geolocated = item.get('latitude') is not None and item.get('longitude') is not None
        # Destination connue : filtrage géographique exclusivement, aucun filtre de thème.
        if requested_station:
            if not geolocated:
                continue
            dist = distance_km(item, requested_station)
            if dist > radius_km:
                continue
            station_for_site = requested_station
        elif geolocated:
            station_for_site = min(stations(), key=lambda candidate: distance_km(item, candidate))
            dist = distance_km(item, station_for_site)
        else:
            station_for_site = None
            dist = None
        if not requested_station and theme and canonical_theme(theme) not in item['theme_tags']:
            continue
        if commune and normalize(commune) not in normalize(item['commune']):
            continue
        if department and normalize(department) not in normalize(item['department']):
            continue
        if station_for_site:
            item['nearest_station'] = station_for_site['name']
            item['station_source_url'] = station_for_site['source_url']
            item['distance_vol_oiseau_km'] = round(dist, 2)
            item['station_relation'] = 'Distance à vol d’oiseau calculée ; itinéraire et accès scolaire à vérifier.'
        item.update(themes=', '.join(item['theme_tags']), nearby_activities=item['description'],
                    accessibility_verdict=item['station_relation'], capacity=None,
                    nature_label='Site de visite', accessible_handicap=None, reference_tariff=None)
        results.append(item)
    if requested_station:
        results.sort(key=lambda item: item['distance_vol_oiseau_km'])
    return results
