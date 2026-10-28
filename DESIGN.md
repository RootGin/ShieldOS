# S.H.I.E.L.D. OS HUD — Design & Architecture Plan (`DESIGN.md`)

Reference mockup: `../reference/shield-os.png` (`2752×1536`, 16:9 widescreen).
User's Screen Resolution is 1920x1080.

---

## 1. Design Tokens

All hex values are sampled directly from `reference/shield-os.png` and named by semantic role.

### Backgrounds & Canvas
| Token | Hex / Value | Role |
| :--- | :--- | :--- |
| `--bg-void` | `#0A0B0F` | Deepest outer screen-edge & corner void |
| `--bg-canvas` | `#0E0F11` | Primary central HUD backdrop |
| `--bg-data-noise` | `#17181C` | Subtle vertical waveform lines & matrix grid backing |

### Steel-Grey Panel Surfaces & Borders
| Token | Hex / Value | Role |
| :--- | :--- | :--- |
| `--surface-panel` | `#2C2D2F` | Primary chamfered perimeter frame & corner plate fill |
| `--surface-panel-recessed` | `#292A2E` | Recessed frame segments & inner housing background |
| `--surface-control` | `#45464A` | Left side dock body & raised control housings |
| `--surface-pill-inactive` | `#4E4E4E` | Inactive workspace pill (`1`, `3`–`7`, `9`, `10`) & window tab fill |
| `--border-panel-outer` | `#5A5C60` | Metallic chamfered bevel highlight along panel edges |
| `--border-panel-groove` | `#18191B` | Dark inner groove line (`1px`) inside the metallic bevel |

### Gold / Amber Primary & Glow
| Token | Hex / Value | Role |
| :--- | :--- | :--- |
| `--accent-primary` | `#DBAD4D` | Central S.H.I.E.L.D. eagle crest & top-left medallion gold |
| `--accent-primary-mid` | `#C79C4E` | Lower-wing shaded gold gradient stop on central emblem |
| `--accent-primary-bright` | `#FEB703` | High-contrast amber fill on active CPU (`2`, `1.0`) & RAM (`42`) bars |
| `--accent-primary-dim` | `#5D440B` | Dark amber fill for `CPU` and `RAM` gauge header blocks |
| `--accent-primary-glow` | `rgba(219, 173, 77, 0.35)` | Outer bloom (`box-shadow` / SVG radial glow) around gold emblems |

### Orange Accents
| Token | Hex / Value | Role |
| :--- | :--- | :--- |
| `--accent-secondary` | `#C08333` | Amber-orange fill for `V0.1` badge, occupied workspace top bar, and first window tab badge |
| `--accent-secondary-bright` | `#EA972D` | Vivid orange fill for `NOV - 2025` date pill |

### Teal Active-State Colors
| Token | Hex / Value | Role |
| :--- | :--- | :--- |
| `--state-active-fill` | `#4F7E86` | Steel-teal background fill on active workspace pills (`2`, `8`) |
| `--state-active-surface` | `#0B4A5C` | Deep cyan-teal fill on active `APPLICATIONS` bottom tab and equalizer bars |
| `--state-active-border` | `#AFDBE6` | Bright ice-teal top indicator bar and active tab border glow |

### Semantic Status & Text Colors
| Token | Hex / Value | Role |
| :--- | :--- | :--- |
| `--state-danger` | `#9D000B` | Crimson alert bar above `DISCONNECTED` pill |
| `--state-danger-badge` | `#AD2927` | Red micro-badges on background window tabs (`Nebula`, `Spartan`, `Gersfit`) |
| `--text-primary` | `#FBFDFC` | Primary HUD white (clock, operator name, workspace numbers, `21`) |
| `--text-ice` | `#D0E9F0` | Cool icy-white used on the 56-star circular ring and active teal tab text |
| `--text-muted` | `#7D7D7F` | Subdued grey for secondary prefixes (`OPERATOR.`) and inactive controls |
| `--text-on-accent` | `#0E0F11` | Near-black text rendered atop bright amber/orange fills (`NOV - 2025`, `42`, `2`) |

