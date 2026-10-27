#!/usr/bin/env python3
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


def main():
    schema = load_and_verify_schema(SCHEMA_PATH)

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

    print(
        f"PASS [seam2-schema]: schema strict, yuck refs valid ({checked_refs} checked), "
        f"active fixtures valid ({', '.join(active_validated)}), "
        f"pending ({', '.join(pending_entries)})."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
