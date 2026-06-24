import os
import json
import asyncio
import httpx

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

_RETRY_DELAYS = [5, 15, 30]  # seconds between retries on 429/503


def _api_key() -> str:
    key = os.getenv("GEMINI_API_KEY", "")
    if not key:
        raise ValueError("GEMINI_API_KEY not set")
    return key


async def _post(payload: dict, key: str | None = None) -> httpx.Response:
    """POST to Gemini with automatic retry on 429 (rate limit) and 503 (overload)."""
    url = f"{GEMINI_API_URL}?key={key or _api_key()}"
    for attempt, delay in enumerate([0] + _RETRY_DELAYS):
        if delay:
            await asyncio.sleep(delay)
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
        if resp.status_code not in (429, 503):
            return resp
        print(f"[gemini] {resp.status_code} on attempt {attempt + 1}, retrying in {_RETRY_DELAYS[attempt]}s...")
    return resp  # return last response after all retries exhausted


async def generate_coaching(session_data: dict) -> dict:
    prompt = f"""You are an expert sim racing coach. Analyse this driver's session data and give exactly 3 specific, actionable coaching tips. Be direct. Reference specific corners or track sections where possible. Do not give generic advice.

Session context:
- Car: {session_data.get('car_name', 'Unknown')}
- Track: {session_data.get('track_name', 'Unknown')}
- Conditions: {session_data.get('air_temp', '?')}°C air, {session_data.get('track_temp', '?')}°C track, {session_data.get('weather', 'unknown')}
- Best lap: {session_data.get('best_lap_time', '?')}s
- Average lap: {session_data.get('avg_lap_time', '?')}s
- Total laps: {session_data.get('lap_count', '?')}
- Delta to PB: {session_data.get('delta_to_pb', '?')}s

Sector breakdown (this session vs personal best):
- Sector 1: {session_data.get('s1_delta', '?')}s
- Sector 2: {session_data.get('s2_delta', '?')}s
- Sector 3: {session_data.get('s3_delta', '?')}s

Driving inputs summary:
- Average max brake pressure: {session_data.get('avg_max_brake', '?')}%
- Average throttle application point (% lap distance): {session_data.get('avg_throttle_point', '?')}%
- Coasting zones detected: {session_data.get('coasting_zones', '?')}
- Oversteer events: {session_data.get('oversteer_count', '?')}

Tyre data:
- Front tyre temp range: {session_data.get('fl_temp_avg', '?')}–{session_data.get('fr_temp_avg', '?')}°C (ideal: 80–100°C for most GT cars)
- Rear tyre temp range: {session_data.get('rl_temp_avg', '?')}–{session_data.get('rr_temp_avg', '?')}°C
- Temperature imbalance (L vs R): {session_data.get('temp_imbalance', '?')}°C

Respond with exactly this JSON structure:
{{
  "tips": [
    {{"title": "short title", "detail": "2-3 sentence specific tip"}},
    {{"title": "short title", "detail": "2-3 sentence specific tip"}},
    {{"title": "short title", "detail": "2-3 sentence specific tip"}}
  ],
  "headline": "one sentence overall session summary"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }

    resp = await _post(payload)
    resp.raise_for_status()
    body = resp.json()
    candidates = body.get("candidates", [])
    if not candidates:
        block = body.get("promptFeedback", {}).get("blockReason", "no candidates returned")
        raise ValueError(f"Gemini returned empty response: {block}")
    raw = candidates[0]["content"]["parts"][0]["text"]
    return json.loads(raw)


async def generate_weekly_narrative(stats: dict) -> str:
    prompt = f"""You are a friendly but precise sim racing coach writing a weekly progress note for a driver. Write 2–3 sentences maximum. Be specific about the numbers. Be encouraging but honest. Do not use bullet points.

This week vs last week (same car and track):
- Best lap improvement: {stats.get('delta', '?')}s ({stats.get('direction', '?')})
- Sector 1 trend: {stats.get('s1_trend', '?')}
- Sector 2 trend: {stats.get('s2_trend', '?')}
- Sector 3 trend: {stats.get('s3_trend', '?')}
- Tyre temp consistency: {stats.get('tyre_consistency', '?')}
- Sessions completed: {stats.get('session_count', '?')}
- Most-driven car: {stats.get('top_car', '?')}
- Most-driven track: {stats.get('top_track', '?')}

Write the progress note now."""

    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    resp = await _post(payload)
    resp.raise_for_status()
    body = resp.json()
    candidates = body.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned empty response for narrative")
    return candidates[0]["content"]["parts"][0]["text"].strip()


async def test_api_key(key: str) -> dict:
    """Returns {"ok": True} or {"ok": False, "error": "<Gemini's actual message>"}."""
    payload = {"contents": [{"parts": [{"text": "Say OK"}]}]}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(f"{GEMINI_API_URL}?key={key}", json=payload)
    if resp.status_code == 200:
        return {"ok": True}
    try:
        body = resp.json()
        message = body.get("error", {}).get("message", resp.text)
    except Exception:
        message = resp.text
    return {"ok": False, "error": f"HTTP {resp.status_code}: {message}"}
