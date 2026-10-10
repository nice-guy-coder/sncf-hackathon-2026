"""Calculer les parcours piétons IGN du catalogue, sans données d’enseignants."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.attractions import catalogue
from app.walking import CACHE_FILE, walking_route, cache_key, closest_station


def main():
    records = json.loads(CACHE_FILE.read_text()) if CACHE_FILE.exists() else {}
    for item in catalogue():
        station = closest_station(item)
        if not station:
            continue
        result = walking_route(item, use_cache=False)
        if result['status'] == 'calculated':
            records[cache_key(item, station)] = result
        print(item['id'], result['status'], result['estimated_walking_minutes'])
    CACHE_FILE.write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')

if __name__ == '__main__':
    main()