---

## 2. Typography

### Font Roles & Free Matching Fonts
1. **HUD Condensed Display (`--font-hud`)**
   - *Visual style*: Tall, narrow, geometric uppercase sans-serif with flat vertical sides and tight character spacing (used on `17:32:14`, `V0.1`, `NFRAGMENT`, `DISCONNECTED`, bottom tabs, `CPU`/`RAM` gauges).
   - *Free matches*: **Rajdhani** (SemiBold/Bold), **Teko** (Medium/SemiBold), or **Barlow Condensed** (SemiBold/Bold).
2. **Extended Sci-Fi Display (`--font-display`)**
   - *Visual style*: Ultra-wide, heavy extended geometric numerals used for the top-right day readout (`21`).
   - *Free matches*: **Orbitron** (Black), **Michroma**, or **Syncopate** (Bold).
3. **Technical Monospace (`--font-mono`)**
   - *Visual style*: Narrow monospace used in the background telemetry/hex noise blocks and micro readouts.
   - *Free matches*: **Share Tech Mono**, **JetBrains Mono**, or **IBM Plex Mono**.

### Size Scale (1080p Base, Scaled via `dpi()`)
| Token | Size | Weight / Tracking | Usage |
| :--- | :--- | :--- | :--- |
| `--text-xs` | `9px` | `400`, `0.06em` | Background data-noise text, window tab micro-badges, sub-operator hash |
| `--text-sm` | `11px` | `600`, `0.08em` | `OPERATOR.` label, `FRI` weekday, `8G`/`UPD` window prefixes |
| `--text-md` | `13px` | `600`, `0.06em` | Bottom menu labels (`LOCALSHARE`, `POWERMENU`, `APPLICATIONS`), `DISCONNECTED`, CPU/RAM scale numbers |
| `--text-lg` | `16px` | `700`, `0.04em` | Workspace numbers (`1`–`10`), `NFRAGMENT`, `NOV - 2025`, `CPU`/`RAM` headers |
| `--text-xl` | `24px` | `700`, `0.03em` | Primary clock (`17:32:14`) and `V0.1` badge |
| `--text-display` | `42px` | `900`, `0.10em` | Top-right day number (`21`) |

---

## 3. Shape Language

- **45° Chamfered Geometry**: Zero rounded corners on panels or buttons (`border-radius: 0`), contrasted solely by true circles for the top-left S.H.I.E.L.D. medallion, the center star ring, and the two small top-left radar/target icons.
- **Corner Cut Scale**:
  - *Micro cuts (`4px–6px`)*: Workspace pills (`1`–`10`) and `NOV - 2025` badge have subtle diagonal corner clips.
  - *Trapezoid / Parallelogram slopes (`10px–16px`)*: Top window tabs (`Hydra`, `Nebula`, etc.) lean at a ~60° angle; bottom menu tabs (`POWERMENU`, `BLUETOOTH`, `APPLICATIONS`) are raised trapezoids with 45° side slopes.
  - *Structural step-chamfers (`24px–44px`)*: Corner plates step down diagonally at 45° into thin edge rails.
- **Border Widths & Bevels**:
  - Outer panel edge: `2px` solid steel highlight (`--border-panel-outer`) paired with a `1px` dark inner shadow line (`--border-panel-groove`).
  - Status top bars: Workspace pills and the `DISCONNECTED` module carry a `2px–3px` colored top accent bar (`--state-active-border`, `--accent-secondary`, or `--state-danger`).
- **Screen-Edge Frame Wrapping**:
  - The HUD forms a discontinuous perimeter frame around all four screen edges. Heavy chamfered plates anchor the four corners (`~90px` tall), stepping down via 45° angled transitions into narrow top/bottom horizontal rails (`~16px–40px`) and slim left/right vertical rails (`~12px–48px`), leaving the central workspace area unobstructed.

