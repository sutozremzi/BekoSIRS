import json
import logging
import os
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


Coordinate = Tuple[float, float]


@dataclass
class RouteMatrix:
    distances_km: List[List[Optional[float]]]
    durations_min: List[List[Optional[float]]]
    source: str


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.lower() in {"1", "true", "yes", "on"}


def routing_enabled() -> bool:
    return _env_bool("ROUTING_API_ENABLED", True)


def get_route_matrix(coordinates: Sequence[Coordinate]) -> Optional[RouteMatrix]:
    """
    Return driving distance/duration matrix from a routing API.

    Coordinates are expected as (lat, lng). The default provider is the public
    OSRM demo server. It is suitable for development/demo use; for production,
    set ROUTING_API_BASE_URL to a self-hosted OSRM instance or another managed
    compatible endpoint.
    """
    if not routing_enabled() or len(coordinates) < 2:
        return None

    provider = os.getenv("ROUTING_API_PROVIDER", "osrm").lower()
    if provider != "osrm":
        return None

    return _fetch_osrm_table(coordinates)


def _fetch_osrm_table(coordinates: Sequence[Coordinate]) -> Optional[RouteMatrix]:
    base_url = os.getenv("ROUTING_API_BASE_URL", "https://router.project-osrm.org").rstrip("/")
    profile = os.getenv("ROUTING_API_PROFILE", "driving")
    timeout = float(os.getenv("ROUTING_API_TIMEOUT_SECONDS", "5"))
    user_agent = os.getenv("ROUTING_API_USER_AGENT", "BekoSIRS/1.0 delivery-routing")

    # OSRM uses longitude,latitude order in URLs.
    coordinate_path = ";".join(f"{lng:.7f},{lat:.7f}" for lat, lng in coordinates)
    query = urlencode({"annotations": "duration,distance"})
    url = f"{base_url}/table/v1/{profile}/{coordinate_path}?{query}"

    request = Request(url, headers={"User-Agent": user_agent})
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except TimeoutError:
        logger.warning("OSRM timeout (%.1fs) — Haversine fallback kullanılıyor. URL: %s", timeout, url)
        return None
    except (HTTPError, URLError, OSError) as exc:
        logger.warning("OSRM erişim hatası — Haversine fallback kullanılıyor. Hata: %s", exc)
        return None
    except ValueError:
        logger.warning("OSRM geçersiz JSON yanıtı — Haversine fallback kullanılıyor.")
        return None

    if payload.get("code") != "Ok":
        logger.warning("OSRM code != Ok (%s) — Haversine fallback kullanılıyor.", payload.get("code"))
        return None

    distances_m = payload.get("distances")
    durations_s = payload.get("durations")
    if not distances_m or not durations_s:
        return None

    try:
        distances_km = [
            [None if value is None else round(float(value) / 1000, 2) for value in row]
            for row in distances_m
        ]
        durations_min = [
            [None if value is None else round(float(value) / 60, 1) for value in row]
            for row in durations_s
        ]
    except (TypeError, ValueError):
        return None

    return RouteMatrix(
        distances_km=distances_km,
        durations_min=durations_min,
        source="osrm",
    )
