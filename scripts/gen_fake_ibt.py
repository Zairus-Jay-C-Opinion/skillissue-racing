"""
Fake IBT dropper for testing the file watcher + parser pipeline.

Instead of generating a real binary IBT file (which requires replicating iRacing's
binary format exactly), this script patches the ibt_parser module with a mock that
returns synthetic data, then calls the watcher's process function directly.

Run:
    python -m scripts.gen_fake_ibt
    python -m scripts.gen_fake_ibt --car "Ferrari 296 GT3" --track "Spa-Francorchamps"
    python -m scripts.gen_fake_ibt --drop   # writes a dummy .ibt file to the watch folder
                                            # (triggers the real file watcher if it's running)
"""

import sys
import os
import json
import math
import random
import argparse
import tempfile
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

# Ensure repo root is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── Mock pyirsdk IBT object ────────────────────────────────────────────────────

class FakeIBT:
    """
    Simulates what irsdk.IBT returns after ir.open(filepath).
    ibt_parser.py calls ir[channel_name] which returns a list of floats, and
    reads session YAML + var headers straight off _shared_mem/_header/
    _var_headers_dict — mirrors the real (undocumented) IBT class shape,
    since this pyirsdk version has no public session_info/var_headers_dict.
    """

    def __init__(self, car: str, track: str, laps: int = 12, best_lap: float = 139.2):
        self.car = car
        self.track = track
        self.laps = laps
        self.best_lap = best_lap
        self._frames = self._generate_frames()

        # Raw YAML block, laid out the way ibt_parser._read_ibt_session_info reads it
        yaml_text = (
            "---\n"
            "WeekendInfo:\n"
            f" CarName: {car}\n"
            f" TrackDisplayName: {track}\n"
            " WeekendOptions:\n"
            f"  Date: {datetime.now().strftime('%Y-%m-%d')}\n"
            "DriverInfo:\n"
            " Drivers: []\n"
        )
        raw = yaml_text.encode("utf-8")
        self._shared_mem = raw + b"\x00" * 16
        self._header = SimpleNamespace(session_info_offset=0, session_info_len=len(raw))

        # name -> VarHeader-like object; real pyirsdk exposes .count as an attribute, not a dict key
        self._var_headers_dict = {ch: SimpleNamespace(count=len(self._frames[ch])) for ch in self._frames}

    def _generate_frames(self) -> dict:
        """
        Generate ~60Hz data for self.laps laps.
        Each lap is approximately self.best_lap seconds long.
        """
        hz = 60
        frames_per_lap = int(self.best_lap * hz)
        total_frames = frames_per_lap * self.laps

        lap_nums = []
        session_time = []
        dist_pct = []
        throttle = []
        brake = []
        speed = []
        rpm = []
        gear_ch = []
        lap_current = []
        lap_last = []
        lap_best_ch = []

        # Tyre temp channels (warm up from cold over first 3 laps)
        tyre = {ch: [] for ch in [
            "LFtempCL", "LFtempCM", "LFtempCR",
            "RFtempCL", "RFtempCM", "RFtempCR",
            "LRtempCL", "LRtempCM", "LRtempCR",
            "RRtempCL", "RRtempCM", "RRtempCR",
            "LFwearM", "RFwearM", "LRwearM", "RRwearM",
        ]}

        running_best = self.best_lap + random.uniform(2, 5)

        for lap in range(self.laps):
            lap_time = self.best_lap + random.uniform(0, 3.5) if lap > 0 else self.best_lap + 5
            if lap_time < running_best:
                running_best = lap_time

            # Tyre temps: cold on outlap, warm up, stabilise
            warmup = min(1.0, lap / 3.0)
            t_base = 60 + 30 * warmup  # 60°C cold → 90°C warm

            for frame in range(frames_per_lap):
                i = lap * frames_per_lap + frame
                t = lap * self.best_lap + frame / hz
                frac = frame / frames_per_lap  # 0→1 within the lap

                # Sinusoidal driving pattern
                phase = frac * math.pi * 8
                spd = 80 + 100 * abs(math.sin(phase))
                thr = max(0.0, min(1.0, 0.5 + 0.5 * math.sin(phase)))
                brk = max(0.0, min(1.0, -0.3 * math.sin(phase + 1.2)))

                lap_nums.append(lap + 1)
                session_time.append(round(t, 4))
                dist_pct.append(round(frac, 4))
                throttle.append(round(thr, 3))
                brake.append(round(brk, 3))
                speed.append(round(spd / 3.6, 3))  # kph → m/s (iRacing uses m/s)
                rpm.append(int(3000 + 5000 * thr))
                gear_ch.append(max(1, min(6, int(spd / 55) + 1)))
                lap_current.append(round(frac * lap_time, 3))
                # LapLastLapTime only updates at lap boundary (first frame of new lap)
                lap_last.append(round(lap_time, 4) if frame == 0 and lap > 0 else 0.0)
                lap_best_ch.append(round(running_best, 4))

                # Tyre temps with small random variation
                for corner in ("LF", "RF", "LR", "RR"):
                    temp = round(t_base + random.uniform(-3, 3), 1)
                    for zone in ("CL", "CM", "CR"):
                        tyre[f"{corner}temp{zone}"].append(temp + random.uniform(-1.5, 1.5))
                    wear = round(1.0 - (i / (self.laps * frames_per_lap)) * 0.05, 4)
                    tyre[f"{corner}wearM"].append(wear)

        channels = {
            "Lap": lap_nums,
            "SessionTime": session_time,
            "LapDistPct": dist_pct,
            "Throttle": throttle,
            "Brake": brake,
            "Speed": speed,
            "RPM": rpm,
            "Gear": gear_ch,
            "LapCurrentLapTime": lap_current,
            "LapLastLapTime": lap_last,
            "LapBestLapTime": lap_best_ch,
            "AirTemp": [20.5] * total_frames,
            "TrackTemp": [32.1] * total_frames,
            "WeatherType": [0] * total_frames,
            **tyre,
        }
        return channels

    def __getitem__(self, channel: str):
        return self._frames.get(channel, [])

    def open(self, path: str):
        pass  # no-op for mock

    def close(self):
        pass


