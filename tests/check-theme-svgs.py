#!/usr/bin/env python3
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

def fail(check, msg):
    sys.stderr.write(f"FAIL [{check}]: {msg}\n")
    sys.exit(1)

def extract_theme_colors(theme_path):
    with open(theme_path, "r", encoding="utf-8") as f:
        content = f.read()

    colors = set()
    for m in re.finditer(r"#[0-9a-fA-F]{3,8}", content):
        colors.add(m.group(0).lower())

    for m in re.finditer(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", content):
        r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        colors.add(f"#{r:02x}{g:02x}{b:02x}")

    return colors

def check_provenance(repo_dir, theme_colors):
    assets_dir = repo_dir / "assets"
    svg_files = list(assets_dir.glob("*.svg"))
    if not svg_files:
        fail("provenance", "No generated SVGs found in assets/")

    for svg_file in svg_files:
        content = svg_file.read_text(encoding="utf-8")
        eight_digit = re.findall(r"#[0-9a-fA-F]{8}\b", content)
        if eight_digit:
            fail("glow-hex", f"Forbidden 8-digit hex found in {svg_file.name}: {eight_digit}")

        found_hexes = re.findall(r"#[0-9a-fA-F]{3,6}\b", content)
        for h in found_hexes:
            if h.lower() not in theme_colors:
                fail("provenance", f"Color {h} in {svg_file.name} does not trace to any theme token in themes/shield-gold.scss")

def check_star_ring(repo_dir):
    ring_file = repo_dir / "assets" / "star-ring.svg"
    if not ring_file.is_file():
        fail("star-ring-missing", "assets/star-ring.svg does not exist")

    try:
        tree = ET.parse(ring_file)
    except Exception as exc:
        fail("star-ring-xml", f"Failed to parse assets/star-ring.svg: {exc}")

    root = tree.getroot()
    polygons = root.findall(".//{http://www.w3.org/2000/svg}polygon")
    if not polygons:
        polygons = root.findall(".//polygon")

    if len(polygons) != 56:
        fail("star-ring-count", f"Expected exactly 56 stars, found {len(polygons)}")

    stars_data = []
    for idx, poly in enumerate(polygons):
        pts_str = poly.attrib.get("points", "")
        pts = [p.strip() for p in pts_str.split() if p.strip()]
        if len(pts) != 10:
            fail("star-ring-geometry", f"Star {idx} does not have 10 vertices (found {len(pts)})")

        trans_str = poly.attrib.get("transform", "")
        m_trans = re.search(r"translate\(\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)", trans_str)
        m_rot = re.search(r"rotate\(\s*([-\d.]+)\s*\)", trans_str)
        if not m_trans or not m_rot:
            fail("star-ring-transform", f"Star {idx} missing valid translate or rotate in transform: '{trans_str}'")

        x = float(m_trans.group(1))
        y = float(m_trans.group(2))
        rot = float(m_rot.group(1))
        stars_data.append((x, y, rot))

    avg_x = sum(s[0] for s in stars_data) / len(stars_data)
    avg_y = sum(s[1] for s in stars_data) / len(stars_data)
    if abs(avg_x - 400.0) > 0.1 or abs(avg_y - 400.0) > 0.1:
        fail("star-ring-center", f"Ring center mismatch: expected (400, 400), got ({avg_x:.3f}, {avg_y:.3f})")

    radii = [math.hypot(s[0] - 400.0, s[1] - 400.0) for s in stars_data]
    expected_r = radii[0]
    for idx, r in enumerate(radii):
        if abs(r - expected_r) > 0.1:
            fail("star-ring-radius", f"Star {idx} radius {r:.3f} deviates from expected {expected_r:.3f}")

    angles = []
    for x, y, rot in stars_data:
        deg = math.degrees(math.atan2(y - 400.0, x - 400.0)) % 360.0
        angles.append((deg, rot))

    angles.sort(key=lambda item: item[0])
    expected_step = 360.0 / 56.0
    for i in range(len(angles)):
        a1 = angles[i][0]
        a2 = angles[(i + 1) % len(angles)][0]
        diff = (a2 - a1) % 360.0
        if abs(diff - expected_step) > 0.05:
            fail("star-ring-spacing", f"Star spacing deviation between {i} and {i+1}: got {diff:.3f}°, expected {expected_step:.3f}°")

    expected_orientation_offset = (stars_data[0][2] - math.degrees(math.atan2(stars_data[0][1] - 400.0, stars_data[0][0] - 400.0))) % 360.0
    for idx, (x, y, rot) in enumerate(stars_data):
        theta = math.degrees(math.atan2(y - 400.0, x - 400.0))
        offset = (rot - theta) % 360.0
        if abs(offset - expected_orientation_offset) > 0.05:
            fail("star-ring-orientation", f"Star {idx} orientation deviates: offset {offset:.3f}° vs expected {expected_orientation_offset:.3f}°")

def check_glow(repo_dir):
    glow_file = repo_dir / "assets" / "glow.svg"
    if not glow_file.is_file():
        fail("glow-missing", "assets/glow.svg does not exist")

    content = glow_file.read_text(encoding="utf-8")
    if "<filter" in content or "feGaussianBlur" in content or "filter=" in content:
        fail("glow-filter", "assets/glow.svg must use radial gradient only, filter/blur detected")

    try:
        tree = ET.parse(glow_file)
    except Exception as exc:
        fail("glow-xml", f"Failed to parse assets/glow.svg: {exc}")

    root = tree.getroot()
    rad_grads = root.findall(".//{http://www.w3.org/2000/svg}radialGradient")
    if not rad_grads:
        rad_grads = root.findall(".//radialGradient")

    if not rad_grads:
        fail("glow-radial", "assets/glow.svg must define a radialGradient")

    stops = rad_grads[0].findall(".//{http://www.w3.org/2000/svg}stop")
    if not stops:
        stops = rad_grads[0].findall(".//stop")

    if len(stops) < 2:
        fail("glow-stops", "radialGradient requires at least two color stops")

    op1 = float(stops[0].attrib.get("stop-opacity", "1"))
    if abs(op1 - 0.35) > 0.01:
        fail("glow-opacity", f"Expected stop-opacity 0.35 from token, got {op1}")

    op_last = float(stops[-1].attrib.get("stop-opacity", "1"))
    if abs(op_last - 0.0) > 0.01:
        fail("glow-opacity-end", f"Expected outer stop-opacity 0, got {op_last}")

def main():
    repo_dir = Path(__file__).resolve().parent.parent
    theme_colors = extract_theme_colors(repo_dir / "themes" / "shield-gold.scss")

    check_provenance(repo_dir, theme_colors)
    check_star_ring(repo_dir)
    check_glow(repo_dir)

    print("PASS [theme-svgs]: provenance, 56-star ring, and radial glow validated successfully.")

if __name__ == "__main__":
    main()
