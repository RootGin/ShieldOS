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
        "status": "PENDING",
        "milestone": "Milestone 4",
        "fixtures": ["niri", "hyprland", "fallback"],
    },
    {
        "name": "network_audio",
        "script": "scripts/network-audio.py",
        "schema_def": "network_audio",
        "status": "PENDING",
        "milestone": "Milestone 6",
        "fixtures": ["connected", "disconnected", "fallback"],
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
                if k in ("outer_border", "inner_groove"):
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

    print(
        f"PASS [gate2-schema]: schema strict, layout verified ({len(governed_dims)} governed dims), "
        f"yuck refs valid ({checked_refs} checked), "
        f"active fixtures valid ({', '.join(active_validated)}), "
        f"pending ({', '.join(pending_entries)})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
