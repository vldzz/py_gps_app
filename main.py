from __future__ import annotations

from dataclasses import asdict
from typing import Optional, Tuple

from flask import Flask, render_template, request

from fuel_service import GeoLookupError, OverpassError, StationInfo, find_gas_station_for_ride

DEFAULT_CITY = "Chisinau"


def parse_float(value: str, field_name: str) -> float:
    message = f"Некорректное значение поля \"{field_name}\". Введите положительное число."
    try:
        parsed = float(value.replace(",", "."))
    except ValueError as exc:
        raise ValueError(message) from exc
    if parsed <= 0:
        raise ValueError(message)
    return parsed


def build_tolerance(ride_distance: float, tolerance_raw: Optional[str]) -> Tuple[float, Optional[str]]:
    if tolerance_raw:
        tolerance = parse_float(tolerance_raw, "Допуск по дистанции")
        return tolerance, None

    tolerance_default = max(ride_distance * 0.2, 5.0)
    hint = (
        "Использовано значение допуска по умолчанию ≈20% от дистанции "
        f"({tolerance_default:.1f} км)."
    )
    return tolerance_default, hint


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    result: Optional[StationInfo] = None
    steps = []
    error: Optional[str] = None
    tolerance_hint: Optional[str] = None
    city = DEFAULT_CITY
    ride_distance_input = ""
    tolerance_input = ""

    if request.method == "POST":
        city = request.form.get("city", "").strip()
        ride_distance_input = request.form.get("ride_distance", "").strip()
        tolerance_input = request.form.get("tolerance", "").strip()

        if not city:
            error = "Поле \"Город\" обязательно."
        else:
            try:
                ride_distance = parse_float(ride_distance_input, "Дистанция поездки")
                tolerance, tolerance_hint = build_tolerance(ride_distance, tolerance_input)

                result, steps = find_gas_station_for_ride(city, ride_distance, tolerance)
            except ValueError as exc:
                error = str(exc)
            except (GeoLookupError, OverpassError) as exc:
                error = str(exc)

    context = {
        "city": city,
        "ride_distance": ride_distance_input,
        "tolerance": tolerance_input,
        "result": asdict(result) if result else None,
        "steps": steps,
        "error": error,
        "tolerance_hint": tolerance_hint,
    }

    return render_template("index.html", **context)


if __name__ == "__main__":
    app.run(debug=True)

