#!/usr/bin/env python3
import argparse
import glob
import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_DIR / "tests" / "fixtures" / "compositor"

HYPRLAND_ADAPTER_STATUS = "fixture-only / unverified"

HYPRLAND_EVENTS = (
    "workspace>>",
    "workspacev2>>",
    "focusedmon>>",
    "focusedmonv2>>",
    "activewindow>>",
    "activewindowv2>>",
    "openwindow>>",
    "closewindow>>",
    "movewindow>>",
    "movewindowv2>>",
    "createworkspace>>",
    "createworkspacev2>>",
    "destroyworkspace>>",
    "destroyworkspacev2>>",
    "moveworkspace>>",
    "moveworkspacev2>>",
    "monitoradded>>",
    "monitorremoved>>",
)

STATIC_TABS = [
    {
        "id": "hydra",
        "tag": "8G",
        "title": "Hydra",
        "badge": "0-0-NE-01",
        "urgent": False,
    },
    {
        "id": "nebula",
        "tag": "UPD",
        "title": "Nebula",
        "badge": "SSWS",
        "urgent": True,
    },
    {
        "id": "spartim",
        "tag": "UPD",
        "title": "Spartim",
        "badge": "3C2E-0010",
        "urgent": True,
    },
    {
        "id": "gersfit",
        "tag": "UPD",
        "title": "Gersfit",
        "badge": "SCOREN",
        "urgent": True,
    },
]


def resolve_fixture_name(cli_fixture):
    if cli_fixture is not None and cli_fixture.strip():
        return cli_fixture.strip()
    env_fixture = os.environ.get("SHIELD_FIXTURE", "").strip()
    return env_fixture if env_fixture else None


def build_fallback_payload():
    workspaces = [{"id": 1, "state": "active"}]
    for i in range(2, 11):
        workspaces.append({"id": i, "state": "empty"})
    return {
        "backend": "none",
        "workspaces": workspaces,
        "tabs": STATIC_TABS,
        "windows": STATIC_TABS,
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


def find_niri_socket():
    if "NIRI_SOCKET" in os.environ:
        sock = os.environ.get("NIRI_SOCKET", "").strip()
        if sock and os.path.exists(sock):
            return sock
        return None
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    matches = sorted(glob.glob(f"{runtime_dir}/niri.*.sock"))
    if matches and os.path.exists(matches[0]):
        return matches[0]
    return None


def find_hyprland_socket():
    if "HYPRLAND_INSTANCE_SIGNATURE" not in os.environ:
        return None
    sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "").strip()
    if not sig:
        return None
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    candidates = [
        f"{runtime_dir}/hypr/{sig}/.socket2.sock",
        f"/tmp/hypr/{sig}/.socket2.sock",
    ]
    for sock in candidates:
        if os.path.exists(sock):
            return sock
    return None


def find_sway_socket():
    if "SWAYSOCK" in os.environ:
        sock = os.environ.get("SWAYSOCK", "").strip()
        if sock and os.path.exists(sock):
            return sock
        return None
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}"
    matches = sorted(glob.glob(f"{runtime_dir}/sway-ipc.*.sock"))
    if matches and os.path.exists(matches[0]):
        return matches[0]
    return None


def detect_backend():
    niri_sock = find_niri_socket()
    if niri_sock:
        return "niri", niri_sock
    hypr_sock = find_hyprland_socket()
    if hypr_sock:
        return "hyprland", hypr_sock
    sway_sock = find_sway_socket()
    if sway_sock:
        return "sway", sway_sock
    return "none", None


