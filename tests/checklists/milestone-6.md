# Milestone Verification Checklist: Milestone 6

Reference Image: `reference/shield-os.png`
Capture Path: `tests/captures/milestone-6.png`
Side-by-Side Path: `tests/captures/compare-6.png`

## Automated Regression
- [x] `tests/run-ticket.sh` (Gates 1 & 2) passes with exit code 0
- [x] `tests/check-gate3-golden.sh check 6` passes against approved golden

## Programmatic Geometry & Color Assertions (`measure`)
- [x] Outer bevel highlight `#5A5C60` thickness assertions pass: `1920x1080 +0+0` (`tests/check-gate3-golden.sh measure 6 '#5A5C60'`)
- [x] Inner groove `#18191B` dimension assertions pass: `1914x1075 +3+3` (`tests/check-gate3-golden.sh measure 6 '#18191B'`)
- [x] Steel-grey control surface `#45464A` (left dock housing & right volume tabs) bounds pass: `1910x1049 +2+8` (`tests/check-gate3-golden.sh measure 6 '#45464A'`)
- [x] Recessed panel surface `#292A2E` (status pill body & play trigger interior) bounds pass: `1916x1077 +2+2` (`tests/check-gate3-golden.sh measure 6 '#292A2E'`)
- [x] Disconnected alert indicator `#AD2927` bounds pass: `1506x957 +145+75` (`tests/check-gate3-golden.sh measure 6 '#AD2927'`)
- [x] Dynamic CPU & RAM active gauge highlight blocks in bright amber `#FEB703` bounds pass: `50x377 +1870+274` (`tests/check-gate3-golden.sh measure 6 '#FEB703'`)
- [x] Gauge headers (CPU and RAM) in dark amber `#5D440B` bounds pass: `48x221 +1870+274` (`tests/check-gate3-golden.sh measure 6 '#5D440B'`)

## Visual Fidelity Review (Milestone 6)
- [x] Bridge Control Dock: Chamfered vertical dock housing styled in steel-grey $surface-control (#45464A) with 58px chamfer cut at 45°
- [x] Radar reticle: Concentric cyan/ice-white radar rings with outer bracket and ice-blue glow wired to `bin/shield-ctl bridge-toggle`
- [x] Vertical typography: Dual columns with :angle 270 rendering bold BRIDGE CONTROL and muted SHIELD OS / SUB-SEC 4
- [x] Status badge & pips: Chamfered STATUS badge and dual status indicator pips reflecting compositor session readiness
- [x] Left rail docking: Perimeter vertical rail (12px width, 484px height) docked below chamfered housing with 20px gap
- [x] Bottom-left status pill: Stepped tab indicator in crimson `#AD2927` showing `DISCONNECTED` with recessed inner groove hairline and notch serrations
- [x] Bottom-left equalizer pod: Recessed pod housing 4 vertical equalizer bars bound to audio levels
- [x] Non-exclusive windowing: Left panel window declares `:exclusive false` leaving central workspace clear

## Approval Decision
- [x] Approved for golden promotion: `tests/check-gate3-golden.sh approve 6 --yes`
