from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
USER_AGENT = "NightRideFuelFinder/1.0 (https://example.com/contact)"


class GeoLookupError(Exception):
    """Исключение для ошибок геокодирования."""


class OverpassError(Exception):
    """Исключение для ошибок загрузки данных из Overpass API."""


@dataclass(frozen=True)
class StationInfo:
    name: str
    brand: Optional[str]
    operator_name: Optional[str]
    address: Optional[str]
    latitude: float
    longitude: float
    distance_km: float
    tags: Dict[str, Any]


def get_city_coordinates(city_name: str) -> Tuple[float, float]:
    """Возвращает координаты (широта, долгота) для указанного города."""
    headers = {"User-Agent": USER_AGENT}
    params = {"q": city_name, "format": "json", "limit": 1}

    try:
        response = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GeoLookupError(f"Не удалось выполнить запрос к геокодеру: {exc}") from exc

    data = response.json()
    if not data:
        raise GeoLookupError("Город не найден. Уточните запрос.")

    first_hit = data[0]
    return float(first_hit["lat"]), float(first_hit["lon"])


def build_overpass_query(lat: float, lon: float, radius_km: float) -> str:
    radius_meters = max(1000, int(radius_km * 1000))
    return f"""
    [out:json][timeout:25];
    (
      node
        (around:{radius_meters},{lat},{lon})
        ["amenity"="fuel"]["opening_hours"~"24/7"];
      way
        (around:{radius_meters},{lat},{lon})
        ["amenity"="fuel"]["opening_hours"~"24/7"];
    );
    out center;
    """


def fetch_open_247_gas_stations(lat: float, lon: float, radius_km: float) -> List[Dict[str, Any]]:
    """Запрашивает список круглосуточных АЗС в заданном радиусе."""
    headers = {"User-Agent": USER_AGENT}
    payload = {"data": build_overpass_query(lat, lon, radius_km)}

    try:
        response = requests.post(OVERPASS_URL, data=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OverpassError(f"Ошибка запроса к Overpass API: {exc}") from exc

    data = response.json()
    elements = data.get("elements", [])
    return elements


def haversine_distance_km(
    lat1: float, lon1: float, lat2: float, lon2: float, earth_radius_km: float = 6371.0
) -> float:
    """Возвращает расстояние между двумя точками на сфере (Хеверсин)."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


def extract_coordinates(element: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Извлекает координаты из ответа Overpass (node/way)."""
    if "lat" in element and "lon" in element:
        return float(element["lat"]), float(element["lon"])
    if "center" in element and "lat" in element["center"] and "lon" in element["center"]:
        center = element["center"]
        return float(center["lat"]), float(center["lon"])
    return None


def build_station_info(element: Dict[str, Any], distance_km: float, coordinates: Tuple[float, float]) -> StationInfo:
    """Преобразует ответ Overpass в StationInfo."""
    tags = element.get("tags", {})
    name = tags.get("name", "Без названия")
    brand = tags.get("brand")
    operator_name = tags.get("operator")

    address_parts = [
        tags.get("addr:city"),
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
    ]
    address_compiled = ", ".join(part for part in address_parts if part) or None

    return StationInfo(
        name=name,
        brand=brand,
        operator_name=operator_name,
        address=address_compiled,
        latitude=coordinates[0],
        longitude=coordinates[1],
        distance_km=distance_km,
        tags=tags,
    )


def find_gas_station_for_ride(
    city: str, ride_distance_km: float, tolerance_km: float
) -> Tuple[StationInfo, List[str]]:
    """Подбирает случайную АЗС согласно параметрам поездки."""
    steps: List[str] = []

    steps.append("Получаю координаты города...")
    city_lat, city_lon = get_city_coordinates(city)

    steps.append("Ищу круглосуточные АЗС поблизости...")
    search_radius_km = max(ride_distance_km + tolerance_km, tolerance_km)
    stations = fetch_open_247_gas_stations(city_lat, city_lon, search_radius_km)

    if not stations:
        raise OverpassError("В указанном радиусе не найдено круглосуточных АЗС.")

    candidates: List[Tuple[Dict[str, Any], float, Tuple[float, float]]] = []

    for station in stations:
        coords = extract_coordinates(station)
        if not coords:
            continue

        station_lat, station_lon = coords
        distance = haversine_distance_km(city_lat, city_lon, station_lat, station_lon)

        if ride_distance_km - tolerance_km <= distance <= ride_distance_km + tolerance_km:
            candidates.append((station, distance, coords))

    if not candidates:
        raise OverpassError(
            "Круглосуточные АЗС найдены, но ни одна не попала в заданный диапазон дистанции."
        )

    steps.append(f"Найдено подходящих вариантов: {len(candidates)}. Выбираю случайную точку назначения...")

    station, distance, coords = random.choice(candidates)
    info = build_station_info(station, distance, coords)
    return info, steps


__all__ = [
    "GeoLookupError",
    "OverpassError",
    "StationInfo",
    "find_gas_station_for_ride",
]