def query_niri(subcommand):
    try:
        proc = subprocess.run(
            ["niri", "msg", "--json"] + subcommand,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    return []


def build_niri_payload(workspaces_list, windows_list):
    windows_by_ws_id = set()
    for win in windows_list:
        if isinstance(win, dict):
            ws_id = win.get("workspace_id")
            if ws_id is not None:
                windows_by_ws_id.add(ws_id)

    slot_states = {i: "empty" for i in range(1, 11)}
    for ws in workspaces_list:
        if not isinstance(ws, dict):
            continue
        slot = None
        name = ws.get("name")
        if name and isinstance(name, str):
            m = re.match(r"^(\d+)", name.strip())
            if m:
                slot = int(m.group(1))
        if slot is None:
            slot = ws.get("idx")
        if slot is not None and 1 <= slot <= 10:
            ws_id = ws.get("id")
            is_occ = (ws_id in windows_by_ws_id) or (ws.get("active_window_id") is not None)
            if ws.get("is_active") or ws.get("is_focused"):
                slot_states[slot] = "active"
            elif is_occ and slot_states[slot] != "active":
                slot_states[slot] = "occupied"

    workspaces = [{"id": i, "state": slot_states[i]} for i in range(1, 11)]

    return {
        "backend": "niri",
        "workspaces": workspaces,
        "tabs": STATIC_TABS,
        "windows": STATIC_TABS,
    }


def extract_hyprland_slot(ws_obj):
    if not isinstance(ws_obj, dict):
        return None
    ws_id = ws_obj.get("id")
    if isinstance(ws_id, int) and 1 <= ws_id <= 10:
        return ws_id
    name = ws_obj.get("name")
    if name and isinstance(name, str):
        m = re.match(r"^(\d+)", name.strip())
        if m:
            slot = int(m.group(1))
            if 1 <= slot <= 10:
                return slot
    return None


def query_hyprland(subcommand):
    try:
        proc = subprocess.run(
            ["hyprctl", "-j", subcommand],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    return {} if subcommand == "activewindow" else []


def build_hyprland_payload(monitors_list, workspaces_list, active_window=None):
    slot_states = {i: "empty" for i in range(1, 11)}

    if isinstance(workspaces_list, list):
        for ws in workspaces_list:
            slot = extract_hyprland_slot(ws)
            if slot is not None:
                windows_count = ws.get("windows", 0)
                if isinstance(windows_count, int) and windows_count > 0:
                    slot_states[slot] = "occupied"

    if isinstance(active_window, dict) and (
        active_window.get("address")
        or active_window.get("class")
        or active_window.get("title")
    ):
        aw_slot = extract_hyprland_slot(active_window.get("workspace"))
        if aw_slot is not None and slot_states[aw_slot] == "empty":
            slot_states[aw_slot] = "occupied"

    if isinstance(monitors_list, list):
        for mon in monitors_list:
            if not isinstance(mon, dict):
                continue
            slot = extract_hyprland_slot(mon.get("activeWorkspace"))
            if slot is not None:
                slot_states[slot] = "active"

    workspaces = [{"id": i, "state": slot_states[i]} for i in range(1, 11)]

    return {
        "backend": "hyprland",
        "workspaces": workspaces,
        "tabs": STATIC_TABS,
        "windows": STATIC_TABS,
    }


def query_sway(msg_type):
    try:
        proc = subprocess.run(
            ["swaymsg", "-r", "-t", msg_type],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if proc.returncode == 0:
            return json.loads(proc.stdout)
    except Exception:
        pass
    return [] if msg_type == "get_workspaces" else {}


def find_occupied_in_sway_tree(tree_node, occupied_ws_nums):
    if not isinstance(tree_node, dict):
        return
    node_type = tree_node.get("type")
    if node_type == "workspace":
        num = tree_node.get("num")
        if num is None or num < 1:
            name = tree_node.get("name", "")
            m = re.match(r"^(\d+)", str(name).strip())
            if m:
                num = int(m.group(1))

        def has_window(n):
            if n.get("type") == "con" and (
                n.get("window") is not None
                or n.get("app_id") is not None
                or n.get("pid") is not None
            ):
                return True
            for child in n.get("nodes", []):
                if has_window(child):
                    return True
            for child in n.get("floating_nodes", []):
                if has_window(child):
                    return True
            return False

        if has_window(tree_node):
            if num is not None:
                occupied_ws_nums.add(num)
        return
    for child in tree_node.get("nodes", []):
        find_occupied_in_sway_tree(child, occupied_ws_nums)
    for child in tree_node.get("floating_nodes", []):
        find_occupied_in_sway_tree(child, occupied_ws_nums)


def build_sway_payload(workspaces_list, tree):
    occupied_ws_nums = set()
    find_occupied_in_sway_tree(tree, occupied_ws_nums)

    slot_states = {i: "empty" for i in range(1, 11)}
    for ws in workspaces_list:
        if not isinstance(ws, dict):
            continue
        num = ws.get("num")
        if num is None or num < 1:
            name = ws.get("name", "")
            m = re.match(r"^(\d+)", str(name).strip())
            if m:
                num = int(m.group(1))
        if num is not None and 1 <= num <= 10:
            has_nodes = (
                bool(ws.get("nodes"))
                or bool(ws.get("floating_nodes"))
                or bool(ws.get("representation"))
            )
            is_occ = (num in occupied_ws_nums) or has_nodes
            if ws.get("visible") or ws.get("focused"):
                slot_states[num] = "active"
            elif is_occ and slot_states[num] != "active":
                slot_states[num] = "occupied"

    workspaces = [{"id": i, "state": slot_states[i]} for i in range(1, 11)]

    return {
        "backend": "sway",
        "workspaces": workspaces,
        "tabs": STATIC_TABS,
        "windows": STATIC_TABS,
    }


def emit_json_line(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def stream_niri(once=False):
    workspaces = query_niri(["workspaces"])
    windows = query_niri(["windows"])
    payload = build_niri_payload(workspaces, windows)
    emit_json_line(payload)
    if once:
        return

    try:
        proc = subprocess.Popen(
            ["niri", "msg", "--json", "event-stream"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        while True:
            time.sleep(60)

    try:
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except Exception:
                continue

            changed = False
            if "WorkspacesChanged" in event:
                workspaces = event["WorkspacesChanged"].get("workspaces", [])
                changed = True
            elif "WindowsChanged" in event:
                windows = event["WindowsChanged"].get("windows", [])
                changed = True
            elif "WorkspaceActivated" in event:
                act_id = event["WorkspaceActivated"].get("id")
                target_out = None
                for ws in workspaces:
                    if ws.get("id") == act_id:
                        target_out = ws.get("output")
                        break
                for ws in workspaces:
                    if target_out is not None and ws.get("output") == target_out:
                        ws["is_active"] = (ws.get("id") == act_id)
                    elif ws.get("id") == act_id:
                        ws["is_active"] = True
                changed = True
            elif "WindowOpenedOrChanged" in event:
                new_win = event["WindowOpenedOrChanged"].get("window")
                if new_win and "id" in new_win:
                    windows = [w for w in windows if w.get("id") != new_win.get("id")]
                    windows.append(new_win)
                    changed = True
            elif "WindowClosed" in event:
                closed_id = event["WindowClosed"].get("id")
                if closed_id is not None:
                    windows = [w for w in windows if w.get("id") != closed_id]
                    changed = True

            if changed:
                payload = build_niri_payload(workspaces, windows)
                emit_json_line(payload)
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def stream_hyprland(sock_path, once=False):
    monitors = query_hyprland("monitors")
    workspaces = query_hyprland("workspaces")
    active_window = query_hyprland("activewindow")
    payload = build_hyprland_payload(monitors, workspaces, active_window)
    emit_json_line(payload)
    if once:
        return

    client = None
    sock_file = None
    try:
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.connect(sock_path)
        sock_file = client.makefile("r", encoding="utf-8", errors="replace")
    except Exception:
        while True:
            time.sleep(60)

    try:
        for raw_line in sock_file:
            line = raw_line.strip()
            if not line:
                continue
            if line.startswith(HYPRLAND_EVENTS):
                monitors = query_hyprland("monitors")
                workspaces = query_hyprland("workspaces")
                active_window = query_hyprland("activewindow")
                payload = build_hyprland_payload(monitors, workspaces, active_window)
                emit_json_line(payload)
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        if sock_file is not None:
            try:
                sock_file.close()
            except Exception:
                pass
        if client is not None:
            try:
                client.close()
            except Exception:
                pass


def stream_sway(once=False):
    workspaces = query_sway("get_workspaces")
    tree = query_sway("get_tree")
    payload = build_sway_payload(workspaces, tree)
    emit_json_line(payload)
    if once:
        return

    try:
        proc = subprocess.Popen(
            ["swaymsg", "-m", "-r", "-t", "subscribe", '["workspace","window"]'],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except Exception:
        while True:
            time.sleep(60)

    try:
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            workspaces = query_sway("get_workspaces")
            tree = query_sway("get_tree")
            payload = build_sway_payload(workspaces, tree)
            emit_json_line(payload)
    except (KeyboardInterrupt, BrokenPipeError):
        pass
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser(description="S.H.I.E.L.D. OS HUD compositor stream")
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

    backend, sock = detect_backend()
    if backend == "niri":
        if sock and "NIRI_SOCKET" not in os.environ:
            os.environ["NIRI_SOCKET"] = sock
        stream_niri(once=args.once)
        return 0
    elif backend == "hyprland":
        stream_hyprland(sock, once=args.once)
        return 0
    elif backend == "sway":
        if sock and "SWAYSOCK" not in os.environ:
            os.environ["SWAYSOCK"] = sock
        stream_sway(once=args.once)
        return 0
    else:
        payload = build_fallback_payload()
        emit_json_line(payload)
        if args.once:
            return 0
        try:
            while True:
                time.sleep(60)
        except (KeyboardInterrupt, BrokenPipeError):
            return 0


if __name__ == "__main__":
    sys.exit(main())
