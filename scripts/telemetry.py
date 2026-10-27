#!/usr/bin/env python3
import argparse
import datetime
import getpass
import json
import os
import re
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_DIR / "tests" / "fixtures" / "telemetry"
HUD_VERSION = "V0.1"


def resolve_fixture_name(cli_fixture):
    if cli_fixture is not None and cli_fixture.strip():
        return cli_fixture.strip()
    env_fixture = os.environ.get("SHIELD_FIXTURE", "").strip()
    return env_fixture if env_fixture else None


def load_fixture_inputs(fixture_name):
    if not fixture_name:
        return None
    fixture_path = FIXTURES_DIR / f"{fixture_name}.json"
    try:
        return json.loads(fixture_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "proc_root": "/nonexistent-proc-fallback",
            "timestamp": null_value(),
            "proc_stat_prev": None,
            "proc_stat": None,
            "proc_loadavg": None,
            "proc_meminfo": None,
            "proc_osrelease": None,
            "env_user": "",
        }


def null_value():
    return None


def read_proc_text(proc_root, rel_path, mocked_value=None, has_mock_key=False):
    if has_mock_key:
        if isinstance(mocked_value, str):
            return mocked_value
        try:
            return (Path(proc_root) / rel_path).read_text(encoding="utf-8")
        except Exception:
            return None
    try:
        return (Path(proc_root) / rel_path).read_text(encoding="utf-8")
    except Exception:
        return None


def parse_proc_stat(stat_text):
    if not stat_text:
        return None
    try:
        for line in stat_text.splitlines():
            parts = line.split()
            if parts and parts[0] == "cpu" and len(parts) >= 5:
                nums = [int(x) for x in parts[1:]]
                idle = nums[3] + (nums[4] if len(nums) > 4 else 0)
                total = sum(nums)
                if total > 0:
                    return (idle, total)
    except Exception:
        return None
    return None


def compute_cpu_percent(prev_sample, curr_sample):
    if not curr_sample:
        return 0
    if not prev_sample:
        idle, total = curr_sample
        if total <= 0:
            return 0
        return max(0, min(100, int(round((1.0 - (idle / total)) * 100))))
    prev_idle, prev_total = prev_sample
    curr_idle, curr_total = curr_sample
    diff_idle = curr_idle - prev_idle
    diff_total = curr_total - prev_total
    if diff_total <= 0:
        return 0
    return max(0, min(100, int(round((1.0 - (diff_idle / diff_total)) * 100))))


def parse_proc_loadavg(loadavg_text):
    if not loadavg_text:
        return 0.0
    try:
        first_token = loadavg_text.strip().split()[0]
        val = round(float(first_token), 2)
        return val if val >= 0.0 else 0.0
    except Exception:
        return 0.0


def parse_proc_meminfo(meminfo_text):
    if not meminfo_text:
        return 0
    try:
        total_match = re.search(r"^MemTotal:\s+(\d+)", meminfo_text, re.MULTILINE)
        avail_match = re.search(r"^MemAvailable:\s+(\d+)", meminfo_text, re.MULTILINE)
        if not total_match or not avail_match:
            return 0
        total_kb = int(total_match.group(1))
        avail_kb = int(avail_match.group(1))
        if total_kb <= 0:
            return 0
        used_ratio = 1.0 - (avail_kb / total_kb)
        return max(0, min(100, int(round(used_ratio * 100))))
    except Exception:
        return 0


def parse_kernel_release(osrelease_text):
    if osrelease_text:
        cleaned = osrelease_text.strip()
        if cleaned:
            return cleaned
    return "UNKNOWN"


def resolve_user(fixture_inputs):
    raw_user = None
    if fixture_inputs is not None and "env_user" in fixture_inputs:
        raw_user = fixture_inputs.get("env_user")
    else:
        raw_user = os.environ.get("USER") or os.environ.get("LOGNAME")
        if not raw_user:
            try:
                raw_user = getpass.getuser()
            except Exception:
                raw_user = None
    if isinstance(raw_user, str) and raw_user.strip():
        return raw_user.strip().upper()
    return "OPERATOR"


def format_clock_fields(fixture_inputs):
    dt = None
    if fixture_inputs is not None and "timestamp" in fixture_inputs:
        ts = fixture_inputs.get("timestamp")
        if isinstance(ts, str) and ts.strip():
            try:
                dt = datetime.datetime.fromisoformat(ts.strip())
            except Exception:
                dt = None
        elif isinstance(ts, (int, float)):
            try:
                dt = datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
            except Exception:
                dt = None
        else:
            dt = datetime.datetime(1970, 1, 1, 0, 0, 0)
    if dt is None:
        dt = datetime.datetime.now()
    return {
        "time": dt.strftime("%H:%M:%S"),
        "day": dt.strftime("%d"),
        "month_year": f"{dt.strftime('%b').upper()} - {dt.strftime('%Y')}",
        "weekday": dt.strftime("%a").upper(),
    }


