"""Location helpers for profile-based course recommendations."""

from __future__ import annotations

import math
import re
from typing import Optional

AREA_COORDINATES = {
    "adachi ku": (35.7750, 139.8040),
    "adachi-ku": (35.7750, 139.8040),
    "arakawa": (35.7362, 139.7833),
    "bunkyo": (35.7081, 139.7528),
    "chiyoda": (35.6938, 139.7530),
    "chuo": (35.6706, 139.7720),
    "edogawa": (35.7068, 139.8684),
    "itabashi": (35.7512, 139.7090),
    "katsushika": (35.7436, 139.8474),
    "kita": (35.7528, 139.7335),
    "kita senju": (35.7498, 139.8053),
    "kitasenju": (35.7498, 139.8053),
    "koenji": (35.7056, 139.6499),
    "ueno": (35.7138, 139.7773),
    "ikebukuro": (35.7289, 139.7101),
    "akihabara": (35.6984, 139.7730),
    "asakusa": (35.7148, 139.7967),
    "shinagawa": (35.6285, 139.7387),
    "meguro": (35.6415, 139.6982),
    "setagaya": (35.6464, 139.6532),
    "nakano": (35.7074, 139.6638),
    "nerima": (35.7356, 139.6517),
    "ota": (35.5613, 139.7160),
    "suginami": (35.6995, 139.6364),
    "sumida": (35.7107, 139.8015),
    "taito": (35.7127, 139.7795),
    "toshima": (35.7295, 139.7163),
    "shinbashi": (35.6663, 139.7587),
    "ebisu": (35.6467, 139.7101),
    "shibuya": (35.6580, 139.7016),
    "shinjuku": (35.6938, 139.7034),
    "harajuku": (35.6702, 139.7027),
    "yoyogi": (35.6831, 139.7020),
    "tokyo": (35.6812, 139.7671),
    "tokyo station": (35.6812, 139.7671),
    "nihombashi": (35.6841, 139.7742),
    "ginza": (35.6717, 139.7650),
    "yokohama": (35.4660, 139.6227),
    "kawasaki": (35.5308, 139.7029),
    "saitama": (35.8617, 139.6455),
    "omiya": (35.9064, 139.6231),
    "urawa": (35.8586, 139.6566),
    "kawaguchi": (35.8079, 139.7241),
    "funabashi": (35.6940, 139.9823),
    "kashiwa": (35.8623, 139.9711),
    "matsudo": (35.7876, 139.9035),
    "chiba station": (35.6131, 140.1130),
    "koto city": (35.6735, 139.8170),
    "machida": (35.5468, 139.4386),
    "tama": (35.6369, 139.4468),
    "chiba": (35.6074, 140.1065),
    "tsudanuma": (35.6914, 140.0206),
    "ichikawa": (35.7219, 139.9311),
    "fuchu": (35.6689, 139.4778),
    "hachioji": (35.6556, 139.3389),
    "tachikawa": (35.6982, 139.4130),
    "kawagoe": (35.9251, 139.4858),
    "tokorozawa": (35.7996, 139.4686),
    "chofu": (35.6518, 139.5407),
    "mitaka": (35.6836, 139.5606),
    "musashino": (35.7170, 139.5663),
    "kamakura": (35.3193, 139.5468),
    "fujisawa": (35.3387, 139.4875),
    "zushi": (35.2964, 139.5786),
}

TRAVEL_SPEED_KMH = {
    "train": 32.0,
    "car": 42.0,
    "either": 37.0,
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def resolve_area_coordinates(area: Optional[str]) -> Optional[tuple[float, float]]:
    """Resolve a supported area string to approximate coordinates."""
    if not area:
        return None

    normalized = _normalize(area)
    if normalized in AREA_COORDINATES:
        return AREA_COORDINATES[normalized]

    for key, coords in AREA_COORDINATES.items():
        if normalized in key or key in normalized:
            return coords

    return None


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate straight-line distance in kilometers."""
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_km * c


def estimate_travel_minutes(
    *,
    from_lat: float,
    from_lon: float,
    to_lat: Optional[float],
    to_lon: Optional[float],
    travel_mode: str = "train",
) -> Optional[int]:
    """Estimate travel time using distance and a coarse mode speed."""
    if to_lat is None or to_lon is None:
        return None

    speed = TRAVEL_SPEED_KMH.get((travel_mode or "train").lower(), TRAVEL_SPEED_KMH["train"])
    distance = haversine_km(from_lat, from_lon, to_lat, to_lon)
    adjusted_distance = distance * 1.35
    return max(10, round((adjusted_distance / speed) * 60))
