#!/usr/bin/env python3
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
LAYOUT_PATH = REPO_DIR / "layout.json"
FIXTURE_DIR = REPO_DIR / "tests" / "fixtures" / "exclusive-zone"

def fail(check_name, message):
    sys.stderr.write(f"FAIL [{check_name}]: {message}\n")
    sys.exit(1)

def main():
    if shutil.which("sway") is None and shutil.which("nix") is not None and (REPO_DIR / "flake.nix").is_file():
        os.execvpe("nix", ["nix", "develop", str(REPO_DIR), "-c", sys.executable, str(Path(__file__).resolve())] + sys.argv[1:], os.environ)

    if not LAYOUT_PATH.is_file():
        fail("exclusive-zone", f"layout.json not found at {LAYOUT_PATH}")

    try:
        layout = json.loads(LAYOUT_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("exclusive-zone", f"Failed to parse layout.json: {exc}")

    screen_w = int(layout["screen"]["width"])
    screen_h = int(layout["screen"]["height"])
    top_h = int(layout["bars"]["top"]["height"])
    bottom_h = int(layout["bars"]["bottom"]["height"])

    work_dir = tempfile.mkdtemp(prefix="shield-exclusive-")
    runtime_dir = Path(work_dir) / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.chmod(0o700)

    sway_cfg = Path(work_dir) / "sway.cfg"
    sway_cfg.write_text(f"output HEADLESS-1 resolution {screen_w}x{screen_h}\ndefault_border none\n", encoding="utf-8")

    env = os.environ.copy()
    env["XDG_RUNTIME_DIR"] = str(runtime_dir)
    env["WLR_BACKENDS"] = "headless"
    env["WLR_LIBINPUT_NO_DEVICES"] = "1"
    env["WLR_RENDERER"] = "pixman"

    sway_proc = subprocess.Popen(["sway", "-c", str(sway_cfg)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    eww_proc = None
    client_proc = None

    try:
        wayland_sock = None
        swaysock = None
        for _ in range(50):
            if sway_proc.poll() is not None:
                fail("exclusive-zone", f"Sway exited prematurely with code {sway_proc.returncode}")
            for entry in runtime_dir.iterdir():
                name = entry.name
                if name.startswith("wayland-") and not name.endswith(".lock") and entry.is_socket():
                    wayland_sock = name
                elif name.startswith("sway-ipc.") and name.endswith(".sock") and entry.is_socket():
                    swaysock = str(entry)
            if wayland_sock and swaysock:
                break
            time.sleep(0.1)

        if not wayland_sock or not swaysock:
            fail("exclusive-zone", "Timed out waiting for Sway Wayland socket / SWAYSOCK")

        env["WAYLAND_DISPLAY"] = wayland_sock
        env["SWAYSOCK"] = swaysock

        config_dir = REPO_DIR
        eww_proc = subprocess.Popen(["eww", "-c", str(config_dir), "daemon", "--no-daemonize"], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        ping_ok = False
        for _ in range(50):
            if eww_proc.poll() is not None:
                _, err = eww_proc.communicate()
                fail("exclusive-zone", f"Eww daemon exited prematurely: {err.decode('utf-8', errors='replace')}")
            ping = subprocess.run(["eww", "-c", str(config_dir), "ping"], env=env, capture_output=True, text=True)
            if ping.returncode == 0 and "pong" in ping.stdout:
                ping_ok = True
                break
            time.sleep(0.1)

        if not ping_ok:
            fail("exclusive-zone", "Timed out waiting for Eww daemon ping")

        has_bottom = False
        bottom_yuck = REPO_DIR / "yuck" / "bottom-bar.yuck"
        if bottom_yuck.is_file() and "bottom" in bottom_yuck.read_text(encoding="utf-8"):
            has_bottom = True

        windows_to_open = ["top"]
        if has_bottom:
            windows_to_open.append("bottom")

        open_res = subprocess.run(["eww", "-c", str(config_dir), "open-many"] + windows_to_open, env=env, capture_output=True, text=True)
        if open_res.returncode != 0:
            fail("exclusive-zone", f"Failed to open windows: {open_res.stderr.strip() or open_res.stdout.strip()}")

        time.sleep(0.5)

        active = subprocess.run(["eww", "-c", str(config_dir), "active-windows"], env=env, capture_output=True, text=True)
        active_windows = [line.split(":")[-1].strip() for line in active.stdout.splitlines() if line.strip()]
        for required_win in windows_to_open:
            if required_win not in active_windows:
                fail("exclusive-zone", f"Window '{required_win}' missing from active windows: {active.stdout.strip()}")

        foot_bin = shutil.which("foot")
        if not foot_bin:
            fail("exclusive-zone", "foot binary not found in PATH")

        client_proc = subprocess.Popen([foot_bin], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        client_rect = None
        for _ in range(50):
            if client_proc.poll() is not None:
                fail("exclusive-zone", f"Test client foot exited prematurely with code {client_proc.returncode}")
            try:
                tree_out = subprocess.check_output(["swaymsg", "-t", "get_tree"], env=env, text=True)
                tree_data = json.loads(tree_out)
            except Exception:
                time.sleep(0.1)
                continue

            def find_foot_rect(node):
                if node.get("app_id") == "foot":
                    return node.get("rect")
                for child in node.get("nodes", []):
                    found = find_foot_rect(child)
                    if found:
                        return found
                for child in node.get("floating_nodes", []):
                    found = find_foot_rect(child)
                    if found:
                        return found
                return None

            client_rect = find_foot_rect(tree_data)
            if client_rect:
                break
            time.sleep(0.1)

        if not client_rect:
            fail("exclusive-zone", "Timed out waiting for foot client window to register in Sway tree")

        cx = client_rect["x"]
        cy = client_rect["y"]
        cw = client_rect["width"]
        ch = client_rect["height"]

        if cy < top_h:
            fail("exclusive-zone", f"Tiled client overlaps top exclusive bar: client y={cy} < top bar height {top_h}")

        if has_bottom and (cy + ch) > (screen_h - bottom_h):
            fail("exclusive-zone", f"Tiled client overlaps bottom exclusive bar: client y+h={cy+ch} > screen.h-bottom.h {screen_h - bottom_h}")

        expected_y = top_h
        expected_h = screen_h - top_h - (bottom_h if has_bottom else 0)
        expected_w = screen_w

        if cy != expected_y or ch != expected_h or cw != expected_w:
            fail(
                "exclusive-zone",
                f"Client geometry mismatch: got (x={cx}, y={cy}, w={cw}, h={ch}), expected (x=0, y={expected_y}, w={expected_w}, h={expected_h})",
            )

        print(
            f"PASS [exclusive-zone]: Tiled client geometry x={cx} y={cy} w={cw} h={ch} "
            f"clears top bar ({top_h}px) with zero overlap."
        )
        return 0

    finally:
        if client_proc and client_proc.poll() is None:
            client_proc.terminate()
            try:
                client_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                client_proc.kill()

        if eww_proc and eww_proc.poll() is None:
            subprocess.run(["eww", "-c", str(config_dir), "kill"], env=env, capture_output=True)
            eww_proc.terminate()
            try:
                eww_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                eww_proc.kill()

        if sway_proc and sway_proc.poll() is None:
            sway_proc.terminate()
            try:
                sway_proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                sway_proc.kill()

        shutil.rmtree(work_dir, ignore_errors=True)

if __name__ == "__main__":
    sys.exit(main())
