#!/usr/bin/env python3
import argparse
import math
import os
import re
import sys
from pathlib import Path

def parse_theme(theme_path):
    tokens = {}
    with open(theme_path, "r", encoding="utf-8") as f:
        content = f.read()

    for m in re.finditer(r"^\$([a-zA-Z0-9_-]+)\s*:\s*([^;]+);", content, re.MULTILINE):
        name = m.group(1).strip()
        val = m.group(2).strip()
        tokens[f"${name}"] = val
        rgba_m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", val)
        if rgba_m:
            r = int(rgba_m.group(1))
            g = int(rgba_m.group(2))
            b = int(rgba_m.group(3))
            a = rgba_m.group(4)
            hex_color = f"#{r:02X}{g:02X}{b:02X}"
            tokens[f"${name}.color"] = hex_color
            tokens[f"${name}.opacity"] = a
        elif re.match(r"^#[0-9a-fA-F]{3,6}$", val):
            tokens[f"${name}.color"] = val
            tokens[f"${name}.opacity"] = "1"

    return tokens

def generate_star_polygons(count, cx=400.0, cy=400.0, ring_radius=280.0, r_out=8.0):
    r_in = r_out * (3.0 - math.sqrt(5.0)) / 2.0
    base_points = []
    for k in range(10):
        angle = math.radians(-90.0 + k * 36.0)
        r = r_out if k % 2 == 0 else r_in
        base_points.append(f"{r * math.cos(angle):.3f},{r * math.sin(angle):.3f}")
    points_str = " ".join(base_points)

    polygons = []
    for i in range(count):
        theta_deg = -90.0 + i * (360.0 / count)
        theta_rad = math.radians(theta_deg)
        x = cx + ring_radius * math.cos(theta_rad)
        y = cy + ring_radius * math.sin(theta_rad)
        rot_deg = theta_deg + 90.0
        polygons.append(
            f'    <polygon class="star" points="{points_str}" transform="translate({x:.3f}, {y:.3f}) rotate({rot_deg:.3f})" />'
        )
    return "\n".join(polygons)

def replace_tokens(template_content, tokens):
    res = template_content
    for k, v in tokens.items():
        res = res.replace("{{" + k + "}}", v)
    return res

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--theme", default="shield-gold")
    parser.add_argument("--stars", type=int, default=None)
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent
    theme_file = repo_dir / "themes" / f"{args.theme}.scss"
    if not theme_file.is_file():
        sys.stderr.write(f"Error: theme file not found: {theme_file}\n")
        sys.exit(1)

    tokens = parse_theme(theme_file)
    star_count = args.stars if args.stars is not None else int(os.environ.get("SHIELD_STARS_COUNT", "56"))

    templates_dir = repo_dir / "assets" / "templates"
    assets_dir = repo_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    star_template_path = templates_dir / "star-ring.svg"
    if star_template_path.is_file():
        with open(star_template_path, "r", encoding="utf-8") as f:
            tmpl = f.read()
        polygons = generate_star_polygons(star_count)
        rendered = tmpl.replace("{{STAR_POLYGONS}}", polygons)
        rendered = replace_tokens(rendered, tokens)
        with open(assets_dir / "star-ring.svg", "w", encoding="utf-8") as f:
            f.write(rendered)

    glow_template_path = templates_dir / "glow.svg"
    if glow_template_path.is_file():
        with open(glow_template_path, "r", encoding="utf-8") as f:
            tmpl = f.read()
        rendered = replace_tokens(tmpl, tokens)
        with open(assets_dir / "glow.svg", "w", encoding="utf-8") as f:
            f.write(rendered)

    placeholder_template_path = templates_dir / "placeholder.svg"
    if placeholder_template_path.is_file():
        with open(placeholder_template_path, "r", encoding="utf-8") as f:
            tmpl = f.read()
        rendered = replace_tokens(tmpl, tokens)
        with open(assets_dir / "placeholder.svg", "w", encoding="utf-8") as f:
            f.write(rendered)

    emblem_src = assets_dir / "emblem-src.svg"
    if not emblem_src.is_file():
        print("SKIP: assets/emblem-src.svg (not present, supplied in Ticket 02)")

if __name__ == "__main__":
    main()