---

## 4. Component Inventory

| # | Component | Screen Position | Visual States | Real Data / Action Binding |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Operator Badge + Clock + Version Tag** | Top-left corner | Normal, hover, alert pulse on medallion. Includes circular gold eagle badge, `17:32:14` clock, orange `V0.1` tag, `OPERATOR. NFRAGMENT`, micro sub-line *(blurry/garbled in image)*, plus 2 circular status icons (ring & crosshair) on the outer bevel. | Clock: system time (`1s` stream via `telemetry` `deflisten`). `NFRAGMENT`: `$USER` / `whoami`. Sub-line: `uname -r` or `hostname`. `V0.1`: config version. Clicking medallion toggles system overview. |
| 2 | **Workspace Pills (`1`–`10`)** | Top bar, left-center | **Active** (`2`, `8`): teal fill (`#4F7E86`), bright cyan top bar, white text. **Occupied** (`4`, `7`): grey fill (`#4E4E4E`), orange top bar. **Empty** (`1,3,5,6,9,10`): grey fill, dark top bar. | Bound to Wayland compositor IPC (`niri` / `hyprland` / `sway` event stream). Click switches to workspace `N`; scroll cycles workspaces. |
| 3 | **Window Tabs** | Top bar, right-center (after pill `10`) | 4 angled parallelogram tabs: `8G / Hydra` (orange badge), `UPD / Nebula` (red badge), `UPD / Spartim` *(garbled "Spartan", red badge)*, `UPD / Gersfit` *(garbled text, red badge)*. Sub-badges contain blurry micro-text. | Bound to windows on the active workspace via compositor IPC. Top-left code = short app class/tag; main text = truncated window title; bottom-right badge = state/PID/urgency. Click focuses window. |
| 4 | **Date Block** | Top-right corner | Giant extended `21`, orange `NOV - 2025` pill with dark text, and `FRI` below inside a chamfered right-corner plate. | System clock/calendar (`%d`, uppercase `%b - %Y`, uppercase `%a`, via `telemetry` `deflisten`). Click toggles calendar popup. |
| 5 | **CPU / RAM Vertical Gauges** | Right edge, upper-middle | Two stacked vertical segmented ladders (`100, 80, 60, 40, 20, 0`). `CPU` shows active amber blocks at `2` (%) and `1.0` (load/GHz). `RAM` highlights the `42` (%) block in bright amber (`#FEB703`). | `deflisten` (`1s` stream, `2s` internal CPU/RAM refresh) reading `/proc/stat`, `/proc/loadavg`, and `/proc/meminfo`. Segmented rows highlight dynamically at the matching threshold bucket. |
| 6 | **Status Pill `"DISCONNECTED"` + Equalizer** | Bottom-left corner | Chamfered pill with red top alert bar (`#9D000B`), robot/drone icon, and `DISCONNECTED` text; adjacent hexagonal pod with 4 vertical cyan bars. | Left pill: `nmcli monitor` network/VPN connection status (red `DISCONNECTED` vs teal `<SSID>`/`CONNECTED`). Right pod: audio output activity (`pactl`/`cava`) or Wi-Fi signal bars; click mutes/opens network menu. |
| 7 | **Bottom Menu Tabs** | Bottom edge, center-to-right | **Left recessed strip** (icon + text): `LOCALSHARE`, `WEBSEARCH`, `COLORS`. **Right raised trapezoids**: `POWERMENU`, `BLUETOOTH`, `APPLICATIONS` (active teal `#0B4A5C` with `#AFDBE6` border). | Click actions: `LOCALSHARE` (LocalSend/share script), `WEBSEARCH` (search prompt), `COLORS` (cycle theme palette), `POWERMENU` (session power modal), `BLUETOOTH` (BT manager/popup), `APPLICATIONS` (app launcher). |
| 8 | **Left Side Panel** | Left edge, vertical middle | Chamfered vertical steel housing with a circular play (`▶`) button at top and segmented vertical slot indicators below. | Bound to MPRIS (`playerctl` play/pause + progress/volume indicator) or quick-dock window slots. |
| 9 | **Right Corner Widgets** | Lower-right edge & bottom-right corner | Vertical plate with 3 angled mini-tabs containing blurry micro-glyphs *(resembling `ω`, `90`, `ᴗ`)* above a 4-pointed star emblem in the bottom-right corner. | 3 mini-tabs: quick toggles (DND/notifications, volume %, night-light/layout). 4-pointed star: toggle HUD visibility or lock screen. |
| 10 | **Center Emblem** | Center of background canvas | Large gold S.H.I.E.L.D. eagle medallion with inner bevel shading, soft golden bloom, and an outer perimeter ring of 56 icy-white 5-pointed stars. | Rendered on the `bottom` layer-shell desktop canvas window as layered SVG artwork (radial glow, 56-star ring, and center emblem mounted via Yuck overlay). |
| 11 | **Background Data-Noise Layer** | Full background behind emblem | Vertical golden-amber waveform lines across the horizontal mid-plane, `+`/`*` reticles, and faint monospace blocks *(all background text in the mockup is garbled AI filler)*. | Static SVG/PNG background layer combined with an optional live monospace telemetry readout (`journalctl` / `top` / network stats) in the text zones. |

