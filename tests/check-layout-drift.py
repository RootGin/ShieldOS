#!/usr/bin/env python3
import importlib.util
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
LAYOUT_GEN_PATH = REPO_DIR / "scripts" / "layout-gen.py"
LAYOUT_PATH = REPO_DIR / "layout.json"
SCHEMA_PATH = REPO_DIR / "schemas" / "layout.schema.json"
SCSS_LAYOUT_PATH = REPO_DIR / "scss" / "_layout.scss"
YUCK_LAYOUT_PATH = REPO_DIR / "yuck" / "_layout.yuck"

def fail(msg):
    sys.stderr.write(f"FAIL [layout-drift]: {msg}\n")
    sys.exit(1)

def load_layout_gen():
    spec = importlib.util.spec_from_file_location("layout_gen", LAYOUT_GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def parse_scss_vars(text):
    out = {}
    for m in re.finditer(r"^\$([a-z0-9-]+):\s*dpi\((-?\d+)px\);", text, re.MULTILINE):
        out[m.group(1)] = int(m.group(2))
    return out

def parse_yuck_vars(text):
    out = {}
    for m in re.finditer(r"^\(defvar\s+([a-z0-9_]+)\s+(-?\d+)\)", text, re.MULTILINE):
        out[m.group(1)] = int(m.group(2))
    return out

def main():
    mod = load_layout_gen()
    raw = mod.load_layout(LAYOUT_PATH, SCHEMA_PATH)
    resolved = mod.resolve_layout(raw)
    scale = float(raw.get("scale", 1.0))

    ez = resolved["exclusive_zone"]
    bars = resolved["bars"]
    wp = resolved["workspace_pills"]
    sp_r = resolved["side_panels"]["right"]
    gg = resolved["gauges"]

    cpu_h = gg["header_height"] + 5 * gg["rung_height"]
    ram_h = gg["header_height"] + 6 * gg["rung_height"]
    cpu_start = sp_r["upper_height"] + gg["gap_upper"]
    ram_start = cpu_start + cpu_h + gg["gap"]
    right_total = ram_start + ram_h + gg["gap_lower"] + sp_r["lower_height"]
    pill_array_w = 10 * wp["width"] + 9 * wp["gap"]
    bottom_overhang = bars["bottom"]["height"] - ez["bottom"]
    right_overhang = sp_r["width"] - ez["right"]
    workable_w = resolved["screen"]["width"] - ez["left"] - ez["right"]
    workable_h = resolved["screen"]["height"] - ez["top"] - ez["bottom"]

    if abs(scale - 0.672) < 1e-6:
        checks = [
            ("exclusive_zone.top", ez["top"], 73),
            ("exclusive_zone.bottom", ez["bottom"], 56),
            ("exclusive_zone.left", ez["left"], 55),
            ("exclusive_zone.right", ez["right"], 55),
            ("workable_width", workable_w, 1810),
            ("workable_height", workable_h, 951),
            ("bars.top.height", bars["top"]["height"], 78),
            ("bars.bottom.height", bars["bottom"]["height"], 108),
            ("workspace_pills.width", wp["width"], 26),
            ("workspace_pills.height", wp["height"], 27),
            ("workspace_pills.gap", wp["gap"], 5),
            ("pill_array_width", pill_array_w, 305),
            ("side_panels.right.width", sp_r["width"], 121),
            ("side_panels.right.upper_height", sp_r["upper_height"], 110),
            ("side_panels.right.lower_height", sp_r["lower_height"], 213),
            ("gauges.width", gg["width"], 34),
            ("gauges.header_height", gg["header_height"], 16),
            ("gauges.rung_height", gg["rung_height"], 20),
            ("gauges.gap_upper", gg["gap_upper"], 13),
            ("gauges.gap", gg["gap"], 17),
            ("gauges.gap_lower", gg["gap_lower"], 11),
            ("cpu_ladder_height", cpu_h, 116),
            ("ram_ladder_height", ram_h, 136),
            ("cpu_start_y", cpu_start, 123),
            ("ram_start_y", ram_start, 256),
            ("right_budget_total", right_total, 616),
            ("side_panels.right.height", sp_r["height"], 616),
            ("bottom_overhang", bottom_overhang, 52),
            ("right_overhang", right_overhang, 66),
        ]
        for name, actual, expected in checks:
            if actual != expected:
                fail(f"{name}: expected {expected}, got {actual}")

    if not SCSS_LAYOUT_PATH.is_file() or not YUCK_LAYOUT_PATH.is_file():
        fail("Generated _layout.scss or _layout.yuck missing")

    scss_vars = parse_scss_vars(SCSS_LAYOUT_PATH.read_text(encoding="utf-8"))
    yuck_vars = parse_yuck_vars(YUCK_LAYOUT_PATH.read_text(encoding="utf-8"))

    sync_checks = [
        ("exclusive-zone-top", "exclusive_zone_top", ez["top"]),
        ("exclusive-zone-bottom", "exclusive_zone_bottom", ez["bottom"]),
        ("exclusive-zone-left", "exclusive_zone_left", ez["left"]),
        ("exclusive-zone-right", "exclusive_zone_right", ez["right"]),
        ("bar-top-height", "bar_top_height", bars["top"]["height"]),
        ("bar-bottom-height", "bar_bottom_height", bars["bottom"]["height"]),
        ("workspace-pill-width", "workspace_pill_width", wp["width"]),
        ("side-right-width", "side_right_width", sp_r["width"]),
        ("side-right-height", "side_right_height", sp_r["height"]),
        ("gauge-width", "gauge_width", gg["width"]),
        ("gauge-header-height", "gauge_header_height", gg["header_height"]),
        ("gauge-rung-height", "gauge_rung_height", gg["rung_height"]),
        ("gauge-gap-upper", "gauge_gap_upper", gg["gap_upper"]),
        ("gauge-gap", "gauge_gap", gg["gap"]),
        ("gauge-gap-lower", "gauge_gap_lower", gg["gap_lower"]),
    ]
    for scss_k, yuck_k, expected in sync_checks:
        if scss_vars.get(scss_k) != expected:
            fail(f"_layout.scss ${scss_k}: expected {expected}, got {scss_vars.get(scss_k)}")
        if yuck_vars.get(yuck_k) != expected:
            fail(f"_layout.yuck {yuck_k}: expected {expected}, got {yuck_vars.get(yuck_k)}")

    print(
        f"PASS [layout-drift]: scale={scale}, workable={workable_w}x{workable_h}, "
        f"right_panel={sp_r['width']}x{sp_r['height']}, pill_array={pill_array_w}px, "
        f"overhangs=({bottom_overhang}px bottom, {right_overhang}px right)"
    )

if __name__ == "__main__":
    main()
