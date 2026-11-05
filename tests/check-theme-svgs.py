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
    panels_dir = assets_dir / "panels"
    if panels_dir.is_dir():
        svg_files.extend(list(panels_dir.glob("*.svg")))
    if not svg_files:
        fail("provenance", "No generated SVGs found in assets/")

    for svg_file in svg_files:
        content = svg_file.read_text(encoding="utf-8")
        eight_digit = re.findall(r"#[0-9a-fA-F]{8}\b", content)
        if eight_digit:
            fail("glow-hex", f"Forbidden 8-digit hex found in {svg_file.name}: {eight_digit}")

        for m in re.finditer(r'(?:fill|stroke|stop-color|flood-color|lighting-color|color)\s*=\s*"([^"]+)"', content):
            val = m.group(1).strip()
            if not val or val == "none" or val.startswith("url("):
                continue
            if re.match(r"^#[0-9a-fA-F]{3,6}$", val):
                if val.lower() not in theme_colors:
                    fail("provenance", f"Color '{val}' in {svg_file.name} does not trace to any theme token in themes/shield-gold.scss")
            else:
                fail("provenance", f"Color '{val}' in {svg_file.name} does not trace to any theme token in themes/shield-gold.scss")

        for m in re.finditer(r'(?:fill|stroke|stop-color)\s*:\s*([^;"]+)', content):
            val = m.group(1).strip()
            if not val or val == "none" or val.startswith("url("):
                continue
            if re.match(r"^#[0-9a-fA-F]{3,6}$", val):
                if val.lower() not in theme_colors:
                    fail("provenance", f"Color '{val}' in {svg_file.name} does not trace to any theme token in themes/shield-gold.scss")
            else:
                fail("provenance", f"Color '{val}' in {svg_file.name} does not trace to any theme token in themes/shield-gold.scss")

        found_hexes = re.findall(r"#[0-9a-fA-F]{3,6}\b", content)
        for h in found_hexes:
            if h.lower() not in theme_colors:
                fail("provenance", f"Color '{h}' in {svg_file.name} does not trace to any theme token in themes/shield-gold.scss")

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
    expected_r = 280.0
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

    expected_orientation_offset = 90.0
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

def check_emblem(repo_dir):
    emblem_file = repo_dir / "assets" / "emblem.svg"
    if not emblem_file.is_file():
        fail("emblem-missing", "assets/emblem.svg does not exist")

    content = emblem_file.read_text(encoding="utf-8")
    if "#DBAD4D" not in content.upper():
        fail("emblem-primary", "assets/emblem.svg missing $accent-primary (#DBAD4D)")
    if "#C79C4E" not in content.upper():
        fail("emblem-primary-mid", "assets/emblem.svg missing $accent-primary-mid (#C79C4E)")

    try:
        ET.parse(emblem_file)
    except Exception as exc:
        fail("emblem-xml", f"Failed to parse assets/emblem.svg: {exc}")

def check_corner_plates(repo_dir):
    panels_dir = repo_dir / "assets" / "panels"
    tl_file = panels_dir / "corner-top-left.svg"
    tr_file = panels_dir / "corner-top-right.svg"
    bl_file = panels_dir / "corner-bottom-left.svg"
    br_file = panels_dir / "corner-bottom-right.svg"
    for path, missing_key in [
        (tl_file, "corner-top-left-missing"),
        (tr_file, "corner-top-right-missing"),
        (bl_file, "corner-bottom-left-missing"),
        (br_file, "corner-bottom-right-missing"),
    ]:
        if not path.is_file():
            fail(missing_key, f"assets/panels/{path.name} does not exist")

    for file_path, name, expected_w, expected_h, expected_vb, expected_chamfer in [
        (tl_file, "top-left", "520", "116", "0 0 520 116", "501,50 L 520,31"),
        (tr_file, "top-right", "260", "90", "0 0 260 90", "0,31 L 11,42"),
        (bl_file, "bottom-left", "520", "160", "0 0 520 160", "235,138 L 256,159"),
        (br_file, "bottom-right", "1156", "160", "0 0 1156 160", "1074,86 L 1097,63"),
    ]:
        try:
            tree = ET.parse(file_path)
        except Exception as exc:
            fail(f"{name}-xml", f"Failed to parse {file_path.name}: {exc}")
        root = tree.getroot()
        w = root.attrib.get("width")
        h = root.attrib.get("height")
        vb = root.attrib.get("viewBox")
        if w != expected_w or h != expected_h or vb != expected_vb:
            fail(f"{name}-dimensions", f"Expected {expected_w}x{expected_h} viewBox '{expected_vb}', got w={w} h={h} vb={vb}")
        paths = root.findall(".//{http://www.w3.org/2000/svg}path")
        if not paths:
            paths = root.findall(".//path")
        if len(paths) < 2:
            fail(f"{name}-paths", f"Expected at least 2 paths in {file_path.name}, got {len(paths)}")
        outer_path = paths[0]
        groove_path = paths[1]
        if outer_path.attrib.get("stroke-width") != "2":
            fail(f"{name}-outer-stroke", f"Outer path stroke-width must be 2, got {outer_path.attrib.get('stroke-width')}")
        if groove_path.attrib.get("stroke-width") != "1":
            fail(f"{name}-groove-stroke", f"Groove path stroke-width must be 1, got {groove_path.attrib.get('stroke-width')}")
        outer_d = outer_path.attrib.get("d", "")
        if expected_chamfer not in outer_d:
            fail(f"{name}-chamfer", f"Expected chamfer segment '{expected_chamfer}' in {file_path.name} path d='{outer_d}'")

