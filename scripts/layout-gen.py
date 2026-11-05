#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from jsonschema import Draft202012Validator

def load_layout(layout_path, schema_path=None):
    if not layout_path.is_file():
        sys.stderr.write(f"FAIL [layout-gen]: File not found: {layout_path}\n")
        sys.exit(1)
    try:
        data = json.loads(layout_path.read_text(encoding="utf-8"))
    except Exception as exc:
        sys.stderr.write(f"FAIL [layout-gen]: Invalid JSON in {layout_path}: {exc}\n")
        sys.exit(1)

    if schema_path and schema_path.is_file():
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
            errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
            if errors:
                err = errors[0]
                loc = ".".join(str(p) for p in err.path) or "<root>"
                sys.stderr.write(f"FAIL [layout-gen]: {layout_path.name} failed schema at '{loc}': {err.message}\n")
                sys.exit(1)
        except Exception as exc:
            sys.stderr.write(f"FAIL [layout-gen]: Schema validation error: {exc}\n")
            sys.exit(1)

    return data

def generate_scss(layout):
    s = layout["screen"]
    v = layout["void"]
    c = layout["canvas"]
    e = layout["emblem"]
    b = layout["bars"]
    sp = layout["side_panels"]
    r = layout["rails"]
    cp = layout["corner_plates"]
    bv = cp["bevel"]
    se = layout.get("star_emblem", {"size": 24})
    op = layout.get("operator", {"medallion_size": 64, "icon_size": 14})
    wp = layout["workspace_pills"]
    gg = layout.get("gauges", {"width": 48, "header_height": 20, "rung_height": 18, "gap": 18})
    vc = layout.get("volume_cluster", {"width": 38, "height": 28, "gap": 8, "chamfer_cut": 8, "bar_width": 2, "bar_height": 8, "bar_gap": 4})
    sp_pill = layout.get("status_pill", {"width": 132, "height": 26, "gap": 8, "chamfer_cut": 4, "indicator_height": 3, "glyph_size": 14})
    eq_pod = layout.get("equalizer_pod", {"width": 36, "height": 26, "chamfer_cut": 4, "bar_width": 3, "bar_height": 16, "bar_gap": 3})
    ld = layout.get("left_dock", {})
    bm = layout.get("bottom_menu", {})

    lines = [
        f"$screen-width: dpi({s['width']}px);",
        f"$screen-height: dpi({s['height']}px);",
        f"$void-padding: dpi({v['padding']}px);",
        f"$canvas-width: dpi({c['width']}px);",
        f"$canvas-height: dpi({c['height']}px);",
        f"$emblem-size: dpi({e['size']}px);",
        f"$star-emblem-size: dpi({se['size']}px);",
        f"$operator-medallion-size: dpi({op['medallion_size']}px);",
        f"$operator-icon-size: dpi({op['icon_size']}px);",
        f"$workspace-pill-width: dpi({wp['width']}px);",
        f"$workspace-pill-height: dpi({wp['height']}px);",
        f"$workspace-pill-gap: dpi({wp['gap']}px);",
        f"$workspace-pill-cut: dpi({wp['chamfer_cut']}px);",
        f"$workspace-pill-bar-width: dpi({wp['bar_width']}px);",
        f"$workspace-pill-bar-height: dpi({wp['bar_height']}px);",
        f"$workspace-pill-top-offset: dpi({wp['top_offset']}px);",
        f"$workspace-pill-left-offset: dpi({wp['left_offset']}px);",
        f"$bar-top-height: dpi({b['top']['height']}px);",
        f"$bar-bottom-height: dpi({b['bottom']['height']}px);",
        f"$side-left-width: dpi({sp['left']['width']}px);",
        f"$side-left-height: dpi({sp['left']['height']}px);",
        f"$side-left-top-offset: dpi({sp['left'].get('top_offset', 30)}px);",
        f"$side-right-width: dpi({sp['right']['width']}px);",
        f"$side-right-height: dpi({sp['right']['height']}px);",
        f"$side-right-top-offset: dpi({sp['right'].get('top_offset', 125)}px);",
        f"$side-right-upper-width: dpi({sp['right'].get('upper_width', 60)}px);",
        f"$side-right-upper-height: dpi({sp['right'].get('upper_height', 130)}px);",
        f"$side-right-lower-width: dpi({sp['right'].get('lower_width', 80)}px);",
        f"$side-right-lower-height: dpi({sp['right'].get('lower_height', 310)}px);",
        f"$rail-top-height: dpi({r['top']['height']}px);",
        f"$rail-bottom-height: dpi({r['bottom']['height']}px);",
        f"$rail-left-width: dpi({r['left']['width']}px);",
        f"$rail-right-width: dpi({r['right']['width']}px);",
        f"$corner-top-left-width: dpi({cp['top_left']['width']}px);",
        f"$corner-top-left-height: dpi({cp['top_left']['height']}px);",
        f"$corner-top-left-cut: dpi({cp['top_left']['chamfer_cut']}px);",
        f"$corner-top-right-width: dpi({cp['top_right']['width']}px);",
        f"$corner-top-right-height: dpi({cp['top_right']['height']}px);",
        f"$corner-top-right-cut: dpi({cp['top_right']['chamfer_cut']}px);",
        f"$corner-bottom-left-width: dpi({cp['bottom_left']['width']}px);",
        f"$corner-bottom-left-height: dpi({cp['bottom_left']['height']}px);",
        f"$corner-bottom-left-cut: dpi({cp['bottom_left']['chamfer_cut']}px);",
        f"$corner-bottom-right-width: dpi({cp['bottom_right']['width']}px);",
        f"$corner-bottom-right-height: dpi({cp['bottom_right']['height']}px);",
        f"$corner-bottom-right-cut: dpi({cp['bottom_right']['chamfer_cut']}px);",
        f"$bevel-outer-border: dpi({bv['outer_border']}px);",
        f"$bevel-inner-groove: dpi({bv['inner_groove']}px);",
        f"$gauge-width: dpi({gg['width']}px);",
        f"$gauge-header-height: dpi({gg['header_height']}px);",
        f"$gauge-rung-height: dpi({gg['rung_height']}px);",
        f"$gauge-gap: dpi({gg['gap']}px);",
        f"$gauge-gap-upper: dpi({gg.get('gap_upper', 18)}px);",
        f"$gauge-gap-lower: dpi({gg.get('gap_lower', 17)}px);",
        f"$volume-pill-width: dpi({vc['width']}px);",
        f"$volume-pill-height: dpi({vc['height']}px);",
        f"$volume-pill-gap: dpi({vc['gap']}px);",
        f"$volume-pill-cut: dpi({vc['chamfer_cut']}px);",
        f"$volume-bar-width: dpi({vc['bar_width']}px);",
        f"$volume-bar-height: dpi({vc['bar_height']}px);",
        f"$volume-bar-gap: dpi({vc['bar_gap']}px);",
        f"$volume-housing-pad-top: dpi({vc.get('housing_pad_top', 110)}px);",
        f"$status-pill-width: dpi({sp_pill['width']}px);",
        f"$status-pill-height: dpi({sp_pill['height']}px);",
        f"$status-pill-gap: dpi({sp_pill['gap']}px);",
        f"$status-pill-cut: dpi({sp_pill['chamfer_cut']}px);",
        f"$status-pill-indicator-height: dpi({sp_pill['indicator_height']}px);",
        f"$status-pill-glyph-size: dpi({sp_pill['glyph_size']}px);",
        f"$equalizer-pod-width: dpi({eq_pod['width']}px);",
        f"$equalizer-pod-height: dpi({eq_pod['height']}px);",
        f"$equalizer-pod-cut: dpi({eq_pod['chamfer_cut']}px);",
        f"$equalizer-bar-width: dpi({eq_pod['bar_width']}px);",
        f"$equalizer-bar-height: dpi({eq_pod['bar_height']}px);",
        f"$equalizer-bar-gap: dpi({eq_pod['bar_gap']}px);",
        f"$left-dock-width: dpi({ld.get('width', 74)}px);",
        f"$left-dock-height: dpi({ld.get('height', 240)}px);",
        f"$left-dock-chamfer-cut: dpi({ld.get('chamfer_cut', 58)}px);",
        f"$left-dock-play-size: dpi({ld.get('play_size', 24)}px);",
        f"$left-dock-play-pad-top: dpi({ld.get('play_pad_top', 58)}px);",
        f"$left-dock-play-pad-left: dpi({ld.get('play_pad_left', 42)}px);",
        f"$left-dock-slot-width: dpi({ld.get('slot_width', 10)}px);",
        f"$left-dock-slot-height: dpi({ld.get('slot_height', 61)}px);",
        f"$left-dock-slot-tall-height: dpi({ld.get('slot_tall_height', 28)}px);",
        f"$left-dock-slot-short-height: dpi({ld.get('slot_short_height', 8)}px);",
        f"$left-dock-slot-gap: dpi({ld.get('slot_gap', 3)}px);",
        f"$left-dock-slot-pad-left: dpi({ld.get('slot_pad_left', 49)}px);",
        f"$left-dock-pip-size: dpi({ld.get('pip_size', 6)}px);",
        f"$left-dock-pip-gap: dpi({ld.get('pip_gap', 4)}px);",
        f"$left-dock-pip-pad-top: dpi({ld.get('pip_pad_top', 12)}px);",
        f"$left-dock-pip-pad-left: dpi({ld.get('pip_pad_left', 51)}px);",
        f"$left-dock-rail-gap: dpi({ld.get('rail_gap', 20)}px);",
        f"$bottom-menu-utility-height: dpi({bm.get('utility_height', 20)}px);",
        f"$bottom-menu-utility-width: dpi({bm.get('utility_width', 144)}px);",
        f"$bottom-menu-utility-sm-width: dpi({bm.get('utility_sm_width', 124)}px);",
        f"$bottom-menu-utility-offset-localshare: dpi({bm.get('utility_offset_localshare', 13)}px);",
        f"$bottom-menu-utility-offset-websearch: dpi({bm.get('utility_offset_websearch', 147)}px);",
        f"$bottom-menu-utility-offset-colors: dpi({bm.get('utility_offset_colors', 281)}px);",
        f"$bottom-menu-utility-icon-size: dpi({bm.get('utility_icon_size', 12)}px);",
        f"$bottom-menu-utility-label-spacing: dpi({bm.get('utility_label_spacing', 6)}px);",
        f"$bottom-menu-tab-height: dpi({bm.get('tab_height', 20)}px);",
        f"$bottom-menu-tab-width: dpi({bm.get('tab_width', 144)}px);",
        f"$bottom-menu-tab-app-width: dpi({bm.get('tab_app_width', 148)}px);",
        f"$bottom-menu-tab-offset-powermenu: dpi({bm.get('tab_offset_powermenu', 412)}px);",
        f"$bottom-menu-tab-offset-bluetooth: dpi({bm.get('tab_offset_bluetooth', 546)}px);",
        f"$bottom-menu-tab-offset-applications: dpi({bm.get('tab_offset_applications', 680)}px);",
        f"$bottom-menu-tray-bottom-offset: dpi({bm.get('tray_bottom_offset', 20)}px);",
        f"$bottom-menu-deck-bottom-offset: dpi({bm.get('deck_bottom_offset', 42)}px);",
    ]
    return "\n".join(lines) + "\n"

