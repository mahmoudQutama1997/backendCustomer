"""Road routing adapter. Configure ROUTING_BASE_URL to a managed OSRM-compatible service."""
import json
import math
import os
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


def road_route(start_lat, start_lon, end_lat, end_lon):
    base = os.getenv("ROUTING_BASE_URL", "https://router.project-osrm.org").rstrip("/")
    url = (f"{base}/route/v1/driving/{start_lon},{start_lat};{end_lon},{end_lat}"
           "?overview=full&geometries=geojson&steps=false")
    request = Request(url, headers={"User-Agent": "Waselni/1.0", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        route = (payload.get("routes") or [None])[0]
        if not route or not route.get("geometry", {}).get("coordinates"):
            raise ValueError("No road route returned")
        return {
            "available": True,
            "distance_meters": round(float(route["distance"])),
            "duration_seconds": round(float(route["duration"])),
            "geometry": route["geometry"]["coordinates"],
            "source": "road_network",
        }
    except (URLError, HTTPError, TimeoutError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        # Do not fabricate a road ETA. Return a straight-line fallback explicitly labelled as approximate.
        radius = 6371000
        p1, p2 = math.radians(start_lat), math.radians(end_lat)
        dp, dl = math.radians(end_lat-start_lat), math.radians(end_lon-start_lon)
        h = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        meters = 2 * radius * math.asin(min(1, math.sqrt(h)))
        return {"available": False, "distance_meters": round(meters), "duration_seconds": None,
                "geometry": [[start_lon, start_lat], [end_lon, end_lat]], "source": "straight_line_approximation",
                "detail": "Road routing is temporarily unavailable; no road ETA is provided."}