def check_star_emblem(repo_dir):
    star_file = repo_dir / "assets" / "panels" / "star-emblem.svg"
    if not star_file.is_file():
        fail("star-emblem-missing", "assets/panels/star-emblem.svg does not exist")
    try:
        tree = ET.parse(star_file)
    except Exception as exc:
        fail("star-emblem-xml", f"Failed to parse star-emblem.svg: {exc}")
    root = tree.getroot()
    w = root.attrib.get("width")
    h = root.attrib.get("height")
    if w != "24" or h != "24":
        fail("star-emblem-dimensions", f"Expected 24x24 for star-emblem, got w={w} h={h}")
    paths = root.findall(".//{http://www.w3.org/2000/svg}path") or root.findall(".//path")
    if not paths:
        fail("star-emblem-paths", "Missing path in star-emblem.svg")
    star_path = paths[0]
    star_d = star_path.attrib.get("d", "")
    if "12,2" not in star_d or "22,12" not in star_d or "12,22" not in star_d or "2,12" not in star_d:
        fail("star-emblem-geometry", f"Star emblem missing 4-pointed cardinal vertices in path: {star_d}")
    fill = star_path.attrib.get("fill", "").upper()
    if fill != "#DBAD4D":
        fail("star-emblem-color", f"Expected star-emblem fill #DBAD4D ($accent-primary), got {fill}")

def check_operator_assets(repo_dir):
    panels_dir = repo_dir / "assets" / "panels"
    medallion_file = panels_dir / "operator-medallion.svg"
    ring_file = panels_dir / "icon-radar-ring.svg"
    target_file = panels_dir / "icon-radar-target.svg"
    for p, key in [
        (medallion_file, "operator-medallion-missing"),
        (ring_file, "icon-radar-ring-missing"),
        (target_file, "icon-radar-target-missing"),
    ]:
        if not p.is_file():
            fail(key, f"assets/panels/{p.name} does not exist")

    med_tree = ET.parse(medallion_file)
    med_root = med_tree.getroot()
    if med_root.attrib.get("width") != "92" or med_root.attrib.get("height") != "92":
        fail("operator-medallion-dims", f"Expected 92x92 for operator medallion, got {med_root.attrib.get('width')}x{med_root.attrib.get('height')}")
    med_content = medallion_file.read_text(encoding="utf-8")
    if "#DBAD4D" not in med_content.upper() or "#C79C4E" not in med_content.upper():
        fail("operator-medallion-colors", "operator-medallion.svg missing tokenized eagle colors ($accent-primary, $accent-primary-mid)")

def main():
    repo_dir = Path(__file__).resolve().parent.parent
    theme_colors = extract_theme_colors(repo_dir / "themes" / "shield-gold.scss")

    check_provenance(repo_dir, theme_colors)
    check_star_ring(repo_dir)
    check_glow(repo_dir)
    check_emblem(repo_dir)
    check_corner_plates(repo_dir)
    check_star_emblem(repo_dir)
    check_operator_assets(repo_dir)

    print("PASS [theme-svgs]: provenance, 56-star ring, radial glow, emblem, corner plates, and 4-pointed star validated successfully.")

if __name__ == "__main__":
    main()