def generate_yuck(layout):
    s = layout["screen"]
    v = layout["void"]
    c = layout["canvas"]
    e = layout["emblem"]
    b = layout["bars"]
    sp = layout["side_panels"]
    r = layout["rails"]
    cp = layout["corner_plates"]
    bv = cp["bevel"]
    se = layout.get("star_emblem", {"size": 24})
    op = layout.get("operator", {"medallion_size": 64, "icon_size": 14})
    wp = layout["workspace_pills"]
    gg = layout.get("gauges", {"width": 48, "header_height": 20, "rung_height": 18, "gap": 18})
    vc = layout.get("volume_cluster", {"width": 38, "height": 28, "gap": 8, "chamfer_cut": 8, "bar_width": 2, "bar_height": 8, "bar_gap": 4})
    sp_pill = layout.get("status_pill", {"width": 132, "height": 26, "gap": 8, "chamfer_cut": 4, "indicator_height": 3, "glyph_size": 14})
    eq_pod = layout.get("equalizer_pod", {"width": 36, "height": 26, "chamfer_cut": 4, "bar_width": 3, "bar_height": 16, "bar_gap": 3})
    ld = layout.get("left_dock", {})
    bm = layout.get("bottom_menu", {})

    lines = [
        f"(defvar screen_width {s['width']})",
        f"(defvar screen_height {s['height']})",
        f"(defvar void_padding {v['padding']})",
        f"(defvar canvas_width {c['width']})",
        f"(defvar canvas_height {c['height']})",
        f"(defvar emblem_size {e['size']})",
        f"(defvar star_emblem_size {se['size']})",
        f"(defvar operator_medallion_size {op['medallion_size']})",
        f"(defvar operator_icon_size {op['icon_size']})",
        f"(defvar workspace_pill_width {wp['width']})",
        f"(defvar workspace_pill_height {wp['height']})",
        f"(defvar workspace_pill_gap {wp['gap']})",
        f"(defvar workspace_pill_cut {wp['chamfer_cut']})",
        f"(defvar workspace_pill_bar_width {wp['bar_width']})",
        f"(defvar workspace_pill_bar_height {wp['bar_height']})",
        f"(defvar workspace_pill_top_offset {wp['top_offset']})",
        f"(defvar workspace_pill_left_offset {wp['left_offset']})",
        f"(defvar bar_top_height {b['top']['height']})",
        f"(defvar bar_bottom_height {b['bottom']['height']})",
        f"(defvar side_left_width {sp['left']['width']})",
        f"(defvar side_left_height {sp['left']['height']})",
        f"(defvar side_left_top_offset {sp['left'].get('top_offset', 30)})",
        f"(defvar side_right_width {sp['right']['width']})",
        f"(defvar side_right_height {sp['right']['height']})",
        f"(defvar side_right_top_offset {sp['right'].get('top_offset', 125)})",
        f"(defvar side_right_upper_width {sp['right'].get('upper_width', 60)})",
        f"(defvar side_right_upper_height {sp['right'].get('upper_height', 130)})",
        f"(defvar side_right_lower_width {sp['right'].get('lower_width', 80)})",
        f"(defvar side_right_lower_height {sp['right'].get('lower_height', 310)})",
        f"(defvar rail_top_height {r['top']['height']})",
        f"(defvar rail_bottom_height {r['bottom']['height']})",
        f"(defvar rail_left_width {r['left']['width']})",
        f"(defvar rail_right_width {r['right']['width']})",
        f"(defvar corner_top_left_width {cp['top_left']['width']})",
        f"(defvar corner_top_left_height {cp['top_left']['height']})",
        f"(defvar corner_top_left_cut {cp['top_left']['chamfer_cut']})",
        f"(defvar corner_top_right_width {cp['top_right']['width']})",
        f"(defvar corner_top_right_height {cp['top_right']['height']})",
        f"(defvar corner_top_right_cut {cp['top_right']['chamfer_cut']})",
        f"(defvar corner_bottom_left_width {cp['bottom_left']['width']})",
        f"(defvar corner_bottom_left_height {cp['bottom_left']['height']})",
        f"(defvar corner_bottom_left_cut {cp['bottom_left']['chamfer_cut']})",
        f"(defvar corner_bottom_right_width {cp['bottom_right']['width']})",
        f"(defvar corner_bottom_right_height {cp['bottom_right']['height']})",
        f"(defvar corner_bottom_right_cut {cp['bottom_right']['chamfer_cut']})",
        f"(defvar bevel_outer_border {bv['outer_border']})",
        f"(defvar bevel_inner_groove {bv['inner_groove']})",
        f"(defvar gauge_width {gg['width']})",
        f"(defvar gauge_header_height {gg['header_height']})",
        f"(defvar gauge_rung_height {gg['rung_height']})",
        f"(defvar gauge_gap {gg['gap']})",
        f"(defvar gauge_gap_upper {gg.get('gap_upper', 18)})",
        f"(defvar gauge_gap_lower {gg.get('gap_lower', 17)})",
        f"(defvar volume_pill_width {vc['width']})",
        f"(defvar volume_pill_height {vc['height']})",
        f"(defvar volume_pill_gap {vc['gap']})",
        f"(defvar volume_pill_cut {vc['chamfer_cut']})",
        f"(defvar volume_bar_width {vc['bar_width']})",
        f"(defvar volume_bar_height {vc['bar_height']})",
        f"(defvar volume_bar_gap {vc['bar_gap']})",
        f"(defvar volume_housing_pad_top {vc.get('housing_pad_top', 110)})",
        f"(defvar status_pill_width {sp_pill['width']})",
        f"(defvar status_pill_height {sp_pill['height']})",
        f"(defvar status_pill_gap {sp_pill['gap']})",
        f"(defvar status_pill_cut {sp_pill['chamfer_cut']})",
        f"(defvar status_pill_indicator_height {sp_pill['indicator_height']})",
        f"(defvar status_pill_glyph_size {sp_pill['glyph_size']})",
        f"(defvar equalizer_pod_width {eq_pod['width']})",
        f"(defvar equalizer_pod_height {eq_pod['height']})",
        f"(defvar equalizer_pod_cut {eq_pod['chamfer_cut']})",
        f"(defvar equalizer_bar_width {eq_pod['bar_width']})",
        f"(defvar equalizer_bar_height {eq_pod['bar_height']})",
        f"(defvar equalizer_bar_gap {eq_pod['bar_gap']})",
        f"(defvar left_dock_width {ld.get('width', 74)})",
        f"(defvar left_dock_height {ld.get('height', 240)})",
        f"(defvar left_dock_chamfer_cut {ld.get('chamfer_cut', 58)})",
        f"(defvar left_dock_play_size {ld.get('play_size', 24)})",
        f"(defvar left_dock_play_pad_top {ld.get('play_pad_top', 58)})",
        f"(defvar left_dock_play_pad_left {ld.get('play_pad_left', 42)})",
        f"(defvar left_dock_slot_width {ld.get('slot_width', 10)})",
        f"(defvar left_dock_slot_height {ld.get('slot_height', 61)})",
        f"(defvar left_dock_slot_tall_height {ld.get('slot_tall_height', 28)})",
        f"(defvar left_dock_slot_short_height {ld.get('slot_short_height', 8)})",
        f"(defvar left_dock_slot_gap {ld.get('slot_gap', 3)})",
        f"(defvar left_dock_slot_pad_left {ld.get('slot_pad_left', 49)})",
        f"(defvar left_dock_pip_size {ld.get('pip_size', 6)})",
        f"(defvar left_dock_pip_gap {ld.get('pip_gap', 4)})",
        f"(defvar left_dock_pip_pad_top {ld.get('pip_pad_top', 12)})",
        f"(defvar left_dock_pip_pad_left {ld.get('pip_pad_left', 51)})",
        f"(defvar left_dock_rail_gap {ld.get('rail_gap', 20)})",
        f"(defvar left_dock_rail_height {ld.get('rail_height', 484)})",
        f"(defvar bottom_menu_utility_height {bm.get('utility_height', 20)})",
        f"(defvar bottom_menu_utility_width {bm.get('utility_width', 144)})",
        f"(defvar bottom_menu_utility_sm_width {bm.get('utility_sm_width', 124)})",
        f"(defvar bottom_menu_utility_offset_localshare {bm.get('utility_offset_localshare', 13)})",
        f"(defvar bottom_menu_utility_offset_websearch {bm.get('utility_offset_websearch', 147)})",
        f"(defvar bottom_menu_utility_offset_colors {bm.get('utility_offset_colors', 281)})",
        f"(defvar bottom_menu_utility_icon_size {bm.get('utility_icon_size', 12)})",
        f"(defvar bottom_menu_utility_label_spacing {bm.get('utility_label_spacing', 6)})",
        f"(defvar bottom_menu_tab_height {bm.get('tab_height', 20)})",
        f"(defvar bottom_menu_tab_width {bm.get('tab_width', 144)})",
        f"(defvar bottom_menu_tab_app_width {bm.get('tab_app_width', 148)})",
        f"(defvar bottom_menu_tab_offset_powermenu {bm.get('tab_offset_powermenu', 412)})",
        f"(defvar bottom_menu_tab_offset_bluetooth {bm.get('tab_offset_bluetooth', 546)})",
        f"(defvar bottom_menu_tab_offset_applications {bm.get('tab_offset_applications', 680)})",
        f"(defvar bottom_menu_tray_bottom_offset {bm.get('tray_bottom_offset', 20)})",
        f"(defvar bottom_menu_deck_bottom_offset {bm.get('deck_bottom_offset', 42)})",
    ]
    return "\n".join(lines) + "\n"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    repo_dir = Path(__file__).resolve().parent.parent
    layout_path = repo_dir / "layout.json"
    schema_path = repo_dir / "schemas" / "layout.schema.json"
    scss_out = repo_dir / "scss" / "_layout.scss"
    yuck_out = repo_dir / "yuck" / "_layout.yuck"

    layout = load_layout(layout_path, schema_path)
    expected_scss = generate_scss(layout)
    expected_yuck = generate_yuck(layout)

    if args.check:
        if not scss_out.is_file():
            sys.stderr.write(f"FAIL [layout-gen]: Missing {scss_out}\n")
            sys.exit(1)
        if not yuck_out.is_file():
            sys.stderr.write(f"FAIL [layout-gen]: Missing {yuck_out}\n")
            sys.exit(1)

        actual_scss = scss_out.read_text(encoding="utf-8")
        if actual_scss != expected_scss:
            sys.stderr.write(f"FAIL [layout-gen]: {scss_out} does not match layout.json\n")
            sys.exit(1)

        actual_yuck = yuck_out.read_text(encoding="utf-8")
        if actual_yuck != expected_yuck:
            sys.stderr.write(f"FAIL [layout-gen]: {yuck_out} does not match layout.json\n")
            sys.exit(1)

        print("PASS [layout-gen]: Generated layout files match layout.json")
        return 0

    scss_out.write_text(expected_scss, encoding="utf-8")
    yuck_out.write_text(expected_yuck, encoding="utf-8")
    print(f"Generated {scss_out} and {yuck_out} from {layout_path}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