def collect_metrics(fixture_inputs, prev_cpu_sample):
    proc_root = os.environ.get("SHIELD_PROC_ROOT", "/proc")
    if fixture_inputs is not None and fixture_inputs.get("proc_root"):
        proc_root = str(fixture_inputs["proc_root"])

    has_mock_prev = fixture_inputs is not None and "proc_stat_prev" in fixture_inputs
    has_mock_stat = fixture_inputs is not None and "proc_stat" in fixture_inputs
    has_mock_load = fixture_inputs is not None and "proc_loadavg" in fixture_inputs
    has_mock_mem = fixture_inputs is not None and "proc_meminfo" in fixture_inputs
    has_mock_osrel = fixture_inputs is not None and "proc_osrelease" in fixture_inputs

    if has_mock_prev:
        prev_text = read_proc_text(proc_root, "stat", fixture_inputs.get("proc_stat_prev"), True)
        prev_cpu_sample = parse_proc_stat(prev_text)

    stat_text = read_proc_text(
        proc_root,
        "stat",
        fixture_inputs.get("proc_stat") if has_mock_stat else None,
        has_mock_stat,
    )
    curr_cpu_sample = parse_proc_stat(stat_text)

    if prev_cpu_sample is None and curr_cpu_sample is not None and fixture_inputs is None:
        time.sleep(0.05)
        second_text = read_proc_text(proc_root, "stat")
        second_sample = parse_proc_stat(second_text)
        if second_sample is not None:
            prev_cpu_sample, curr_cpu_sample = curr_cpu_sample, second_sample

    cpu_percent = compute_cpu_percent(prev_cpu_sample, curr_cpu_sample)

    load_text = read_proc_text(
        proc_root,
        "loadavg",
        fixture_inputs.get("proc_loadavg") if has_mock_load else None,
        has_mock_load,
    )
    cpu_load = parse_proc_loadavg(load_text)

    mem_text = read_proc_text(
        proc_root,
        "meminfo",
        fixture_inputs.get("proc_meminfo") if has_mock_mem else None,
        has_mock_mem,
    )
    ram_percent = parse_proc_meminfo(mem_text)

    osrel_text = read_proc_text(
        proc_root,
        "sys/kernel/osrelease",
        fixture_inputs.get("proc_osrelease") if has_mock_osrel else None,
        has_mock_osrel,
    )
    kernel = parse_kernel_release(osrel_text)

    return {
        "cpu_percent": cpu_percent,
        "cpu_load": cpu_load,
        "ram_percent": ram_percent,
        "kernel": kernel,
    }, curr_cpu_sample


def build_payload(fixture_inputs, cached_metrics):
    clock = format_clock_fields(fixture_inputs)
    user = resolve_user(fixture_inputs)
    return {
        "time": clock["time"],
        "day": clock["day"],
        "month_year": clock["month_year"],
        "weekday": clock["weekday"],
        "cpu_percent": cached_metrics["cpu_percent"],
        "cpu_load": cached_metrics["cpu_load"],
        "ram_percent": cached_metrics["ram_percent"],
        "user": user,
        "kernel": cached_metrics["kernel"],
        "version": HUD_VERSION,
    }


def emit_json_line(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def main():
    parser = argparse.ArgumentParser(description="S.H.I.E.L.D. OS HUD telemetry stream")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--fixture", type=str, default=None)
    args = parser.parse_args()

    fixture_name = resolve_fixture_name(args.fixture)
    fixture_inputs = load_fixture_inputs(fixture_name)

    prev_cpu_sample = None
    cached_metrics, prev_cpu_sample = collect_metrics(fixture_inputs, prev_cpu_sample)

    if args.once:
        payload = build_payload(fixture_inputs, cached_metrics)
        emit_json_line(payload)
        return 0

    last_refresh = time.monotonic()
    try:
        while True:
            now_mono = time.monotonic()
            if now_mono - last_refresh >= 2.0:
                cached_metrics, prev_cpu_sample = collect_metrics(fixture_inputs, prev_cpu_sample)
                last_refresh = now_mono
            payload = build_payload(fixture_inputs, cached_metrics)
            emit_json_line(payload)
            time.sleep(1.0)
    except (KeyboardInterrupt, BrokenPipeError):
        return 0


if __name__ == "__main__":
    sys.exit(main())
