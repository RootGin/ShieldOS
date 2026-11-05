#!/usr/bin/env python3
import datetime
import glob
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
SCHEMA_PATH = REPO_DIR / "schemas" / "state.schema.json"
LAYOUT_PATH = REPO_DIR / "layout.json"
LAYOUT_SCHEMA_PATH = REPO_DIR / "schemas" / "layout.schema.json"

SCRIPT_REGISTRY = [
    {
        "name": "telemetry",
        "script": "scripts/telemetry.py",
        "schema_def": "telemetry",
        "status": "ACTIVE",
        "milestone": "Milestone 1",
        "fixtures": ["frozen", "fallback"],
    },
    {
        "name": "compositor",
        "script": "scripts/compositor.py",
        "schema_def": "compositor",
        "status": "ACTIVE",
        "milestone": "Milestone 4",
        "fixtures": ["frozen", "fallback", "niri", "hyprland", "sway"],
    },
    {
        "name": "network_audio",
        "script": "scripts/network-audio.py",
        "schema_def": "network_audio",
        "status": "ACTIVE",
        "milestone": "Milestone 6",
        "fixtures": ["connected", "disconnected", "audio", "frozen", "fallback"],
    },
]

CHAIN_PATTERN = re.compile(
    r"(?<![a-zA-Z0-9_/.-])(telemetry|compositor|network_audio)((?:\??\.[a-zA-Z_][a-zA-Z0-9_]*|\[\d+\]|\[[a-zA-Z_][a-zA-Z0-9_]*\])+)"
)
STEP_PATTERN = re.compile(r"\??\.([a-zA-Z_][a-zA-Z0-9_]*)|\[(\d+|[a-zA-Z_][a-zA-Z0-9_]*)\]")


def fail(check_name, message):
    sys.stderr.write(f"FAIL [{check_name}]: {message}\n")
    sys.exit(1)