---

## 5. Architecture Proposal

### Recommended Stack
- **UI Runtime**: **Eww (ElKowar's Wacky Widgets)** on Wayland (`layer-shell`) inside `/home/rootgin/.config/eww/shieldOS-eww/`.
- **Styling**: **SCSS compiled to GTK3 CSS** (strictly scoped to GTK-supported properties per `scss-best-practices-eww`), paired with Yuck `image :path` widgets inside `overlay` containers for assets where SVG is required.
  - *Why Native SCSS Shapes + Yuck SVGs*: Relative `url()` in SCSS does not resolve in GTK3 CSS (it fails silently, rendering nothing while preserving background colors). All external assets must load via Yuck `image :path`. Most chamfers and bevels do not require external SVGs: GTK3 CSS natively supports 45° corner cuts via 4-quadrant clipped `linear-gradient` mixins (`octagon`, `cut2`) and zero-content border-triangle boxes (`.triangle.<corner>`), directly consuming SCSS theme tokens at compile time without needing SVG generation.
- **Data Scripts**: Event-driven Python/Bash scripts (`deflisten` for telemetry, compositor workspaces/windows, network, audio) following ADR-0001 multi-compositor auto-detection.

### Folder Structure
```text
shieldOS-eww/
├── eww.yuck                  # Shared state (defpoll/deflisten/defvar) + (include ...) list only
├── eww.scss                  # Global reset, dpi() scale import, base classes, @import list only
├── theme.scss                # Single line: @import "./themes/shield-gold.scss";
├── themes/
│   └── shield-gold.scss      # Semantic color tokens ($bg-void, $accent-primary, etc.)
├── scss/
│   ├── _scale.scss           # $scale factor + dpi() function
│   ├── _tokens.scss          # Typography & spacing scales
│   ├── background.scss       # Center emblem + data-noise canvas styles
│   ├── top-bar.scss          # Operator badge, workspaces, window tabs, date block
│   ├── side-panels.scss      # Left media/dock panel, right CPU/RAM gauges & quick tabs
│   ├── bottom-bar.scss       # Disconnected pill, equalizer, utility links, trapezoid tabs
│   └── overlays.scss         # Applications launcher, powermenu, bluetooth popups
├── yuck/
│   ├── background.yuck
│   ├── top-bar.yuck
│   ├── side-panels.yuck
│   ├── bottom-bar.yuck
│   └── overlays.yuck
├── schemas/
│   └── state.schema.json     # Canonical JSON Schema for all script payloads
├── scripts/
│   ├── compositor.py         # deflisten: workspaces 1-10 + active window tabs (Niri/Hyprland/Sway + --fixture)
│   ├── telemetry.py          # deflisten: CPU %, CPU load, RAM %, date/time (+ --fixture / frozen clock)
│   ├── network-audio.py      # deflisten: connectivity state + 4-bar equalizer/audio state (+ --fixture)
│   └── theme-gen.py          # Injects active theme hex tokens into SVG templates
├── docs/
│   └── eww-geometry.md       # Geometry reference & token mapping
├── tests/
│   ├── check-gate1-gtk.sh    # CSS denylist lint + headless eww open-all, active-windows, state & log check
│   ├── check-gate2-schema.py # Validates yuck field refs + script outputs (niri, hyprland, fallback fixtures) vs schema
│   ├── check-gate3-golden.sh # Fixed-res frozen-clock grim capture + golden regression diff
│   ├── check-yuck-triangles.py # Yuck triangle geometry & overlay constraints validator
│   ├── fixtures/             # niri, hyprland, and hardware/IPC failure fallback fixtures
│   └── goldens/              # Approved milestone golden screenshots for regression diffing
├── bin/
│   └── shield-ctl            # CLI entrypoint for keybinds & tab actions
└── assets/
    ├── templates/            # Token-free SVG templates
    ├── star-ring.svg         # 56-star perimeter ring SVG
    ├── glow.svg              # Radial glow backdrop SVG
    ├── placeholder.svg       # Neutral center emblem placeholder SVG
    ├── data-noise.svg        # Waveform lines & reticle grid
    └── panels/               # Parameterized SVG frames for corner plates only
```

### Component Geometry & Styling Techniques

| Component | Technique | Notes |
|---|---|---|
| Workspace pills, date pill, small plates (4-6px cuts) | four-corner octagon mixin | opaque colors only (no rgba); never set background-color on the same element |
| Frame bevels (#5A5C60 edge, #18191B groove) | nested octagons | measure the diagonal band thickness; spike before committing |
| Window tabs, bottom trapezoid tabs (slants, variable width) | fixed-size slant caps + stretchy body box | paint in the tab's own color (additive); a $xbg mask is not a real cut and shows over the noise |
| Frame corner plates (24-44px step-chamfers) | SVG via `image :path`, or stacked boxes | spike one corner both ways in Milestone 2 |
| Emblem, 56-star ring, data noise, glow | SVG via `image :path` | the glow rgba token belongs here |

### How Components Share Theme Tokens & Tradeoffs
- **Single Source of Truth**: Color tokens live in `themes/<name>.scss`. Because relative `url()` in SCSS does not resolve, assets load via yuck `image :path` inside an `overlay`. `scripts/theme-gen.py` generates and recolors the layered SVGs (`glow.svg`, `star-ring.svg`, `placeholder.svg`, `data-noise.svg`, corner plates); SCSS-only shapes take colors directly from theme tokens at compile time.
- **Tradeoffs**:
  - *Eww Native CSS Chamfers + Yuck SVGs (Recommended)*: Lightweight (~25 MB RAM), zero Qt6 overhead. Uses pure GTK3 CSS gradients and border-triangles for cards and tabs with direct token binding, reserving SVG plates for intricate multi-color center graphics and complex corner plates.
  - *Quickshell / AGS alternative*: Supports native canvas/clip-path drawing in QML/GTK4, but adds heavy runtime dependencies and diverges from this repository's established Eww architecture.

---

## 6. Testing Gates & Verification Cadence

- **Execution Cadence**: Run **Gates 1 + 2 on every ticket**; run **Gate 3 at every milestone boundary**.

1. **Gate 1 — GTK3 CSS Denylist & Headless Eww Runtime Check (Per Ticket)**
   - **Static Denylist Lint**: Compile SCSS (`sass --no-source-map --silence-deprecation=import,global-builtin shieldOS-eww/eww.scss /tmp/shield.css`) and fail if any denylisted CSS property or syntax appears:
     - Layout & positioning: `display: flex`, `justify-content`, `align-items`, `flex-direction`, `position`, `z-index`, `float`, `clear`.
     - Pseudo-elements / text / appearance: `::before`, `::after`, `text-overflow`, `white-space`, `-webkit-*`, `appearance`, `cursor`, `:focus-visible`, `@media`, `var(--`.
     - Sizing & overflows: `max-width`, `max-height`, `overflow`.
     - Deprecated or invalid GTK properties: `line-height` (rejected by GTK 3.24 as an invalid property), `transition: all` (accepted by GTK3 but denylisted as a style rule).
     - Geometry, parser & rule additions (Ticket 3b):
       - `!important` (unsupported by GTK3 CSS; causes GTK to discard the entire compiled stylesheet).
       - Comma-separated `@keyframes` selectors (e.g. `0%, 24% {`; causes GTK to discard the whole stylesheet).
       - `animation-delay` (silently ignored by GTK3; timing stagger must be baked directly into keyframes).
       - `steps(` (unsupported in GTK3; fake via adjacent percentage keyframe stops).
       - 8-digit hex colors (`#RRGGBBAA`; fails to parse in GTK3 gradients/properties).
       - `to top right` in gradients (fails to parse in GTK3; use `to bottom right` or explicit angles).
       - Two-position gradient color stops (`$c 0 3px` form; heuristic check, fails GTK parser; use explicit stops `$c 0, $c 3px`).
       - Any `url(` in compiled CSS (relative `url()` does not resolve in SCSS; assets must load via Yuck `image :path`).
     - Verified against core geometry techniques: 4-quadrant linear gradients from `@mixin octagon` and `@mixin cut2` cleanly pass all 30 denylist patterns while two-position color stops are strictly caught.
   - **Yuck Triangle Geometry Lint**: AST parser (`tests/check-yuck-triangles.py`) validating all `.yuck` files to enforce that border-only triangle widgets (`.triangle`, `.trianglesub`) never declare explicit `:width` or `:height` (which turns borders into trapezoids); includes built-in negative test asserting rejection of dimensioned triangles.
   - **Headless Runtime Verification**: Start Eww in a headless session with `SHIELD_FIXTURE=frozen`, open every defined window (`eww -c shieldOS-eww open-many ...`), assert all expected windows are listed in `eww -c shieldOS-eww active-windows` and variables are populated in `eww -c shieldOS-eww state --all` (not just `eww ping`), and fail on any CSS or parser warnings in `eww -c shieldOS-eww logs`. Always start a fresh Eww daemon in tests, never `eww reload`; unknown-property errors and CSS parser failures only print at daemon start.
2. **Gate 2 — JSON Schema Contract & Fixture Pipeline Check (Per Ticket)**
   - **Contract Source of Truth**: `schemas/state.schema.json` defines the exact schema for `telemetry`, `compositor`, and `network_audio` payloads.
   - **Yuck Field Reference Check**: Static test verifying that `eww.yuck` and `yuck/*.yuck` only access JSON properties declared in `schemas/state.schema.json`.
   - **Fixture & Fallback Validation**: Run all data scripts in `--once --fixture <name>` mock mode and validate stdout against `schemas/state.schema.json`, covering:
     - `niri` compositor fixture
     - `hyprland` compositor fixture
     - Failure/fallback fixtures (missing sysfs battery/thermals, absent compositor IPC, disconnected network/audio).
3. **Gate 3 — Deterministic `grim` Golden Regression & Fidelity Checklist (Per Milestone)**
   - **Deterministic Capture**: Render in a fixed-resolution headless Wayland output with mock fixture data and a frozen clock/date (`17:32:14`, `21 NOV - 2025 FRI`), capturing the screen via `grim`.
   - **Golden Regression Diff**: Pixel-diff (`magick compare -metric AE -fuzz 2%`) only against our own approved milestone golden images (`tests/goldens/milestone-<N>.png`) to catch regressions. Tolerance policy: a `-fuzz 2%` color margin failing if differing pixels exceed 0.1% of the image surface area (up to 2,073 pixels on 1920x1080) accommodates minor antialiasing and subpixel rasterization variations across GPU/CPU rendering backends while catching any visible layout shift, color mistake, or missing element.
   - **Reference Fidelity Review**: Compare against `reference/shield-os.png` using a structured visual checklist (colors, typography, chamfered geometry, placement, states) rather than a pixel diff against the mockup.

---

## 7. Build Order (Staged Milestones)

Each milestone closes with **Gate 3** (`grim` capture with frozen clock/mock data, checklist review against `reference/shield-os.png`, and golden image approval). Every ticket within a milestone runs **Gates 1 + 2**.

1. **Milestone 1 — Scaffold, Contracts, Tokens & Background Canvas**
   - Set up `shieldOS-eww/` layout, `schemas/state.schema.json`, Gate 1+2 test runners, `themes/shield-gold.scss`, `dpi()` scaling, and the `bottom`-layer background window with the dark void canvas, data-noise waveform lines, and central S.H.I.E.L.D. eagle + 56-star ring SVG.
   - *Done when*: Gates 1+2 pass and `grim` capture of `background` passes the checklist for the centered gold eagle emblem with outer glow, 56-star ring, and vertical waveform background.
2. **Milestone 2 — Perimeter Chamfered Frame & Corner Plates**
   - Build the static steel-grey chamfered perimeter bevels (top, bottom, left, right rails and 4 corner housings) with the bottom-right 4-pointed star emblem.
   - *Done when*: All four screen edges show continuous chamfered steel-grey framing with `#5A5C60` highlights and `#18191B` inner grooves without blocking the center canvas, verified with `measure`-based assertions (`tests/check-gate3-golden.sh measure 2 <hex>`) asserting frame thickness and bevel dimensions (e.g. `#5A5C60` bevel highlight thickness and `#18191B` inner groove bounds).
3. **Milestone 3 — Top-Left Operator Module & Top-Right Date Block**
   - Implement the circular gold S.H.I.E.L.D. badge, live/frozen `HH:MM:SS` clock, orange `V0.1` box, `OPERATOR. <USER>` readout, two circular radar/target icons, and the top-right `21 / NOV - 2025 / FRI` date block.
   - *Done when*: Frozen-clock fixture renders `17:32:14` and `21 / NOV - 2025 / FRI` matching the reference checklist, and live polling updates clock and calendar.
4. **Milestone 4 — Workspace Pills (`1`–`10`) & Angled Window Tabs**
   - Wire `scripts/compositor.py` (`deflisten` + `niri`/`hyprland`/fallback fixtures) to render workspace pills `1`–`10` (empty, occupied-orange, active-teal states) and up to 4 angled window tabs with app tags and status badges.
   - *Done when*: Both `niri` and `hyprland` fixtures pass Gate 2, active workspaces render `#4F7E86` fill with `#AFDBE6` top bar, clicking pills dispatches workspace switches, and angled window tabs populate cleanly.
5. **Milestone 5 — Right-Edge CPU / RAM Vertical Gauges & Lower Quick Tabs**
   - Implement the stacked `CPU` and `RAM` vertical ladder gauges (`100` down to `0`) with dynamic bright-amber (`#FEB703`) active threshold blocks, plus the 3 lower-right angled quick-toggle tabs.
   - *Done when*: Mock telemetry fixture (`CPU=2 / 1.0`, `RAM=42`) illuminates the exact vertical steps in `#FEB703` with `#0E0F11` text.
6. **Milestone 6 — Left Side Panel & Bottom-Left Connectivity / Equalizer**
   - Build the left vertical chamfered dock (with top `▶` media trigger and slot bars) and the bottom-left `DISCONNECTED`/network status pill + 4-bar hexagonal equalizer pod.
   - *Done when*: Disconnected and connected fixtures toggle the bottom-left pill between red `#9D000B` `DISCONNECTED` and teal connected state, and audio/media fixtures update the left panel and 4-bar pod.
7. **Milestone 7 — Bottom Menu Strip & Interactive Overlays**
   - Build the bottom utility links (`LOCALSHARE`, `WEBSEARCH`, `COLORS`) and raised trapezoid tabs (`POWERMENU`, `BLUETOOTH`, `APPLICATIONS`), plus toggleable HUD overlays for Applications, Powermenu, and Theme cycling.
   - *Done when*: Clicking `APPLICATIONS` highlights the tab in `#0B4A5C` with `#AFDBE6` border and opens the S.H.I.E.L.D.-styled launcher overlay; clicking `COLORS` rotates the HUD theme across SCSS and SVG plates.

---

### Resolved: Window Management Reserve Space (was Open Question 6)

Decision: the HUD reserves screen space. Tiled windows sit inside the frame
and are never drawn under interactive HUD elements.

- **Top bar window** (operator module, workspaces, window tabs, date block):
  layer-shell, anchored top, full width, `:exclusive true`. Exclusive zone
  equals the full top bar height, so the 90px corner plates are inside it.
- **Bottom bar window** (connectivity pod, utility links, trapezoid tabs):
  anchored bottom, full width, `:exclusive true`, same rule.
- **Left and right side windows** (left dock, CPU/RAM gauges, quick tabs):
  anchored to their edge, NOT exclusive. Compositor gaps/struts keep tiled
  windows clear of them (niri: `struts`/`gaps`; hyprland: `general:gaps_out`;
  sway: `gaps outer`). Gap width = widest side element, set in one place.
- **Background canvas window**: `bottom` layer, fullscreen, not exclusive,
  not focusable.
- All HUD windows: `:focusable false` so they never steal keyboard focus.

Consequence: 5 windows total (top, bottom, left, right, background).
Milestone 2 builds the frame as pieces of these windows, not one fullscreen
overlay.

## 8. Open Questions (Ambiguities in Reference Image)

1. **Garbled Window Tab Sub-Badges & Labels**: The four top window tabs (`8G Hydra`, `UPD Nebula`, `UPD Spartim`, `UPD Gersfit`) have tiny orange/red bottom-right badges with unreadable AI-garbled text. Should these tabs represent **open windows on the current workspace** (prefix = app category/tag, title = window title, bottom-right badge = workspace/PID/status), or **pinned system services/containers**?
2. **Dual Teal Workspaces (`2` and `8`)**: Both workspace `2` and `8` are highlighted in teal (`#4F7E86`), while `4` and `7` have thin orange top bars. Should teal represent **focused workspace on primary + secondary monitor** (with orange top bar = occupied unfocused), or a different state model?
3. **Left Side Panel Function**: The left vertical panel has a `▶` icon at the top and vertical segmented slots below, with no text labels. Should we bind this to **MPRIS media controls + volume/progress**, or **minimized/parked window slots**?
4. **Three Lower-Right Mini-Tabs**: The three small angled tabs on the lower-right frame contain blurry symbols (`ω`, `90`, `ᴗ`). What three quick actions or readouts would you like bound there (e.g., Volume %, Do-Not-Disturb, Keyboard Layout / Night Light)?
5. **Background Data-Noise Text**: The small monospace blocks in the background canvas are illegible AI placeholder text. Should they remain **static decorative texture**, or should we populate them with **live system logs / process telemetry** (`journalctl`, `uname`, top processes)?
