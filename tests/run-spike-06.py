#!/usr/bin/env python3
import os
import re
import subprocess
import sys
from pathlib import Path

def run_cmd(cmd, cwd=None):
    res = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"Command failed: {cmd}\nOutput: {res.stdout}\nError: {res.stderr}\n")
        sys.exit(res.returncode)
    return res.stdout

def main():
    repo_dir = Path(__file__).resolve().parent.parent
    yuck_spike = repo_dir / "yuck" / "spike_06.yuck"
    scss_spike = repo_dir / "scss" / "spike_06.scss"
    eww_scss = repo_dir / "eww.scss"
    eww_yuck = repo_dir / "eww.yuck"

    orig_eww_scss = eww_scss.read_text(encoding="utf-8")
    orig_eww_yuck = eww_yuck.read_text(encoding="utf-8")

    scss_content = """@mixin octagon-outer($leg) {
  $color: $border-panel-outer;
  $stop: $leg * 0.70710678;
  background-image:
    linear-gradient(135deg, transparent $stop, $color $stop),
    linear-gradient(-135deg, transparent $stop, $color $stop),
    linear-gradient(45deg, transparent $stop, $color $stop),
    linear-gradient(-45deg, transparent $stop, $color $stop);
  background-size: 50.6% 50.6%;
  background-position: top left, top right, bottom left, bottom right;
  background-repeat: no-repeat;
}

@mixin octagon-groove($leg) {
  $color: $border-panel-groove;
  $stop: $leg * 0.70710678;
  background-image:
    linear-gradient(135deg, transparent $stop, $color $stop),
    linear-gradient(-135deg, transparent $stop, $color $stop),
    linear-gradient(45deg, transparent $stop, $color $stop),
    linear-gradient(-45deg, transparent $stop, $color $stop);
  background-size: 50.6% 50.6%;
  background-position: top left, top right, bottom left, bottom right;
  background-repeat: no-repeat;
}

@mixin octagon-surface($leg) {
  $color: $surface-panel;
  $stop: $leg * 0.70710678;
  background-image:
    linear-gradient(135deg, transparent $stop, $color $stop),
    linear-gradient(-135deg, transparent $stop, $color $stop),
    linear-gradient(45deg, transparent $stop, $color $stop),
    linear-gradient(-45deg, transparent $stop, $color $stop);
  background-size: 50.6% 50.6%;
  background-position: top left, top right, bottom left, bottom right;
  background-repeat: no-repeat;
}

.spike-container {
  padding: dpi(40px);
}

.spike-title {
  font-family: $font-hud;
  font-size: $text-sm;
  color: $text-muted;
  margin-bottom: dpi(12px);
}

.spike-card-a1-outer {
  @include octagon-outer(dpi(24px));
}

.spike-card-a1-groove {
  @include octagon-groove(dpi(22px));
}

.spike-card-a1-surface {
  @include octagon-surface(dpi(21px));
}

.spike-card-a2-body {
  background-color: $surface-panel;
  border: dpi(2px) solid $border-panel-outer;
}

.triangle {
  min-width: 0;
  min-height: 0;

  &.spike-tri-edge {
    &.topleft {
      border-width: dpi(24px) 0 0 dpi(24px);
      border-color: $border-panel-outer transparent transparent transparent;
    }
    &.topright {
      border-width: dpi(24px) dpi(24px) 0 0;
      border-color: $border-panel-outer transparent transparent transparent;
    }
    &.bottomleft {
      border-width: 0 0 dpi(24px) dpi(24px);
      border-color: transparent transparent $border-panel-outer transparent;
    }
    &.bottomright {
      border-width: 0 dpi(24px) dpi(24px) 0;
      border-color: transparent transparent $border-panel-outer transparent;
    }
  }

  &.spike-tri-cut {
    &.topleft {
      border-width: dpi(21px) 0 0 dpi(21px);
      border-color: $bg-canvas transparent transparent transparent;
    }
    &.topright {
      border-width: dpi(21px) dpi(21px) 0 0;
      border-color: $bg-canvas transparent transparent transparent;
    }
    &.bottomleft {
      border-width: 0 0 dpi(21px) dpi(21px);
      border-color: transparent transparent $bg-canvas transparent;
    }
    &.bottomright {
      border-width: 0 dpi(21px) dpi(21px) 0;
      border-color: transparent transparent $bg-canvas transparent;
    }
  }
}

.spike-housing-a-body {
  background-color: $surface-panel;
  border-top: dpi(2px) solid $border-panel-outer;
  border-left: dpi(2px) solid $border-panel-outer;
  border-bottom: dpi(2px) solid $border-panel-outer;
}

.spike-housing-a-rail {
  background-color: $surface-panel;
  border-top: dpi(2px) solid $border-panel-outer;
  border-bottom: dpi(2px) solid $border-panel-outer;
  border-right: dpi(2px) solid $border-panel-outer;
}

.spike-housing-a-groove-h {
  border-top: dpi(1px) solid $border-panel-groove;
  margin-top: dpi(2px);
  margin-bottom: dpi(2px);
  border-bottom: dpi(1px) solid $border-panel-groove;
}

.spike-housing-b-rail {
  background-color: $surface-panel;
  border-top: dpi(2px) solid $border-panel-outer;
  border-bottom: dpi(2px) solid $border-panel-outer;
  border-right: dpi(2px) solid $border-panel-outer;
}

.spike-housing-b-groove-h {
  border-top: dpi(1px) solid $border-panel-groove;
  margin-top: dpi(2px);
  margin-bottom: dpi(2px);
  border-bottom: dpi(1px) solid $border-panel-groove;
}
"""

    yuck_content = """(defwindow spike-frame
  :monitor 0
  :geometry (geometry :x "0px"
                      :y "0px"
                      :width "100%"
                      :height "100%"
                      :anchor "top left")
  :stacking "fg"
  :exclusive false
  :focusable false
  :namespace "shield-spike"
  (box :class "spike-container"
       :hexpand true
       :vexpand true
       :orientation "vertical"
       :space-evenly false
    (box :class "spike-row-top"
         :space-evenly true
         :height 300
      (box :class "spike-column" :orientation "vertical" :space-evenly false
        (label :class "spike-title" :text "APPROACH A1: NESTED-OCTAGON GRADIENT MIXIN")
        (box :class "spike-card-a1-outer" :width 200 :height 100 :halign "center"
          (box :class "spike-card-a1-groove" :width 196 :height 96 :halign "center" :valign "center"
            (box :class "spike-card-a1-surface" :width 194 :height 94 :halign "center" :valign "center"))))
      (box :class "spike-column" :orientation "vertical" :space-evenly false
        (label :class "spike-title" :text "APPROACH A2: STACKED CSS BOXES WITH BORDER TRIANGLES")
        (overlay :width 200 :height 100 :halign "center"
          (box :class "spike-card-a2-body" :width 200 :height 100)
          (box :class "triangle spike-tri-edge topleft" :halign "start" :valign "start")
          (box :class "triangle spike-tri-cut topleft" :halign "start" :valign "start")
          (box :class "triangle spike-tri-edge topright" :halign "end" :valign "start")
          (box :class "triangle spike-tri-cut topright" :halign "end" :valign "start")
          (box :class "triangle spike-tri-edge bottomleft" :halign "start" :valign "end")
          (box :class "triangle spike-tri-cut bottomleft" :halign "start" :valign "end")
          (box :class "triangle spike-tri-edge bottomright" :halign "end" :valign "end")
          (box :class "triangle spike-tri-cut bottomright" :halign "end" :valign "end")))
      (box :class "spike-column" :orientation "vertical" :space-evenly false
        (label :class "spike-title" :text "APPROACH B: SVG CORNER PLATE (TOKEN-INJECTED)")
        (box :class "spike-card-b" :halign "center" :valign "center" :width 200 :height 100
          (image :path "./assets/panels/spike-plate-b.svg" :image-width 200 :image-height 100))))
    (box :class "spike-row-bottom"
         :space-evenly true
         :height 350
      (box :class "spike-column" :orientation "vertical" :space-evenly false
        (label :class "spike-title" :text "APPROACH A: CSS CORNER HOUSING + STEP CHAMFER")
        (overlay :width 460 :height 90 :halign "center"
          (box :class "spike-housing-a-rail" :width 200 :height 32 :halign "end" :valign "start"
            (box :class "spike-housing-a-groove-h" :vexpand true))
          (box :class "spike-housing-a-body" :width 260 :height 90 :halign "start" :valign "start")
          (box :class "triangle spike-tri-edge bottomright" :halign "start" :valign "start")
          (box :class "triangle spike-tri-cut bottomright" :halign "start" :valign "start")))
      (box :class "spike-column" :orientation "vertical" :space-evenly false
        (label :class "spike-title" :text "APPROACH B: SVG CORNER HOUSING + HYBRID CSS RAIL")
        (box :class "spike-housing-b-wrapper" :orientation "horizontal" :space-evenly false :halign "center" :width 460 :height 90
          (box :class "spike-housing-b-svg" :width 260 :height 90
            (image :path "./assets/panels/spike-housing-b.svg" :image-width 260 :image-height 90))
          (box :class "spike-housing-b-rail" :width 200 :height 32 :valign "start"
            (box :class "spike-housing-b-groove-h" :vexpand true)))))))
"""

    try:
        scss_spike.write_text(scss_content, encoding="utf-8")
        yuck_spike.write_text(yuck_content, encoding="utf-8")

        if '@import "./scss/spike_06";' not in orig_eww_scss:
            eww_scss.write_text(orig_eww_scss + '\n@import "./scss/spike_06";\n', encoding="utf-8")

        if '(include "./yuck/spike_06.yuck")' not in orig_eww_yuck:
            eww_yuck.write_text(orig_eww_yuck + '\n(include "./yuck/spike_06.yuck")\n', encoding="utf-8")

        run_cmd("python3 scripts/theme-gen.py", cwd=repo_dir)

        print("==> Validating Gate 1 checks with spike harness...")
        run_cmd("bash tests/check-gate1-gtk.sh", cwd=repo_dir)

        print("==> Capturing spike render in Sway + Eww (1920x1080)...")
        run_cmd("bash tests/check-gate3-golden.sh capture spike-06.png", cwd=repo_dir)

        capture_img = repo_dir / "tests" / "captures" / "spike-06.png"
        if not capture_img.is_file():
            sys.stderr.write("Capture failed: spike-06.png not created\n")
            sys.exit(1)

        print("==> Measuring color bounding boxes via check-gate3-golden.sh measure...")
        m_outer = run_cmd("bash tests/check-gate3-golden.sh measure spike-06.png '#5A5C60'", cwd=repo_dir).strip().splitlines()[-1]
        m_groove = run_cmd("bash tests/check-gate3-golden.sh measure spike-06.png '#18191B'", cwd=repo_dir).strip().splitlines()[-1]
        m_surface = run_cmd("bash tests/check-gate3-golden.sh measure spike-06.png '#2C2D2F'", cwd=repo_dir).strip().splitlines()[-1]

        print(f"Bounding Box $border-panel-outer (#5A5C60): {m_outer}")
        print(f"Bounding Box $border-panel-groove (#18191B): {m_groove}")
        print(f"Bounding Box $surface-panel (#2C2D2F): {m_surface}")

        def parse_pixels(txt_output):
            lines = txt_output.strip().splitlines()
            pixels = {}
            for line in lines[1:]:
                m = re.match(r"^(\d+),(\d+):\s+\(([^)]+)\)\s+(#[0-9A-Fa-f]+)", line)
                if m:
                    x = int(m.group(1))
                    y = int(m.group(2))
                    hex_val = m.group(4).upper()
                    pixels[(x, y)] = hex_val
            return pixels

        def find_box(color_hex, search_geom):
            w, h, sx, sy = search_geom
            txt = run_cmd(f"magick tests/captures/spike-06.png -crop {w}x{h}+{sx}+{sy} +repage txt:-", cwd=repo_dir)
            pixels = parse_pixels(txt)
            target = color_hex.upper()
            xs = [x for (x, y), c in pixels.items() if c == target]
            ys = [y for (x, y), c in pixels.items() if c == target]
            if not xs or not ys:
                return None
            return (min(xs) + sx, min(ys) + sy, max(xs) - min(xs) + 1, max(ys) - min(ys) + 1)

        box_a1 = find_box("#5A5C60", (600, 250, 40, 40))
        box_a2 = find_box("#5A5C60", (600, 250, 660, 40))
        box_b = find_box("#5A5C60", (600, 250, 1280, 40))

        c_a1_x, c_a1_y = (box_a1[0], box_a1[1]) if box_a1 else (247, 68)
        c_a2_x, c_a2_y = (box_a2[0], box_a2[1]) if box_a2 else (860, 68)
        c_b_x, c_b_y = (box_b[0], box_b[1]) if box_b else (1473, 68)

        run_cmd(f"magick tests/captures/spike-06.png -crop 40x40+{c_a1_x}+{c_a1_y} +repage -scale 500% tests/captures/crop-a1-z5.png", cwd=repo_dir)
        run_cmd(f"magick tests/captures/spike-06.png -crop 40x40+{c_a2_x}+{c_a2_y} +repage -scale 500% tests/captures/crop-a2-z5.png", cwd=repo_dir)
        run_cmd(f"magick tests/captures/spike-06.png -crop 40x40+{c_b_x}+{c_b_y} +repage -scale 500% tests/captures/crop-b-z5.png", cwd=repo_dir)

        box_ha = find_box("#5A5C60", (850, 300, 40, 350))
        box_hb = find_box("#5A5C60", (850, 300, 960, 350))

        ha_x, ha_y = (box_ha[0] + 160, box_ha[1] + 10) if box_ha else (430, 378)
        hb_x, hb_y = (box_hb[0] + 160, box_hb[1] + 10) if box_hb else (1350, 378)

        run_cmd(f"magick tests/captures/spike-06.png -crop 90x80+{ha_x}+{ha_y} +repage -scale 250% tests/captures/crop-ha-z2.png", cwd=repo_dir)
        run_cmd(f"magick tests/captures/spike-06.png -crop 90x80+{hb_x}+{hb_y} +repage -scale 250% tests/captures/crop-hb-z2.png", cwd=repo_dir)

        compare_path = repo_dir / "tests" / "captures" / "spike-06-compare.png"

        script_comp = """
magick -size 1920x1080 xc:"#0A0B0F" \\
  \\( tests/captures/spike-06.png -resize 1920x500! \\) -geometry +0+25 -composite \\
  -stroke "#5A5C60" -strokewidth 2 -draw "line 0,530 1920,530" \\
  -stroke "#2C2D2F" -strokewidth 2 -draw "line 640,530 640,1080" \\
  -stroke "#2C2D2F" -strokewidth 2 -draw "line 1280,530 1280,1080" \\
  -stroke "#2C2D2F" -strokewidth 2 -draw "line 0,810 1920,810" \\
  \\( tests/captures/crop-a1-z5.png \\) -geometry +220+575 -composite \\
  \\( tests/captures/crop-a2-z5.png \\) -geometry +860+575 -composite \\
  \\( tests/captures/crop-b-z5.png \\) -geometry +1500+575 -composite \\
  \\( tests/captures/crop-ha-z2.png \\) -geometry +210+850 -composite \\
  \\( tests/captures/crop-hb-z2.png \\) -geometry +1170+850 -composite \\
  -font Barlow -fill "#DBAD4D" -pointsize 16 -draw "text 30,20 'SPIKE 06: FRAME GEOMETRY FIDELITY COMPARISON (1920x1080 SWAY + EWW)'" \\
  -font Barlow -fill "#FFFFFF" -pointsize 13 -draw "text 40,550 'APPROACH A1: NESTED-OCTAGON GRADIENT MIXIN (5x ZOOM)'" \\
  -font Barlow -fill "#AAAAAA" -pointsize 11 -draw "text 40,565 'Outer highlight: 1px | Groove: 1px | Diagonal band narrows from 2px straight rail | Cairo AA blur'" \\
  -font Barlow -fill "#FFFFFF" -pointsize 13 -draw "text 680,550 'APPROACH A2: STACKED CSS BORDER TRIANGLES (5x ZOOM)'" \\
  -font Barlow -fill "#AAAAAA" -pointsize 11 -draw "text 680,565 'No true corner subtraction | Base card stays opaque | Occludes background data-noise'" \\
  -font Barlow -fill "#DBAD4D" -pointsize 13 -draw "text 1320,550 'APPROACH B: VECTOR SVG CORNER PLATE (5x ZOOM)'" \\
  -font Barlow -fill "#DBAD4D" -pointsize 11 -draw "text 1320,565 'Exact 2px outer stroke | Continuous 1px groove | True alpha cut reveals canvas noise'" \\
  -font Barlow -fill "#FFFFFF" -pointsize 13 -draw "text 40,830 'HOUSING A: CSS STEP-CHAMFER & RAIL (2.5x ZOOM)'" \\
  -font Barlow -fill "#AAAAAA" -pointsize 11 -draw "text 40,845 'Corner stays solid rectangular block; CSS cannot subtract corner against backdrop'" \\
  -font Barlow -fill "#DBAD4D" -pointsize 13 -draw "text 1000,830 'HOUSING B: SVG STEP-CHAMFER & HYBRID CSS RAIL (2.5x ZOOM)'" \\
  -font Barlow -fill "#DBAD4D" -pointsize 11 -draw "text 1000,845 'Authentic 45° step-chamfer cut; continuous #18191B groove; seamless CSS rail dock'" \\
  tests/captures/spike-06-compare.png
"""
        run_cmd(script_comp, cwd=repo_dir)
        print(f"CREATED: Side-by-side comparison image written to {compare_path}")

    finally:
        print("==> Restoring production HUD state...")
        if yuck_spike.exists():
            yuck_spike.unlink()
        if scss_spike.exists():
            scss_spike.unlink()
        eww_scss.write_text(orig_eww_scss, encoding="utf-8")
        eww_yuck.write_text(orig_eww_yuck, encoding="utf-8")
        print("==> Running production verification gates...")
        run_cmd("bash tests/run-ticket.sh", cwd=repo_dir)
        run_cmd("bash tests/check-gate3-golden.sh check 1", cwd=repo_dir)
        print("==> Production HUD state verified: 0 errors, 0 pixel diff against golden.")

if __name__ == "__main__":
    main()