def load_and_verify_schema(schema_path):
    if not schema_path.is_file():
        fail("schema-load", f"Schema file not found: {schema_path}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("schema-load", f"Invalid JSON in {schema_path}: {exc}")

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        fail("schema-meta", f"Schema failed Draft 2020-12 meta-validation: {exc}")

    defs = schema.get("$defs", {})
    for required_def in ("telemetry", "compositor", "network_audio"):
        if required_def not in defs:
            fail("schema-defs", f"Missing required $defs entry '{required_def}' in {schema_path.name}")

    def check_strict_objects(node, path="root"):
        if isinstance(node, dict):
            if node.get("type") == "object":
                if node.get("additionalProperties") is not False:
                    fail("schema-strict", f"Object at '{path}' must set additionalProperties: false")
                req = node.get("required")
                if not isinstance(req, list) or len(req) == 0:
                    fail("schema-strict", f"Object at '{path}' must list required fields")
            for k, v in node.items():
                check_strict_objects(v, f"{path}.{k}")
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                check_strict_objects(item, f"{path}[{idx}]")

    check_strict_objects(schema)
    return schema


def resolve_subschema(schema, node):
    while "$ref" in node:
        ref = node["$ref"]
        if not ref.startswith("#/"):
            fail("schema-ref", f"Unsupported external $ref: {ref}")
        target = schema
        for part in ref[2:].split("/"):
            target = target[part]
        node = target
    return node


def validate_yuck_chain(schema, root_var, chain_tail, source_label):
    defs = schema["$defs"]
    current = resolve_subschema(schema, defs[root_var])
    traversed = root_var

    for match in STEP_PATTERN.finditer(chain_tail):
        prop_name, idx_token = match.group(1), match.group(2)
        current = resolve_subschema(schema, current)
        if prop_name is not None:
            if current.get("type") != "object":
                fail(
                    "yuck-field-ref",
                    f"{source_label}: Cannot access property '.{prop_name}' on non-object '{traversed}' (type={current.get('type')})",
                )
            props = current.get("properties", {})
            if prop_name not in props:
                declared = ", ".join(sorted(props.keys()))
                fail(
                    "yuck-field-ref",
                    f"{source_label}: Undeclared field '{traversed}.{prop_name}' (declared on '{traversed}': [{declared}])",
                )
            current = props[prop_name]
            traversed = f"{traversed}.{prop_name}"
        elif idx_token is not None:
            if current.get("type") != "array":
                fail(
                    "yuck-field-ref",
                    f"{source_label}: Cannot index '[{idx_token}]' on non-array '{traversed}' (type={current.get('type')})",
                )
            if idx_token.isdigit():
                idx_val = int(idx_token)
                max_items = current.get("maxItems")
                if max_items is not None and (idx_val < 0 or idx_val >= max_items):
                    fail(
                        "yuck-field-ref",
                        f"{source_label}: Index out of bounds '{traversed}[{idx_val}]' (maxItems={max_items})",
                    )
            current = current.get("items", {})
            traversed = f"{traversed}[{idx_token}]"


def strip_single_quoted_strings(yuck_text):
    return re.sub(r"'[^']*'", "''", yuck_text)


def check_yuck_references(schema, yuck_files):
    checked_refs = 0
    for yuck_path in yuck_files:
        raw_text = yuck_path.read_text(encoding="utf-8")
        scan_text = strip_single_quoted_strings(raw_text)
        rel_label = yuck_path.relative_to(REPO_DIR) if yuck_path.is_relative_to(REPO_DIR) else yuck_path
        for match in CHAIN_PATTERN.finditer(scan_text):
            root_var = match.group(1)
            chain_tail = match.group(2)
            validate_yuck_chain(schema, root_var, chain_tail, str(rel_label))
            checked_refs += 1
    return checked_refs


def validate_payload_against_def(schema, def_name, payload, context_label):
    subschema = {
        "$schema": schema["$schema"],
        "$defs": schema["$defs"],
        "$ref": f"#/$defs/{def_name}",
    }
    validator = Draft202012Validator(subschema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        loc = ".".join(str(p) for p in err.path) or "<root>"
        fail("schema-validation", f"{context_label} failed schema '#/$defs/{def_name}' at '{loc}': {err.message}")


def run_script_fixture(script_path, fixture_name, def_name, schema, extra_env=None):
    cmd = [sys.executable, str(script_path), "--once", "--fixture", fixture_name]
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(cmd, cwd=str(REPO_DIR), env=env, capture_output=True, text=True, timeout=5)
    context_label = f"{script_path.relative_to(REPO_DIR)} --once --fixture {fixture_name}"

    if proc.returncode != 0:
        fail("script-exit", f"{context_label} exited with code {proc.returncode}: {proc.stderr.strip()}")

    raw_lines = proc.stdout.splitlines()
    if len(raw_lines) != 1 or not proc.stdout.endswith("\n"):
        fail("script-lines", f"{context_label} must print exactly 1 newline-terminated line, got {len(raw_lines)} lines")

    line = raw_lines[0]
    try:
        payload = json.loads(line)
    except Exception as exc:
        fail("script-json", f"{context_label} emitted invalid JSON: {exc} (line={line!r})")

    validate_payload_against_def(schema, def_name, payload, context_label)
    return payload


def run_env_fixture_precedence_check(script_path, schema):
    env = os.environ.copy()
    env["SHIELD_FIXTURE"] = "frozen"
    proc_env = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc_env.returncode != 0:
        fail("fixture-env", f"SHIELD_FIXTURE=frozen {script_path.name} --once exited {proc_env.returncode}")
    lines = proc_env.stdout.splitlines()
    if len(lines) != 1:
        fail("fixture-env", f"SHIELD_FIXTURE=frozen {script_path.name} --once printed {len(lines)} lines")
    env_payload = json.loads(lines[0])
    validate_payload_against_def(schema, "telemetry", env_payload, "SHIELD_FIXTURE=frozen telemetry.py --once")
    if env_payload.get("time") != "17:32:14" or env_payload.get("cpu_percent") != 2 or env_payload.get("ram_percent") != 42:
        fail("fixture-env", f"SHIELD_FIXTURE=frozen produced unexpected values: {env_payload}")
    cpu_lad = env_payload.get("cpu_ladder", {})
    if cpu_lad.get("bucket") != 0 or not cpu_lad.get("rungs") or cpu_lad["rungs"][-1].get("label") != "2" or cpu_lad["rungs"][-1].get("sublabel") != "1.0" or cpu_lad["rungs"][-1].get("state") != "active":
        fail("fixture-env-cpu-ladder", f"SHIELD_FIXTURE=frozen unexpected cpu_ladder: {cpu_lad}")
    ram_lad = env_payload.get("ram_ladder", {})
    if ram_lad.get("bucket") != 40 or not ram_lad.get("rungs") or ram_lad["rungs"][2].get("label") != "42" or ram_lad["rungs"][2].get("state") != "active":
        fail("fixture-env-ram-ladder", f"SHIELD_FIXTURE=frozen unexpected ram_ladder: {ram_lad}")

    env_override = os.environ.copy()
    env_override["SHIELD_FIXTURE"] = "fallback"
    override_payload = run_script_fixture(
        script_path,
        "frozen",
        "telemetry",
        schema,
        extra_env={"SHIELD_FIXTURE": "fallback"},
    )
    if override_payload.get("time") != "17:32:14" or override_payload.get("cpu_percent") != 2:
        fail("fixture-precedence", f"--fixture frozen did not override SHIELD_FIXTURE=fallback: {override_payload}")


def run_production_proc_fallback_check(script_path, schema):
    env = os.environ.copy()
    env.pop("SHIELD_FIXTURE", None)
    env["SHIELD_PROC_ROOT"] = "/nonexistent-proc-fallback"
    proc = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc.returncode != 0:
        fail("production-proc-fallback", f"{script_path.name} --once with unreadable /proc exited {proc.returncode}: {proc.stderr}")
    lines = proc.stdout.splitlines()
    if len(lines) != 1:
        fail("production-proc-fallback", f"{script_path.name} printed {len(lines)} lines")
    payload = json.loads(lines[0])
    validate_payload_against_def(schema, "telemetry", payload, "production unreadable /proc")
    if payload.get("cpu_percent") != 0 or payload.get("ram_percent") != 0 or payload.get("kernel") != "UNKNOWN":
        fail("production-proc-fallback", f"Unexpected metrics on unreadable /proc: {payload}")
    now = datetime.datetime.now()
    if payload.get("day") != now.strftime("%d"):
        fail("production-proc-fallback", f"Expected real day {now.strftime('%d')}, got {payload.get('day')}")
    if payload.get("month_year") != f"{now.strftime('%b').upper()} - {now.strftime('%Y')}":
        fail("production-proc-fallback", f"Expected real month_year, got {payload.get('month_year')}")
    if payload.get("weekday") != now.strftime("%a").upper():
        fail("production-proc-fallback", f"Expected real weekday, got {payload.get('weekday')}")


def run_ladder_gauge_boundary_checks(schema):
    import importlib.util
    telem_script = REPO_DIR / "scripts" / "telemetry.py"
    spec = importlib.util.spec_from_file_location("telemetry_mod", str(telem_script))
    telem_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(telem_mod)

    boundary_cases = [
        (0, 0),
        (19, 0),
        (20, 20),
        (100, 100),
    ]

    for pct, expected_bucket in boundary_cases:
        actual_bucket = telem_mod.compute_percent_bucket(pct)
        if actual_bucket != expected_bucket:
            fail("ladder-bucket-boundary", f"compute_percent_bucket({pct}) expected {expected_bucket}, got {actual_bucket}")

        cpu_ladder = telem_mod.build_cpu_ladder(pct, 1.0)
        validate_payload_against_def(schema, "ladder_gauge", cpu_ladder, f"cpu_ladder boundary {pct}%")
        if cpu_ladder["bucket"] != expected_bucket:
            fail("ladder-bucket-boundary", f"build_cpu_ladder({pct}) bucket expected {expected_bucket}, got {cpu_ladder['bucket']}")

        ram_ladder = telem_mod.build_ram_ladder(pct)
        validate_payload_against_def(schema, "ladder_gauge", ram_ladder, f"ram_ladder boundary {pct}%")
        if ram_ladder["bucket"] != expected_bucket:
            fail("ladder-bucket-boundary", f"build_ram_ladder({pct}) bucket expected {expected_bucket}, got {ram_ladder['bucket']}")

    print("VALIDATED [ladder-boundary]: tested boundary values 0%, 19%, 20%, and 100% OK")


def run_compositor_checks(script_path, schema):
    env = os.environ.copy()
    env["SHIELD_FIXTURE"] = "frozen"
    proc_env = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc_env.returncode != 0:
        fail("fixture-env-compositor", f"SHIELD_FIXTURE=frozen {script_path.name} --once exited {proc_env.returncode}")
    lines = proc_env.stdout.splitlines()
    if len(lines) != 1:
        fail("fixture-env-compositor", f"SHIELD_FIXTURE=frozen {script_path.name} --once printed {len(lines)} lines")
    env_payload = json.loads(lines[0])
    validate_payload_against_def(schema, "compositor", env_payload, "SHIELD_FIXTURE=frozen compositor.py --once")
    ws_map = {ws["id"]: ws["state"] for ws in env_payload.get("workspaces", [])}
    if ws_map.get(2) != "active" or ws_map.get(8) != "active":
        fail("fixture-env-compositor", f"SHIELD_FIXTURE=frozen workspaces 2 and 8 must be active: {ws_map}")

    env_hypr = os.environ.copy()
    env_hypr["SHIELD_FIXTURE"] = "hyprland"
    proc_hypr = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env_hypr,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc_hypr.returncode != 0:
        fail("fixture-env-hyprland", f"SHIELD_FIXTURE=hyprland {script_path.name} --once exited {proc_hypr.returncode}")
    hypr_lines = proc_hypr.stdout.splitlines()
    if len(hypr_lines) != 1:
        fail("fixture-env-hyprland", f"SHIELD_FIXTURE=hyprland {script_path.name} --once printed {len(hypr_lines)} lines")
    hypr_env_payload = json.loads(hypr_lines[0])
    validate_payload_against_def(schema, "compositor", hypr_env_payload, "SHIELD_FIXTURE=hyprland compositor.py --once")
    if hypr_env_payload.get("backend") != "hyprland":
        fail("fixture-env-hyprland", f"Expected backend 'hyprland', got {hypr_env_payload.get('backend')}")

    env_override = os.environ.copy()
    env_override["SHIELD_FIXTURE"] = "fallback"
    override_payload = run_script_fixture(
        script_path,
        "frozen",
        "compositor",
        schema,
        extra_env={"SHIELD_FIXTURE": "fallback"},
    )
    ws_override_map = {ws["id"]: ws["state"] for ws in override_payload.get("workspaces", [])}
    if ws_override_map.get(2) != "active" or ws_override_map.get(8) != "active":
        fail("fixture-precedence-compositor", f"--fixture frozen did not override SHIELD_FIXTURE=fallback: {override_payload}")

    env_fallback = os.environ.copy()
    env_fallback.pop("SHIELD_FIXTURE", None)
    env_fallback["NIRI_SOCKET"] = ""
    env_fallback["HYPRLAND_INSTANCE_SIGNATURE"] = ""
    env_fallback["SWAYSOCK"] = ""
    proc_fallback = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env_fallback,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc_fallback.returncode != 0:
        fail("compositor-fallback", f"{script_path.name} fallback exited {proc_fallback.returncode}: {proc_fallback.stderr}")
    fallback_lines = proc_fallback.stdout.splitlines()
    if len(fallback_lines) != 1:
        fail("compositor-fallback", f"{script_path.name} fallback printed {len(fallback_lines)} lines")
    fallback_payload = json.loads(fallback_lines[0])
    validate_payload_against_def(schema, "compositor", fallback_payload, "compositor standalone fallback")
    if fallback_payload.get("backend") != "none":
        fail("compositor-fallback", f"Expected backend 'none' in standalone fallback, got {fallback_payload.get('backend')}")
    fb_ws_map = {ws["id"]: ws["state"] for ws in fallback_payload.get("workspaces", [])}
    if fb_ws_map.get(1) != "active":
        fail("compositor-fallback", f"Expected workspace 1 to be 'active' in standalone fallback, got: {fb_ws_map}")

    import importlib.util
    spec = importlib.util.spec_from_file_location("compositor_mod", str(script_path))
    comp_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(comp_mod)

    if getattr(comp_mod, "HYPRLAND_ADAPTER_STATUS", None) != "fixture-only / unverified":
        fail(
            "compositor-hyprland-status",
            f"Expected HYPRLAND_ADAPTER_STATUS='fixture-only / unverified', got {getattr(comp_mod, 'HYPRLAND_ADAPTER_STATUS', None)!r}",
        )

    niri_dual = comp_mod.build_niri_payload(
        [
            {"id": 10, "idx": 2, "output": "DP-1", "is_active": True, "is_focused": True, "active_window_id": 101},
            {"id": 20, "idx": 8, "output": "DP-2", "is_active": True, "is_focused": False, "active_window_id": None},
            {"id": 30, "idx": 4, "output": "DP-1", "is_active": False, "is_focused": False, "active_window_id": 102},
        ],
        [{"id": 101, "workspace_id": 10}, {"id": 102, "workspace_id": 30}],
    )
    validate_payload_against_def(schema, "compositor", niri_dual, "niri multi-monitor mapping")
    niri_map = {ws["id"]: ws["state"] for ws in niri_dual["workspaces"]}
    if niri_map.get(2) != "active" or niri_map.get(8) != "active" or niri_map.get(4) != "occupied" or niri_map.get(1) != "empty":
        fail("compositor-niri-mapping", f"Unexpected niri multi-monitor mapping: {niri_map}")

    hypr_dual = comp_mod.build_hyprland_payload(
        [
            {"id": 0, "name": "DP-1", "activeWorkspace": {"id": 2, "name": "2"}},
            {"id": 1, "name": "DP-2", "activeWorkspace": {"id": 8, "name": "8"}},
        ],
        [
            {"id": 2, "name": "2", "windows": 1},
            {"id": 4, "name": "4", "windows": 2},
            {"id": 8, "name": "8", "windows": 0},
        ],
        {"address": "0x1234", "workspace": {"id": 2, "name": "2"}},
    )
    validate_payload_against_def(schema, "compositor", hypr_dual, "hyprland multi-monitor mapping")
    hypr_map = {ws["id"]: ws["state"] for ws in hypr_dual["workspaces"]}
    if hypr_map.get(2) != "active" or hypr_map.get(8) != "active" or hypr_map.get(4) != "occupied" or hypr_map.get(1) != "empty":
        fail("compositor-hyprland-mapping", f"Unexpected hyprland multi-monitor mapping: {hypr_map}")

    sway_dual = comp_mod.build_sway_payload(
        [
            {"num": 2, "name": "2", "visible": True, "focused": True, "nodes": []},
            {"num": 8, "name": "8", "visible": True, "focused": False, "nodes": []},
            {"num": 4, "name": "4", "visible": False, "focused": False, "nodes": [{"id": 1}]},
        ],
        {},
    )
    validate_payload_against_def(schema, "compositor", sway_dual, "sway multi-monitor mapping")
    sway_map = {ws["id"]: ws["state"] for ws in sway_dual["workspaces"]}
    if sway_map.get(2) != "active" or sway_map.get(8) != "active" or sway_map.get(4) != "occupied" or sway_map.get(1) != "empty":
        fail("compositor-sway-mapping", f"Unexpected sway multi-monitor mapping: {sway_map}")


def run_shield_ctl_checks():
    shield_ctl_path = REPO_DIR / "bin" / "shield-ctl"
    if not shield_ctl_path.is_file():
        fail("shield-ctl-missing", f"CLI entrypoint not found: {shield_ctl_path}")
    if not os.access(shield_ctl_path, os.X_OK):
        fail("shield-ctl-executable", f"CLI entrypoint not executable: {shield_ctl_path}")

    cases = [
        (["--backend", "niri", "--dry-run", "workspace", "3"], {}, "niri msg action focus-workspace 3"),
        (["--backend", "niri", "--dry-run", "workspace", "next"], {}, "niri msg action focus-workspace-down"),
        (["--backend", "niri", "--dry-run", "workspace", "prev"], {}, "niri msg action focus-workspace-up"),
        (["--backend", "niri", "--dry-run", "focus", "42"], {}, "niri msg action focus-window --id 42"),
        (["workspace", "3", "--backend", "sway", "--dry-run"], {}, "swaymsg workspace number 3"),
        (["workspace", "next", "--backend", "sway", "--dry-run"], {}, "swaymsg workspace next"),
        (["workspace", "prev", "--backend", "sway", "--dry-run"], {}, "swaymsg workspace prev"),
        (["focus", "42", "--backend", "sway", "--dry-run"], {}, "swaymsg [con_id=42] focus"),
        (["--backend", "hyprland", "--dry-run", "workspace", "3"], {}, "hyprctl dispatch workspace 3"),
        (["--backend", "hyprland", "--dry-run", "workspace", "next"], {}, "hyprctl dispatch workspace e+1"),
        (["--backend", "hyprland", "--dry-run", "workspace", "prev"], {}, "hyprctl dispatch workspace e-1"),
        (["--backend", "hyprland", "--dry-run", "focus", "0x1234"], {}, "hyprctl dispatch focuswindow address:0x1234"),
        (["--backend", "hyprland", "--dry-run", "focus", "address:0x5678"], {}, "hyprctl dispatch focuswindow address:0x5678"),
        (["workspace", "2"], {"SHIELD_DRY_RUN": "1", "NIRI_SOCKET": "/mock/niri.sock", "SWAYSOCK": "", "HYPRLAND_INSTANCE_SIGNATURE": ""}, "niri msg action focus-workspace 2"),
        (["focus", "99"], {"SHIELD_DRY_RUN": "1", "NIRI_SOCKET": "/mock/niri.sock", "SWAYSOCK": "", "HYPRLAND_INSTANCE_SIGNATURE": ""}, "niri msg action focus-window --id 99"),
        (["workspace", "4"], {"SHIELD_DRY_RUN": "1", "NIRI_SOCKET": "", "SWAYSOCK": "/mock/sway.sock", "HYPRLAND_INSTANCE_SIGNATURE": ""}, "swaymsg workspace number 4"),
        (["focus", "88"], {"SHIELD_DRY_RUN": "1", "NIRI_SOCKET": "", "SWAYSOCK": "/mock/sway.sock", "HYPRLAND_INSTANCE_SIGNATURE": ""}, "swaymsg [con_id=88] focus"),
        (["workspace", "5"], {"SHIELD_DRY_RUN": "1", "NIRI_SOCKET": "", "SWAYSOCK": "", "HYPRLAND_INSTANCE_SIGNATURE": "mock_sig"}, "hyprctl dispatch workspace 5"),
        (["focus", "0xdead"], {"SHIELD_DRY_RUN": "1", "NIRI_SOCKET": "", "SWAYSOCK": "", "HYPRLAND_INSTANCE_SIGNATURE": "mock_sig"}, "hyprctl dispatch focuswindow address:0xdead"),
        (["--dry-run", "volume", "up"], {}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"),
        (["--dry-run", "volume", "down"], {}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),
        (["--dry-run", "volume", "get"], {}, "wpctl get-volume @DEFAULT_AUDIO_SINK@"),
        (["--dry-run", "volume", "set", "50%"], {}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 50%"),
        (["--dry-run", "volume", "set", "75"], {}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 75%"),
        (["volume", "up"], {"SHIELD_DRY_RUN": "1"}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"),
        (["volume", "down"], {"SHIELD_DRY_RUN": "1"}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"),
        (["volume", "get"], {"SHIELD_DRY_RUN": "1"}, "wpctl get-volume @DEFAULT_AUDIO_SINK@"),
        (["volume", "set", "60%"], {"SHIELD_DRY_RUN": "1"}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 60%"),
        (["volume", "set", "80"], {"SHIELD_DRY_RUN": "1"}, "wpctl set-volume @DEFAULT_AUDIO_SINK@ 80%"),
        (["--dry-run", "play-pause"], {}, "playerctl play-pause"),
        (["play-pause"], {"SHIELD_DRY_RUN": "1"}, "playerctl play-pause"),
        (["--dry-run", "media", "play-pause"], {}, "playerctl play-pause"),
        (["media", "play-pause"], {"SHIELD_DRY_RUN": "1"}, "playerctl play-pause"),
    ]

    for args, env_overrides, expected_cmd in cases:
        env = os.environ.copy()
        env.update(env_overrides)
        proc = subprocess.run(
            [str(shield_ctl_path)] + args,
            capture_output=True,
            text=True,
            env=env,
        )
        if proc.returncode != 0:
            fail("shield-ctl-dry-run", f"shield-ctl {' '.join(args)} failed with code {proc.returncode}: {proc.stderr.strip()}")
        out = proc.stdout.strip()
        if out != expected_cmd:
            fail("shield-ctl-dry-run", f"shield-ctl {' '.join(args)} expected '{expected_cmd}', got '{out}'")

    neg_cases = [
        [],
        ["invalid_subcommand"],
        ["workspace"],
        ["workspace", "0"],
        ["workspace", "-1"],
        ["workspace", "abc"],
        ["focus"],
        ["focus", ""],
        ["volume"],
        ["volume", "invalid_action"],
        ["volume", "set"],
        ["--backend", "invalid_backend", "workspace", "1"],
    ]

    for args in neg_cases:
        proc = subprocess.run(
            [str(shield_ctl_path)] + args,
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            fail("shield-ctl-negative", f"Expected non-zero exit for shield-ctl {' '.join(args)}, got 0")

    no_backend_env = os.environ.copy()
    no_backend_env.pop("NIRI_SOCKET", None)
    no_backend_env.pop("SWAYSOCK", None)
    no_backend_env.pop("HYPRLAND_INSTANCE_SIGNATURE", None)
    no_backend_env.pop("SHIELD_BACKEND", None)
    no_backend_env["XDG_RUNTIME_DIR"] = "/tmp/shield-test-empty-runtime"
    proc_no_backend = subprocess.run(
        [str(shield_ctl_path), "workspace", "1"],
        capture_output=True,
        text=True,
        env=no_backend_env,
    )
    if proc_no_backend.returncode == 0:
        fail("shield-ctl-negative", "Expected non-zero exit when no compositor backend is detected, got 0")

    print("VALIDATED [shield-ctl]: dry-run IPC commands across backends and negative cases OK")


def validate_compositor_fixtures(schema):
    comp_fixtures_dir = REPO_DIR / "tests" / "fixtures" / "compositor"
    if not comp_fixtures_dir.is_dir():
        return []
    validated = []
    for fixture_file in sorted(comp_fixtures_dir.glob("*.json")):
        try:
            data = json.loads(fixture_file.read_text(encoding="utf-8"))
        except Exception as exc:
            fail("compositor-fixture", f"Invalid JSON in {fixture_file.name}: {exc}")
        validate_payload_against_def(schema, "compositor", data, f"compositor fixture {fixture_file.name}")
        if fixture_file.stem == "frozen":
            ws_map = {ws["id"]: ws["state"] for ws in data.get("workspaces", [])}
            if ws_map.get(2) != "active" or ws_map.get(8) != "active":
                fail("compositor-fixture-frozen", f"frozen.json workspaces 2 and 8 must be 'active', got: {ws_map}")
            tabs = data.get("tabs", [])
            if len(tabs) != 4 or tabs[0]["title"] != "Hydra" or tabs[1]["title"] != "Nebula":
                fail("compositor-fixture-frozen", f"frozen.json tabs must contain the 4 homelab placeholder slots, got: {tabs}")
        print(f"VALIDATED [compositor-static:{fixture_file.stem}]: {fixture_file.name} -> #/$defs/compositor OK")
        validated.append(f"compositor:{fixture_file.stem}")
    return validated


def validate_network_audio_fixtures(schema):
    net_fixtures_dir = REPO_DIR / "tests" / "fixtures" / "network-audio"
    if not net_fixtures_dir.is_dir():
        return []
    validated = []
    for fixture_file in sorted(net_fixtures_dir.glob("*.json")):
        try:
            data = json.loads(fixture_file.read_text(encoding="utf-8"))
        except Exception as exc:
            fail("network-audio-fixture", f"Invalid JSON in {fixture_file.name}: {exc}")
        validate_payload_against_def(schema, "network_audio", data, f"network_audio fixture {fixture_file.name}")
        if fixture_file.stem in ("frozen", "disconnected"):
            if data.get("connected") is not False:
                fail("network-audio-fixture", f"{fixture_file.name} connected must be False, got {data.get('connected')}")
            if data.get("label") != "DISCONNECTED":
                fail("network-audio-fixture", f"{fixture_file.name} label must be 'DISCONNECTED', got {data.get('label')}")
        if fixture_file.stem == "connected":
            if data.get("connected") is not True:
                fail("network-audio-fixture", f"connected.json connected must be True, got {data.get('connected')}")
        if fixture_file.stem == "audio":
            media = data.get("media", {})
            if media.get("playing") is not True:
                fail("network-audio-fixture", f"audio.json media.playing must be True, got {media.get('playing')}")
            levels = data.get("audio_level", [])
            if len(levels) != 4 or any(not isinstance(x, int) or x < 0 or x > 100 for x in levels):
                fail("network-audio-fixture", f"audio.json audio_level must have 4 integers 0-100, got {levels}")
        print(f"VALIDATED [network-audio-static:{fixture_file.stem}]: {fixture_file.name} -> #/$defs/network_audio OK")
        validated.append(f"network_audio:{fixture_file.stem}")
    return validated


def run_network_audio_checks(script_path, schema):
    env_frozen = os.environ.copy()
    env_frozen["SHIELD_FIXTURE"] = "frozen"
    proc_frozen = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env_frozen,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc_frozen.returncode != 0:
        fail("fixture-env-network-audio", f"SHIELD_FIXTURE=frozen {script_path.name} --once exited {proc_frozen.returncode}")
    lines = proc_frozen.stdout.splitlines()
    if len(lines) != 1:
        fail("fixture-env-network-audio", f"SHIELD_FIXTURE=frozen {script_path.name} --once printed {len(lines)} lines")
    frozen_payload = json.loads(lines[0])
    validate_payload_against_def(schema, "network_audio", frozen_payload, "SHIELD_FIXTURE=frozen network-audio.py --once")
    if frozen_payload.get("connected") is not False or frozen_payload.get("label") != "DISCONNECTED":
        fail("fixture-env-network-audio", f"SHIELD_FIXTURE=frozen unexpected payload: {frozen_payload}")

    override_payload = run_script_fixture(
        script_path,
        "connected",
        "network_audio",
        schema,
        extra_env={"SHIELD_FIXTURE": "disconnected"},
    )
    if override_payload.get("connected") is not True:
        fail("fixture-precedence-network-audio", f"--fixture connected did not override SHIELD_FIXTURE=disconnected: {override_payload}")

    env_live = os.environ.copy()
    env_live.pop("SHIELD_FIXTURE", None)
    proc_live = subprocess.run(
        [sys.executable, str(script_path), "--once"],
        cwd=str(REPO_DIR),
        env=env_live,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc_live.returncode != 0:
        fail("network-audio-live", f"{script_path.name} --once exited {proc_live.returncode}: {proc_live.stderr}")
    live_lines = proc_live.stdout.splitlines()
    if len(live_lines) != 1:
        fail("network-audio-live", f"{script_path.name} --once printed {len(live_lines)} lines")
    live_payload = json.loads(live_lines[0])
    validate_payload_against_def(schema, "network_audio", live_payload, "network-audio.py live --once")


def load_and_verify_layout_schema(schema_path, layout_path):
    if not schema_path.is_file():
        fail("layout-schema-load", f"Layout schema file not found: {schema_path}")
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("layout-schema-load", f"Invalid JSON in {schema_path}: {exc}")

    try:
        Draft202012Validator.check_schema(schema)
    except Exception as exc:
        fail("layout-schema-meta", f"Layout schema failed Draft 2020-12 meta-validation: {exc}")

    if not layout_path.is_file():
        fail("layout-load", f"Layout file not found: {layout_path}")
    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail("layout-load", f"Invalid JSON in {layout_path}: {exc}")

    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(layout), key=lambda e: list(e.path))
    if errors:
        err = errors[0]
        loc = ".".join(str(p) for p in err.path) or "<root>"
        fail("layout-validation", f"layout.json failed schema at '{loc}': {err.message}")

    return layout


def verify_layout_generation(layout_data):
    layout_gen_script = REPO_DIR / "scripts" / "layout-gen.py"
    if not layout_gen_script.is_file():
        fail("layout-gen-missing", f"Generator script not found: {layout_gen_script}")

    proc = subprocess.run(
        [sys.executable, str(layout_gen_script), "--check"],
        cwd=str(REPO_DIR),
        capture_output=True,
        text=True,
        timeout=5,
    )
    if proc.returncode != 0:
        fail("layout-gen-check", f"scripts/layout-gen.py --check failed: {proc.stderr.strip() or proc.stdout.strip()}")


def extract_governed_dimensions(layout):
    governed = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("outer_border", "inner_groove", "bar_width", "bar_height", "top_offset", "gap", "gap_upper", "gap_lower", "chamfer_cut", "bar_gap", "housing_pad_top", "rung_height", "header_height", "volume_cluster", "status_pill", "equalizer_pod", "upper_width", "upper_height", "lower_width", "lower_height", "indicator_height", "glyph_size", "rails", "left_dock"):
                    continue
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, int) and not isinstance(obj, bool):
            governed.add(obj)

    walk(layout)
    return governed


def lint_scss_layout_text(text, label, governed_dims):
    errors = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()
        if not clean_line or clean_line.startswith("$") or clean_line.startswith("@import"):
            continue
        clean_line = re.sub(r"\b(font(-size)?|letter-spacing)\s*:[^;]+;?", "", clean_line)
        for match in re.finditer(r"\bdpi\((\d+)px\)", clean_line):
            val = int(match.group(1))
            if val in governed_dims:
                errors.append(
                    f"{label}:{idx}: Hardcoded governed layout dimension dpi({val}px) found: '{clean_line}'"
                )
        for match in re.finditer(r"(?<![a-zA-Z0-9_$-])(\d+)px\b", clean_line):
            val = int(match.group(1))
            if val in governed_dims:
                errors.append(
                    f"{label}:{idx}: Hardcoded governed layout dimension {val}px found: '{clean_line}'"
                )
    return errors


def lint_yuck_layout_text(text, label, governed_dims):
    errors = []
    lines = text.splitlines()
    for idx, line in enumerate(lines, 1):
        clean_line = line.strip()
        if not clean_line or clean_line.startswith(";"):
            continue
        if "(geometry" in clean_line:
            # defwindow geometry only accepts literals (no defvars), exempt.
            continue
        for match in re.finditer(
            r":(width|height|image-width|image-height|size)\s+[\"']?(\d+)(?:px)?[\"']?",
            clean_line,
        ):
            attr_name = match.group(1)
            val = int(match.group(2))
            if val in governed_dims:
                errors.append(
                    f"{label}:{idx}: Hardcoded governed layout dimension :{attr_name} {val} found: '{clean_line}'"
                )
    return errors


def run_layout_selftest(governed_dims):
    sample_dim = 1888
    neg_scss = f".test {{ min-width: dpi({sample_dim}px); }}"
    neg_scss_errors = lint_scss_layout_text(neg_scss, "<neg-scss>", governed_dims)
    if not neg_scss_errors:
        fail("layout-selftest", f"Negative SCSS test failed to catch dpi({sample_dim}px)")

    neg_yuck = f"(box :width {sample_dim} :height 100)"
    neg_yuck_errors = lint_yuck_layout_text(neg_yuck, "<neg-yuck>", governed_dims)
    if not neg_yuck_errors:
        fail("layout-selftest", f"Negative Yuck test failed to catch :width {sample_dim}")

    pos_scss = ".test { min-width: $canvas-width; }"
    pos_scss_errors = lint_scss_layout_text(pos_scss, "<pos-scss>", governed_dims)
    if pos_scss_errors:
        fail("layout-selftest", f"Positive SCSS test had false positive: {pos_scss_errors}")

    pos_font_scss = f".test {{ font-size: dpi({sample_dim}px); }}"
    pos_font_errors = lint_scss_layout_text(pos_font_scss, "<pos-font-scss>", governed_dims)
    if pos_font_errors:
        fail("layout-selftest", f"Typography SCSS test had false positive: {pos_font_errors}")

    pos_yuck = "(box :width canvas_width :height canvas_height)"
    pos_yuck_errors = lint_yuck_layout_text(pos_yuck, "<pos-yuck>", governed_dims)
    if pos_yuck_errors:
        fail("layout-selftest", f"Positive Yuck test had false positive: {pos_yuck_errors}")


def check_hardcoded_layout_dimensions(governed_dims):
    run_layout_selftest(governed_dims)

    scss_files = [REPO_DIR / "eww.scss"] + [
        Path(p)
        for p in sorted(glob.glob(str(REPO_DIR / "scss" / "*.scss")))
        if Path(p).name not in ("_scale.scss", "_tokens.scss", "_layout.scss")
    ]
    yuck_files = [REPO_DIR / "eww.yuck"] + [
        Path(p)
        for p in sorted(glob.glob(str(REPO_DIR / "yuck" / "*.yuck")))
        if Path(p).name != "_layout.yuck"
    ]

    total_errors = []
    for scss_path in scss_files:
        if scss_path.is_file():
            text = scss_path.read_text(encoding="utf-8")
            rel_label = scss_path.relative_to(REPO_DIR) if scss_path.is_relative_to(REPO_DIR) else scss_path
            errs = lint_scss_layout_text(text, str(rel_label), governed_dims)
            total_errors.extend(errs)

    for yuck_path in yuck_files:
        if yuck_path.is_file():
            text = yuck_path.read_text(encoding="utf-8")
            rel_label = yuck_path.relative_to(REPO_DIR) if yuck_path.is_relative_to(REPO_DIR) else yuck_path
            errs = lint_yuck_layout_text(text, str(rel_label), governed_dims)
            total_errors.extend(errs)

    if total_errors:
        for err in total_errors:
            sys.stderr.write(f"FAIL [layout-hardcoded]: {err}\n")
        fail("layout-hardcoded", f"Found {len(total_errors)} hardcoded layout dimension occurrence(s)")


def main():
    schema = load_and_verify_schema(SCHEMA_PATH)
    layout = load_and_verify_layout_schema(LAYOUT_SCHEMA_PATH, LAYOUT_PATH)
    verify_layout_generation(layout)
    governed_dims = extract_governed_dimensions(layout)
    check_hardcoded_layout_dimensions(governed_dims)

    yuck_files = [REPO_DIR / "eww.yuck"] + [
        Path(p) for p in sorted(glob.glob(str(REPO_DIR / "yuck" / "*.yuck")))
    ]
    checked_refs = check_yuck_references(schema, yuck_files)

    active_validated = []
    comp_validated = validate_compositor_fixtures(schema)
    active_validated.extend(comp_validated)
    net_validated = validate_network_audio_fixtures(schema)
    active_validated.extend(net_validated)
    pending_entries = []

    for entry in SCRIPT_REGISTRY:
        name = entry["name"]
        script_rel = entry["script"]
        script_path = REPO_DIR / script_rel
        def_name = entry["schema_def"]
        status = entry["status"]
        milestone = entry["milestone"]

        if status == "PENDING":
            pending_entries.append(f"{name} ({script_rel}, {milestone})")
            print(f"PENDING [{name}]: {script_rel} -> #/$defs/{def_name} (scheduled for {milestone})")
            continue

        if not script_path.is_file():
            fail("script-missing", f"Active script '{script_rel}' is missing")

        for fixture_name in entry["fixtures"]:
            payload = run_script_fixture(script_path, fixture_name, def_name, schema)
            print(f"VALIDATED [{name}:{fixture_name}]: {script_rel} -> #/$defs/{def_name} OK")
            active_validated.append(f"{name}:{fixture_name}")

        if name == "telemetry":
            run_env_fixture_precedence_check(script_path, schema)
            run_production_proc_fallback_check(script_path, schema)
            run_ladder_gauge_boundary_checks(schema)
        if name == "compositor":
            run_compositor_checks(script_path, schema)
        if name == "network_audio":
            run_network_audio_checks(script_path, schema)

    run_shield_ctl_checks()

    print(
        f"PASS [gate2-schema]: schema strict, layout verified ({len(governed_dims)} governed dims), "
        f"yuck refs valid ({checked_refs} checked), "
        f"active fixtures valid ({', '.join(active_validated)}), "
        f"pending ({', '.join(pending_entries) if pending_entries else 'none'})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
