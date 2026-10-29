#!/usr/bin/env python3
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
LAYOUT_FILE = REPO_DIR / "layout.json"
ASSETS_DIR = REPO_DIR / "assets" / "panels"
TEMPLATES_DIR = REPO_DIR / "assets" / "templates" / "panels"

def fail(check_name, message):
    sys.stderr.write(f"FAIL [{check_name}]: {message}\n")
    sys.exit(1)

def check_static_docking():
    tl_svg = ASSETS_DIR / "corner-top-left.svg"
    tr_svg = ASSETS_DIR / "corner-top-right.svg"
    if not tl_svg.is_file() or not tr_svg.is_file():
        fail("docking-assets", "Generated corner panel assets not found")

    tl_tree = ET.parse(tl_svg)
    tl_paths = tl_tree.getroot().findall(".//{http://www.w3.org/2000/svg}path") or tl_tree.getroot().findall(".//path")
    if len(tl_paths) < 2:
        fail("docking-paths-tl", f"Expected at least 2 paths in {tl_svg.name}")
    tl_outer_d = tl_paths[0].attrib.get("d", "")
    tl_groove_d = tl_paths[1].attrib.get("d", "")

    if "L 259,32" in tl_outer_d or "L 260,32" in tl_outer_d or "L 259,1" in tl_outer_d:
        fail("docking-closed-seam-tl", f"Top-left corner plate contains vertical seam stroke along docking edge: {tl_outer_d}")
    if "260,31" not in tl_outer_d:
        fail("docking-outer-endpoint-tl", f"Top-left outer path does not dock at (260, 31): {tl_outer_d}")
    if "260,27.5" not in tl_groove_d:
        fail("docking-groove-endpoint-tl", f"Top-left groove path does not dock at (260, 27.5): {tl_groove_d}")

    tr_tree = ET.parse(tr_svg)
    tr_paths = tr_tree.getroot().findall(".//{http://www.w3.org/2000/svg}path") or tr_tree.getroot().findall(".//path")
    if len(tr_paths) < 2:
        fail("docking-paths-tr", f"Expected at least 2 paths in {tr_svg.name}")
    tr_outer_d = tr_paths[0].attrib.get("d", "")
    tr_groove_d = tr_paths[1].attrib.get("d", "")

    if "L 1,32" in tr_outer_d or "L 0,32" in tr_outer_d or "L 1,1" in tr_outer_d:
        fail("docking-closed-seam-tr", f"Top-right corner plate contains vertical seam stroke along docking edge: {tr_outer_d}")
    if "0,31" not in tr_outer_d:
        fail("docking-outer-endpoint-tr", f"Top-right outer path does not dock at (0, 31): {tr_outer_d}")
    if "0,27.5" not in tr_groove_d:
        fail("docking-groove-endpoint-tr", f"Top-right groove path does not dock at (0, 27.5): {tr_groove_d}")

def parse_pixels(txt_output):
    pixel_map = {}
    for line in txt_output.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split(":")
        if len(parts) >= 2:
            coord = parts[0].strip()
            x_str, y_str = coord.split(",")
            hex_match = None
            for token in parts[1].split():
                if token.startswith("#") and len(token) == 7:
                    hex_match = token.upper()
                    break
            if hex_match:
                pixel_map[(int(x_str), int(y_str))] = hex_match
    return pixel_map

def sample_region(capture_file, geom):
    cmd = ["magick", f"{capture_file}[{geom}]", "txt:"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        fail("sample-region", f"magick failed to sample region {geom}: {proc.stderr.strip()}")
    return parse_pixels(proc.stdout)

def hex_close(h1, h2, tolerance=15):
    r1, g1, b1 = int(h1[1:3], 16), int(h1[3:5], 16), int(h1[5:7], 16)
    r2, g2, b2 = int(h2[1:3], 16), int(h2[3:5], 16), int(h2[5:7], 16)
    return abs(r1 - r2) <= tolerance and abs(g1 - g2) <= tolerance and abs(b1 - b2) <= tolerance

def check_raster_docking(capture_file):
    if not capture_file.is_file():
        return

    border_outer = "#5A5C60"
    border_groove = "#18191B"
    surface_panel = "#2C2D2F"
    canvas_void = "#0E0F11"

    mid_pixels = sample_region(capture_file, "1x40+960+0")
    if 31 in [y for x, y in mid_pixels]:
        b_bottom = mid_pixels.get((0, 31))
        if not b_bottom or not hex_close(b_bottom, border_outer):
            fail("rail-height-bottom", f"Expected bottom outer border (#5A5C60) at x=960, y=31, got {b_bottom}")

    if 32 in [y for x, y in mid_pixels]:
        under_rail = mid_pixels.get((0, 32))
        if under_rail and hex_close(under_rail, border_outer, tolerance=5):
            fail("rail-height-overhang", f"Top rail rendered height exceeds 32px: detected outer border at y=32 ({under_rail})")

    tl_seam = sample_region(capture_file, "6x1+257+15")
    for (x, y), col in tl_seam.items():
        if hex_close(col, border_outer, tolerance=10):
            fail("seam-divider-tl", f"Vertical outer border divider detected at top-left joint: ({x+257}, {y+15}) = {col}")

    tl_bottom = sample_region(capture_file, "4x1+258+31")
    for (x, y), col in tl_bottom.items():
        if hex_close(col, canvas_void, tolerance=5):
            fail("seam-notch-tl", f"Missing pixel / void notch detected at top-left joint bottom border: ({x+258}, {y+31}) = {col}")

    tr_seam = sample_region(capture_file, "6x1+1657+15")
    for (x, y), col in tr_seam.items():
        if hex_close(col, border_outer, tolerance=10):
            fail("seam-divider-tr", f"Vertical outer border divider detected at top-right joint: ({x+1657}, {y+15}) = {col}")

    tr_bottom = sample_region(capture_file, "4x1+1658+31")
    for (x, y), col in tr_bottom.items():
        if hex_close(col, canvas_void, tolerance=5):
            fail("seam-notch-tr", f"Missing pixel / void notch detected at top-right joint bottom border: ({x+1658}, {y+31}) = {col}")

def main():
    check_static_docking()

    captures = [
        REPO_DIR / "tests" / "captures" / "ticket-09.png",
        REPO_DIR / "tests" / "captures" / "milestone-2.png",
    ]
    for cap in captures:
        if cap.is_file():
            check_raster_docking(cap)

    print("PASS [docking-seams]: Corner plate docking paths, rail height (32px), and junction continuity verified.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
