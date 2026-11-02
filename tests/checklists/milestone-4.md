# Milestone Verification Checklist: Milestone 4

Reference Image: `reference/shield-os.png`
Capture Path: `tests/captures/milestone-4.png`
Side-by-Side Path: `tests/captures/compare-4.png`

## Automated Regression
- [x] `tests/run-ticket.sh` (Gates 1 & 2) passes with exit code 0
- [x] `tests/check-gate3-golden.sh check 4` passes against approved golden

## Programmatic Geometry & Color Assertions (`measure`)
- [x] Outer bevel highlight `#5A5C60` thickness assertions pass: `1920x1080 +0+0` (`tests/check-gate3-golden.sh measure 4 '#5A5C60'`)
- [x] Inner groove `#18191B` dimension assertions pass: `1914x1074 +3+3` (`tests/check-gate3-golden.sh measure 4 '#18191B'`)
- [x] Dual active teal workspace fill `#4F7E86` (workspaces 2 and 8) bounds pass: `352x36 +719+36` (`tests/check-gate3-golden.sh measure 4 '#4F7E86'`)
- [x] Dual active cyan indicator top bar `#AFDBE6` (workspaces 2 and 8) bounds pass: `356x40 +717+34` (`tests/check-gate3-golden.sh measure 4 '#AFDBE6'`)
- [x] Urgent alert node status badges `#AD2927` (Nebula, Spartim, Gersfit) bounds pass: `258x6 +1393+75` (`tests/check-gate3-golden.sh measure 4 '#AD2927'`)
- [x] Amber-orange status elements `#EA972D` (occupied top bars, 8G Hydra badge, date pill) bounds pass: `1058x45 +815+36` (`tests/check-gate3-golden.sh measure 4 '#EA972D'`)

## Visual Fidelity Review (Milestone 4)
- [x] Workspaces 1–10 render 4-corner micro-chamfers with distinct states: active teal fill `#4F7E86` on 2 & 8, occupied amber-orange indicator `#EA972D` on 4 & 7, and empty inactive grey on 1, 3, 5, 6, 9, 10
- [x] Workspaces 1–10 interaction: click switches workspace via `bin/shield-ctl workspace N`; scroll cycles next/previous
- [x] Window tabs: 4 stepped HUD polygon pills (`8G Hydra`, `UPD Nebula`, `UPD Spartim`, `UPD Gersfit`) positioned cleanly on the top rail deck to the right of workspace 10
- [x] Window tabs: anchor prefix `F:`, top-left rivet notch, stepped upper plateau, contour hairline, and docked parallelogram micro-badges matching reference layout
- [x] Node tags & titles: HUD typography (`$font-hud-condensed`) with prominent bold tags (`8G`, `UPD`) and node names (`Hydra`, `Nebula`, `Spartim`, `Gersfit`)
- [x] Micro-badges: Amber-orange badge (`0-0-NE-01`) on Hydra; alert red badges (`SSWS`, `3C2E-0010`, `SCOREN`) on Nebula, Spartim, and Gersfit
- [x] Stepped status hairlines running flush through tabs to connect with docked badges
- [x] Window tab interaction: click dispatches `bin/shield-ctl focus <id>` to focus the node slot

## Approval Decision
- [x] Approved for golden promotion: `tests/check-gate3-golden.sh approve 4 --yes`
