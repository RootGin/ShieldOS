#!/usr/bin/env python3
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_DIR / "tests" / "fixtures" / "network-audio"


def resolve_fixture_name(cli_fixture):
    if cli_fixture is not None and cli_fixture.strip():
        return cli_fixture.strip()
    env_fixture = os.environ.get("SHIELD_FIXTURE", "").strip()
    return env_fixture if env_fixture else None


def build_fallback_payload():
    return {
        "connected": False,
        "label": "DISCONNECTED",
        "signal": 0,
        "audio_level": [0, 0, 0, 0],
        "muted": False,
        "volume": 0,
        "media": {
            "playing": False,
            "title": "",
            "artist": "",
            "progress": 0,
            "slots": 0,
        },
        "quick_tabs": {
            "mute": False,
            "dnd": False,
            "night_light": False,
        },
    }


def load_fixture_payload(fixture_name):
    if not fixture_name:
        return None
    fixture_path = FIXTURES_DIR / f"{fixture_name}.json"
    if fixture_path.is_file():
        try:
            return json.loads(fixture_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return build_fallback_payload()


def get_network_state():
    if shutil.which("nmcli"):
        try:
            proc = subprocess.run(
                ["nmcli", "-t", "-f", "active,ssid,signal", "dev", "wifi", "list", "--rescan", "no"],
                capture_output=True,
                text=True,
                timeout=1.5,
            )
            if proc.returncode == 0 and proc.stdout:
                for line in proc.stdout.splitlines():
                    parts = line.strip().split(":")
                    if len(parts) >= 3 and parts[0] in ("yes", "*"):
                        ssid = parts[1] if parts[1] else "WIFI"
                        try:
                            sig_pct = int(parts[2])
                        except ValueError:
                            sig_pct = 0
                        if sig_pct >= 75:
                            sig_val = 4
                        elif sig_pct >= 50:
                            sig_val = 3
                        elif sig_pct >= 25:
                            sig_val = 2
                        elif sig_pct > 0:
                            sig_val = 1
                        else:
                            sig_val = 0
                        return {"connected": True, "label": ssid, "signal": sig_val}
        except Exception:
            pass

        try:
            proc = subprocess.run(
                ["nmcli", "-t", "-f", "TYPE,STATE,CONNECTION", "dev"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if proc.returncode == 0 and proc.stdout:
                for line in proc.stdout.splitlines():
                    parts = line.strip().split(":")
                    if len(parts) >= 3 and parts[1].startswith("connected"):
                        conn_type = parts[0]
                        conn_name = parts[2] if parts[2] else conn_type.upper()
                        if conn_type != "loopback":
                            return {"connected": True, "label": conn_name, "signal": 4}
        except Exception:
            pass

    net_dir = Path("/sys/class/net")
    if net_dir.is_dir():
        try:
            for iface in net_dir.iterdir():
                if iface.name == "lo":
                    continue
                oper_file = iface / "operstate"
                if oper_file.is_file():
                    state = oper_file.read_text(encoding="utf-8").strip()
                    if state == "up":
                        return {"connected": True, "label": iface.name.upper(), "signal": 4}
        except Exception:
            pass

    return {"connected": False, "label": "DISCONNECTED", "signal": 0}


def get_audio_state():
    vol = 50
    muted = False
    if shutil.which("wpctl"):
        try:
            proc = subprocess.run(
                ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if proc.returncode == 0 and proc.stdout:
                line = proc.stdout.strip()
                muted = "[MUTED]" in line
                m = re.search(r"Volume:\s*([0-9.]+)", line)
                if m:
                    vol_float = float(m.group(1))
                    vol = max(0, min(100, int(round(vol_float * 100))))
        except Exception:
            pass
    return {"volume": vol, "muted": muted}


def get_media_state():
    media = {
        "playing": False,
        "title": "",
        "artist": "",
        "progress": 0,
        "slots": 0,
    }
    if shutil.which("playerctl"):
        try:
            status_proc = subprocess.run(
                ["playerctl", "status"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if status_proc.returncode == 0:
                st = status_proc.stdout.strip().lower()
                media["playing"] = (st == "playing")

                meta_proc = subprocess.run(
                    ["playerctl", "metadata", "--format", "{{title}}:::{{artist}}:::{{position}}:::{{mpris:length}}"],
                    capture_output=True,
                    text=True,
                    timeout=1.0,
                )
                if meta_proc.returncode == 0 and meta_proc.stdout:
                    parts = meta_proc.stdout.strip().split(":::")
                    if len(parts) >= 2:
                        media["title"] = parts[0].strip()
                        media["artist"] = parts[1].strip()
                    if len(parts) >= 4:
                        try:
                            pos = float(parts[2].strip())
                            length = float(parts[3].strip())
                            if length > 0:
                                pct = max(0, min(100, int(round((pos / length) * 100))))
                                media["progress"] = pct
                                media["slots"] = max(0, min(10, int(round(pct / 10))))
                        except (ValueError, TypeError):
                            pass
        except Exception:
            pass
    return media


def build_live_payload(audio_bars=None):
    net = get_network_state()
    audio = get_audio_state()
    media = get_media_state()
    bars = audio_bars if audio_bars is not None else [0, 0, 0, 0]
    return {
        "connected": net["connected"],
        "label": net["label"],
        "signal": net["signal"],
        "audio_level": bars,
        "muted": audio["muted"],
        "volume": audio["volume"],
        "media": media,
        "quick_tabs": {
            "mute": audio["muted"],
            "dnd": False,
            "night_light": False,
        },
    }


def parse_cava_line(line):
    parts = [p.strip() for p in line.strip().split(";") if p.strip()]
    if len(parts) >= 4:
        try:
            return [max(0, min(100, int(x))) for x in parts[:4]]
        except ValueError:
            pass
    return [0, 0, 0, 0]


def spawn_cava():
    if not shutil.which("cava"):
        return None, None
    try:
        tmp_cfg = tempfile.NamedTemporaryFile("w", delete=False, prefix="cava_", suffix=".conf")
        tmp_cfg.write("[general]\nbars = 4\nframerate = 15\n[output]\nmethod = raw\nraw_target = /dev/stdout\ndata_format = ascii\nascii_max_range = 100\nbar_delimiter = 59\n")
        tmp_cfg.flush()
        tmp_cfg.close()
        proc = subprocess.Popen(
            ["cava", "-p", tmp_cfg.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        return proc, tmp_cfg.name
    except Exception:
        return None, None


def emit_json_line(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def stream_live(once=False):
    if once:
        payload = build_live_payload()
        emit_json_line(payload)
        return

    cava_proc, tmp_cfg_path = spawn_cava()
    last_meta_time = 0.0
    cached_payload = build_live_payload()
    emit_json_line(cached_payload)

    try:
        if cava_proc and cava_proc.stdout:
            while True:
                line = cava_proc.stdout.readline()
                if not line:
                    break
                now = time.monotonic()
                if now - last_meta_time >= 2.0:
                    cached_payload = build_live_payload()
                    last_meta_time = now
                cached_payload["audio_level"] = parse_cava_line(line)
                emit_json_line(cached_payload)
        while True:
            time.sleep(1.0)
            emit_json_line(build_live_payload())
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        if cava_proc:
            try:
                cava_proc.terminate()
                cava_proc.wait(timeout=1.0)
            except Exception:
                try:
                    cava_proc.kill()
                except Exception:
                    pass
        if tmp_cfg_path and os.path.exists(tmp_cfg_path):
            try:
                os.remove(tmp_cfg_path)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="S.H.I.E.L.D. OS HUD network and audio stream")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--fixture", type=str, default=None)
    args = parser.parse_args()

    fixture_name = resolve_fixture_name(args.fixture)
    if fixture_name:
        payload = load_fixture_payload(fixture_name)
        emit_json_line(payload)
        if args.once:
            return 0
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, BrokenPipeError):
            return 0

    stream_live(once=args.once)
    return 0


if __name__ == "__main__":
    sys.exit(main())
