TYRE_TEMP_RANGES = {
    "default":    {"min": 75,  "max": 105},
    "gt3":        {"min": 80,  "max": 105},
    "gt4":        {"min": 75,  "max": 100},
    "formula":    {"min": 85,  "max": 110},
    "prototype":  {"min": 80,  "max": 108},
    "street":     {"min": 60,  "max": 90},
}

IMBALANCE_AXLE_THRESHOLD = 8.0
IMBALANCE_FA_THRESHOLD = 12.0


def _classify_car(car_name: str) -> str:
    name = car_name.lower()
    if any(k in name for k in ["gt3", "amg", "porsche 911 gt3", "ferrari 296", "bmw m4"]):
        return "gt3"
    if any(k in name for k in ["gt4"]):
        return "gt4"
    if any(k in name for k in ["formula", "f3", "f4", "ir-04", "dallara"]):
        return "formula"
    if any(k in name for k in ["lmp", "prototype", "gr86", "hypercar"]):
        return "prototype"
    if any(k in name for k in ["mx-5", "street", "civic"]):
        return "street"
    return "default"


def analyse_tyre_data(car_name: str, fl: float, fr: float, rl: float, rr: float) -> dict:
    """
    Returns a recommendation string and per-corner status flags.
    Status: "ok" | "hot" | "cold"
    """
    ranges = TYRE_TEMP_RANGES[_classify_car(car_name)]
    lo, hi = ranges["min"], ranges["max"]

    def status(temp):
        if temp < lo:
            return "cold"
        if temp > hi:
            return "hot"
        return "ok"

    statuses = {"fl": status(fl), "fr": status(fr), "rl": status(rl), "rr": status(rr)}
    imbalance_front = abs(fl - fr)
    imbalance_rear = abs(rl - rr)
    imbalance_fa = abs((fl + fr) / 2 - (rl + rr) / 2)

    issues = []

    if imbalance_front > IMBALANCE_AXLE_THRESHOLD:
        issues.append(f"Significant front left-right tyre imbalance ({imbalance_front:.1f}°C) — check camber settings.")
    if imbalance_rear > IMBALANCE_AXLE_THRESHOLD:
        issues.append(f"Significant rear left-right tyre imbalance ({imbalance_rear:.1f}°C) — check camber settings.")

    front_avg = (fl + fr) / 2
    rear_avg = (rl + rr) / 2

    if statuses["rl"] == "cold" and statuses["rr"] == "cold":
        delta = lo - rear_avg
        issues.append(
            f"Rear tyres running {delta:.1f}°C below ideal — try increasing rear tyre pressure by 1–2 PSI or reduce brake bias forward."
        )
    if statuses["fl"] == "hot" and statuses["fr"] == "hot":
        issues.append("Front tyres overheating — consider brake bias rearward or reduce front ARB stiffness.")

    if imbalance_fa > IMBALANCE_FA_THRESHOLD:
        direction = "fronts hotter" if front_avg > rear_avg else "rears hotter"
        issues.append(f"Front-rear tyre temp imbalance ({imbalance_fa:.1f}°C, {direction}) — review setup balance.")

    recommendation = " ".join(issues) if issues else "Tyre temps are well balanced this session."

    return {
        "statuses": statuses,
        "imbalance_front": round(imbalance_front, 2),
        "imbalance_rear": round(imbalance_rear, 2),
        "recommendation": recommendation,
    }
