# Spec: S.H.I.E.L.D. OS HUD Desktop Shell (`shieldOS-eww`)

Status: ready-for-agent

## Problem Statement

Users wanting a tactical S.H.I.E.L.D.-style desktop HUD (`reference/shield-os.png`) on Wayland lack a modular, lightweight implementation that renders 45° chamfered steel-grey perimeter bezels, a glowing golden eagle centerpiece with a 56-star ring, vertical CPU/RAM ladder gauges, angled window tabs, and trapezoidal utility menus without relying on heavy desktop environments or browser-only CSS features unsupported by GTK.

## Solution

Build `shieldOS-eww` from scratch as a modular Eww (ElKowar's Wacky Widgets) desktop shell configuration in `shieldOS-eww/`. Following the design tokens, typography, shape language, component inventory, and staged build order in `DESIGN.md`, the shell combines GTK3-safe SCSS tokens with parameterized SVG chamfered panels, multi-compositor IPC listeners (per ADR-0001), and theme-switching hooks (per ADR-0002).

## User Stories

### HUD Canvas & Perimeter Frame (Drafting Sheet Equivalent)
1. As an operator, I want a full-screen bottom-layer HUD canvas with a dark void backdrop (`#0A0B0F` / `#0E0F11`), golden-amber vertical data-noise waveform lines, and reticle markers, so that my desktop backdrop establishes the S.H.I.E.L.D. tactical aesthetic.
2. As an operator, I want a centered golden S.H.I.E.L.D. eagle emblem (`#DBAD4D` with outer glow) encircled by 56 icy-white 5-pointed stars (`#D0E9F0`), so that the central desktop focal point matches the reference mockup.
3. As an operator, I want a discontinuous steel-grey chamfered perimeter frame (`#2C2D2F` fill, `#5A5C60` bevel highlight, `#18191B` inner groove) wrapping all four screen edges and corners at 45° angles, so that all HUD modules sit inside a cohesive tactical bezel.
4. As an operator on displays of varying DPI, I want all pixel and font dimensions wrapped in the `dpi()` scaling function, so that the HUD scales cleanly across resolutions.

### Top-Left Operator Module & Top-Right Date Block
5. As an operator, I want a circular golden S.H.I.E.L.D. badge in the top-left corner adjacent to the live system clock (`HH:MM:SS`), so that time and insignia are immediately visible.
6. As an operator, I want an amber-orange version tag (`V0.1`, `#C08333`) and my active call-sign (`OPERATOR. <USER>`) displayed beneath the clock, so that session identity and shell version are clear.
7. As an operator, I want two circular status icons (ring and 4-segment target crosshair) integrated into the top-left frame bevel, so that auxiliary status triggers are accessible.
8. As an operator, I want a top-right chamfered date module showing a wide geometric day number (`21`), an orange month-year pill (`NOV - 2025` in `#EA972D` with `#0E0F11` text), and the uppercase weekday (`FRI`), so that calendar context is readable at a glance.

### Workspace Pills (Zones `1`–`10`) & Window Tabs
9. As an operator, I want ten numbered workspace pills (`1`–`10`) along the top bar, so that I can monitor and switch across all ten virtual workspaces.
10. As an operator, I want focused workspaces rendered with a steel-teal fill (`#4F7E86`) and bright ice-teal top bar (`#AFDBE6`), occupied unfocused workspaces marked with an amber-orange top bar (`#C08333`), and empty workspaces rendered in dark grey (`#4E4E4E`), so that workspace state is unambiguous.
11. As an operator, I want to click any workspace pill `1`–`10` to switch directly to that workspace across Niri, Hyprland, or Sway, so that workspace navigation works with mouse or touch.
12. As an operator, I want up to four angled parallelogram window tabs to the right of workspace `10` showing an app prefix code, window title, and colored status micro-badge (`#C08333` orange or `#AD2927` red), so that active tasks can be identified and focused.

### Right-Edge CPU / RAM Vertical Gauges & Quick Tabs
13. As an operator, I want a vertical segmented `CPU` ladder gauge (`100`, `80`, `60`, `40`, active `%`, active load) on the upper-right edge with a dark gold header (`#5D440B`) and bright amber active cells (`#FEB703`), so that processor load is visible in real time.
14. As an operator, I want a stacked vertical segmented `RAM` ladder gauge (`100`, `80`, active `%`, `40`, `20`, `0`) below the CPU gauge that highlights the active memory bucket in bright amber (`#FEB703`), so that memory utilization is visible at a glance.
15. As an operator, I want three angled quick-action mini-tabs on the lower-right vertical bezel and a 4-pointed star emblem in the bottom-right corner, so that quick toggles and HUD lock/hide actions are reachable from the right edge.

### Left Side Panel & Bottom-Left Connectivity Pod
16. As an operator, I want a vertical chamfered panel on the left screen edge with a circular play (`▶`) trigger and segmented vertical slot indicators, so that media playback or parked slots can be controlled from the left bezel.
17. As an operator, I want a bottom-left chamfered connectivity pill with a crimson top alert bar (`#9D000B`), robot/drone glyph, and `DISCONNECTED` (or active network SSID) readout, so that network loss is immediately conspicuous.
18. As an operator, I want a hexagonal 4-bar cyan equalizer/signal pod (`#0B4A5C` / `#AFDBE6`) next to the connectivity pill, so that live audio output or wireless link strength is visualized.

### Bottom Utility Links & Trapezoid Menu Tabs (Application Register & Controls)
19. As an operator, I want recessed bottom-center utility triggers for `LOCALSHARE`, `WEBSEARCH`, and `COLORS` with matching icons, so that file sharing, web search, and theme rotation are one click away.
20. As an operator, I want raised trapezoid tabs on the bottom-right for `POWERMENU`, `BLUETOOTH`, and `APPLICATIONS`, with the active tab illuminated in deep teal (`#0B4A5C`) and bordered in ice-teal (`#AFDBE6`), so that primary shell overlays have clear active feedback.
21. As an operator, I want clicking `APPLICATIONS` to summon the keyboard-driven Application Register overlay, `BLUETOOTH` to open Bluetooth controls, `POWERMENU` to open session power actions, and `COLORS` to rotate the active HUD theme palette.

## Implementation Decisions

- **Modular Eww Architecture (`shieldOS-eww/`)**:
  - Root `eww.yuck` holds only shared `defpoll`, `deflisten`, `defvar`, and `(include ...)` statements.
  - Root `eww.scss` holds only `@import "./theme"`, `@import "./scss/_scale"`, global reset, base classes, and feature `@import` statements.
  - One `yuck/<module>.yuck` + `scss/<module>.scss` pair per HUD zone (`background`, `top-bar`, `side-panels`, `bottom-bar`, `overlays`).
- **GTK3 CSS + SVG Hybrid Geometry**:
  - Relative `url()` in SCSS does not resolve (fails silently in GTK3 CSS). All external assets must load via Yuck `image :path` inside an `overlay`.
  - Most 45° chamfers, angled cuts, and bevels are built natively in SCSS using 4-quadrant clipped linear gradients (`@mixin octagon`, `@mixin cut2`) and border-triangles (`.triangle.<corner>`), directly consuming SCSS theme tokens at compile time.
  - Parameterized SVG backing plates in `assets/panels/` are reserved for corner plates only, with `scripts/theme-gen.py` recoloring the few remaining SVGs.
  - **Component -> Technique Mapping**:
    | Component | Technique | Notes |
    |---|---|---|
    | Workspace pills, date pill, small plates (4-6px cuts) | four-corner octagon mixin | opaque colors only (no rgba); never set background-color on the same element |
    | Frame bevels (#5A5C60 edge, #18191B groove) | nested octagons | measure the diagonal band thickness; spike before committing |
    | Window tabs, bottom trapezoid tabs (slants, variable width) | fixed-size slant caps + stretchy body box | paint in the tab's own color (additive); a $xbg mask is not a real cut and shows over the noise |
    | Frame corner plates (24-44px step-chamfers) | SVG via `image :path`, or stacked boxes | spike one corner both ways in Milestone 2 |
    | Emblem, 56-star ring, data noise, glow | SVG via `image :path` | the glow rgba token belongs here |
- **Multi-Compositor & Progressive Telemetry Fallbacks (ADR-0001)**:
  - `scripts/compositor.py` auto-detects Niri, Hyprland, or Sway IPC and falls back to a local state file in headless/test environments.
  - `scripts/telemetry.py` reads `/proc/stat`, `/proc/loadavg`, and `/proc/meminfo` with safe fallback values.
- **Theme Token Synchronization (ADR-0002)**:
  - All semantic colors reside in `themes/*.scss` (`themes/shield-gold.scss` as default). `scripts/theme-gen.py` synchronizes SVG fill/stroke hex values with the active theme for layered SVGs (`glow.svg`, `star-ring.svg`, `placeholder.svg`, `data-noise.svg`, corner plates).

## Testing Decisions

- **Verification Cadence**:
  - Run **Gates 1 + 2 on every ticket**; run **Gate 3 at every milestone**.
- **Gate 1 — GTK3 CSS Denylist & Headless Eww Runtime Gate (Per Ticket)**:
  - Compile SCSS (`sass --no-source-map --silence-deprecation=import,global-builtin shieldOS-eww/eww.scss /tmp/shield.css`) and run a denylist linter on compiled CSS (`/tmp/shield.css`) to reject unsupported GTK3 CSS properties and syntaxes:
    - `display: flex`, `justify-content`, `align-items`, `flex-direction`, `position`, `z-index`, `float`, `clear`
    - `::before`, `::after`, `text-overflow`, `white-space`, `-webkit-*`, `appearance`, `cursor`, `:focus-visible`, `@media`, `var(--`
    - `max-width`, `max-height`, `overflow`, `line-height` (rejected by GTK 3.24 as invalid), `transition: all` (style rule)
    - `!important` (causes GTK to discard the whole stylesheet)
    - Comma-separated `@keyframes` selectors (e.g. `0%, 24% {`; causes GTK to discard stylesheet)
    - `animation-delay` (silently ignored; timing stagger must be baked into keyframes)
    - `steps(` (unsupported in GTK3; fake via adjacent percentage keyframe stops)
    - 8-digit hex colors (`#RRGGBBAA`; fails to parse in GTK3)
    - `to top right` in gradients (fails to parse; use `to bottom right` or explicit angles)
    - Two-position gradient color stops (`$c 0 3px` form; heuristic check, fails GTK parser)
    - Any `url(` in compiled CSS (relative `url()` does not resolve in SCSS; assets must load via Yuck `image :path`).
  - Open **every defined window** in a headless Eww session with `SHIELD_FIXTURE=frozen`, assert all windows appear in `eww -c shieldOS-eww active-windows` and state populates in `eww -c shieldOS-eww state --all` (not just `ping`), and fail on any CSS or parser warnings in `eww -c shieldOS-eww logs`. Always start a fresh Eww daemon in tests, never `eww reload`; unknown-property errors and CSS parser failures only print at daemon start.
- **Gate 2 — JSON Schema Contract & Fixture Pipeline Gate (Per Ticket)**:
  - Maintain `schemas/state.schema.json` as the single source of truth for all script payloads.
  - Test that `eww.yuck` and `yuck/*.yuck` only reference fields declared in `schemas/state.schema.json`.
  - Validate `scripts/telemetry.py`, `scripts/compositor.py`, and `scripts/network-audio.py` in `--once --fixture <name>` mock mode against `schemas/state.schema.json`, including a `niri` fixture, a `hyprland` fixture, and hardware/IPC failure/fallback payloads.
- **Gate 3 — Deterministic Golden Regression & Fidelity Checklist Gate (Per Milestone)**:
  - Capture screenshots using `grim` at a fixed resolution with mock fixture data and a frozen clock (`17:32:14`, `21 NOV - 2025 FRI`).
  - Pixel-diff (`magick compare -metric AE -fuzz 2%`) only against our own approved milestone golden images (`tests/goldens/milestone-<N>.png`) for regression detection.
  - Evaluate fidelity against `reference/shield-os.png` via a structured checklist review rather than pixel diffing against the reference image.
  - Provide helper subcommands `crop <N> x,y,w,h [zoom]` for tight inspection and `measure <N> <hex>` for programmatic bounding-box and thickness assertions (used for Milestone 2 frame thickness verification).
- **Prior Art**:
  - Extends the verification patterns in `.scratch/draftpaper-eww/spec.md` and `scss-best-practices-eww`.

## Out of Scope

- Writing implementation code during this planning step.
- Custom Wayland compositor implementation (relies on existing Niri/Hyprland/Sway layer-shell).
- Reproducing AI-garbled placeholder strings verbatim where real system telemetry replaces them.

## Further Notes

- Full design token tables, typography scale, shape geometry rules, component inventory, and open questions are documented in `DESIGN.md`.