# ── Patch irsdk and invoke parser ─────────────────────────────────────────────

def run_mock_parse(car: str, track: str, laps: int = 12, best_lap: float = 139.2) -> dict | None:
    """
    Monkeypatches irsdk so ibt_parser.py uses our FakeIBT class,
    then calls parse_ibt() on a dummy path. Returns the parsed session dict.
    """
    fake = FakeIBT(car=car, track=track, laps=laps, best_lap=best_lap)

    # Patch only the IBT constructor on the real irsdk module — ibt_parser.py
    # needs the real module's yaml/CustomYamlSafeLoader to actually parse the
    # session YAML, so we can't swap out all of sys.modules["irsdk"].
    import irsdk
    from agent.ibt_parser import parse_ibt

    # Write a dummy file so the size check passes
    with tempfile.NamedTemporaryFile(suffix=".ibt", delete=False) as f:
        f.write(b"\x00" * 20 * 1024)  # 20 KB dummy
        tmp_path = f.name

    try:
        with patch.object(irsdk, "IBT", return_value=fake):
            result = parse_ibt(tmp_path)
    finally:
        os.unlink(tmp_path)

    return result


def drop_dummy_ibt(folder: str):
    """
    Writes a 20KB dummy .ibt file to the watched folder.
    Useful for triggering the real file watcher — but the watcher
    will fail to parse it (it's not a real IBT). Combine with
    the mock approach for full end-to-end testing.
    """
    path = os.path.join(folder, f"test_drop_{int(datetime.now().timestamp())}.ibt")
    with open(path, "wb") as f:
        f.write(b"\x00" * 20 * 1024)
    print(f"Dropped dummy file: {path}")
    print("Note: the watcher will attempt to parse this. It will fail unless")
    print("pyirsdk is installed and you're running via the mock patch approach.")
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate fake IBT data for testing")
    parser.add_argument("--car", default="Ferrari 296 GT3")
    parser.add_argument("--track", default="Spa-Francorchamps")
    parser.add_argument("--laps", type=int, default=12)
    parser.add_argument("--best-lap", type=float, default=139.2, help="Best lap time in seconds")
    parser.add_argument("--upload", action="store_true", help="POST parsed result to backend")
    parser.add_argument("--drop", action="store_true", help="Drop a dummy .ibt file to the watch folder")
    args = parser.parse_args()

    if args.drop:
        # Read watch folder from backend settings
        try:
            import httpx
            s = httpx.get("http://localhost:8000/api/settings", timeout=3).json()
            folder = s.get("telemetry_folder", os.path.expanduser("~/Documents/iRacing/telemetry"))
        except Exception:
            folder = os.path.expanduser("~/Documents/iRacing/telemetry")
        drop_dummy_ibt(folder)
        return

    print(f"Generating fake IBT data: {args.car} @ {args.track} ({args.laps} laps, PB {args.best_lap}s)")
    result = run_mock_parse(args.car, args.track, args.laps, args.best_lap)

    if result is None:
        print("ERROR: parse returned None")
        sys.exit(1)

    print(f"\nParsed OK:")
    print(f"  Car:       {result['car_name']}")
    print(f"  Track:     {result['track_name']}")
    print(f"  Best lap:  {result['best_lap_time']}s")
    print(f"  Avg lap:   {result['avg_lap_time']}s")
    print(f"  Laps:      {result['lap_count']}")
    print(f"  Tyre laps: {len(result.get('tyre_laps', []))}")
    print(f"  Raw JSON:  {len(result.get('raw_json', ''))} chars")
    print(f"  Air/Track: {result['air_temp']}°C / {result['track_temp']}°C")
    print(f"  S1 best:   {result.get('sector_1_best')}s")
    print(f"  S2 best:   {result.get('sector_2_best')}s")
    print(f"  S3 best:   {result.get('sector_3_best')}s")

    if args.upload:
        import httpx
        resp = httpx.post("http://localhost:8000/api/sessions", json=result, timeout=30)
        if resp.status_code == 201:
            print(f"\nUploaded -> session id: {resp.json()['id']}")
        elif resp.status_code == 409:
            print("\nSession already exists in DB.")
        else:
            print(f"\nUpload failed: {resp.status_code} {resp.text}")


if __name__ == "__main__":
    main()
