# Milestone Verification Checklist: Milestone 5

Reference Image: `reference/shield-os.png`
Capture Path: `tests/captures/milestone-5.png`
Side-by-Side Path: `tests/captures/compare-5.png`

## Automated Regression
- [x] `tests/run-ticket.sh` (Gates 1 & 2) passes with exit code 0
- [x] `tests/check-gate3-golden.sh check 5` passes against approved golden

## Programmatic Geometry & Color Assertions (`measure`)
- [x] Outer bevel highlight `#5A5C60` thickness assertions pass: `1920x1080 +0+0` (`tests/check-gate3-golden.sh measure 5 '#5A5C60'`)
- [x] Inner groove `#18191B` dimension assertions pass: `1914x1074 +3+3` (`tests/check-gate3-golden.sh measure 5 '#18191B'`)
- [x] Dual active teal workspace fill `#4F7E86` bounds pass: `352x36 +719+36` (`tests/check-gate3-golden.sh measure 5 '#4F7E86'`)
- [x] Dual active cyan indicator top bar `#AFDBE6` bounds pass: `356x40 +717+34` (`tests/check-gate3-golden.sh measure 5 '#AFDBE6'`)
- [x] Urgent alert node status badges `#AD2927` bounds pass: `258x6 +1393+75` (`tests/check-gate3-golden.sh measure 5 '#AD2927'`)
- [x] Dynamic CPU & RAM active gauge highlight blocks in bright amber `#FEB703` bounds pass: `50x377 +1859+274` (`tests/check-gate3-golden.sh measure 5 '#FEB703'`)
- [x] Gauge headers (CPU and RAM) in dark amber `#5D440B` bounds pass: `48x221 +1859+274` (`tests/check-gate3-golden.sh measure 5 '#5D440B'`)

## Visual Fidelity Review (Milestone 5)
- [x] CPU ladder gauge: Vertical segmented ladder (100, 80, 60, 40, active 2 / 1.0 load) positioned on the upper-right rail deck with yellow rail track line along right margin
- [x] CPU ladder header: Dark amber header block `#5D440B` with bold white text `CPU`
- [x] CPU ladder active cell: Highlights 2% and 1.0 load in bright amber `#FEB703` with dark text `#0E0F11`
- [x] RAM ladder gauge: Vertical segmented ladder (100, 80, active 42, 40, 20, 0) positioned below CPU ladder with matching track border
- [x] RAM ladder header: Dark amber header block `#5D440B` with bold white text `RAM`
- [x] RAM ladder active cell: Highlights 42% bucket in bright amber `#FEB703` with dark text `#0E0F11`
- [x] Lower-right quick-toggle cluster: 3 angled mini-tabs (`E`, `50`, `L`) docked in the lower-right bezel housing above the 4-pointed star corner plate
- [x] Mini-tab geometry: 45° chamfered lower-left cut, rounded top-right corner, and cyan pip indicator bar
- [x] Volume cluster interaction: Click toggle/down handlers and scroll up/down handlers on volume level tab with CSS hover highlights
- [x] Telemetry contract: Dynamic buckets conform to schema (#/$defs/telemetry) with boundary checks passing at 0%, 19%, 20%, 100%

## Approval Decision
- [x] Approved for golden promotion: `tests/check-gate3-golden.sh approve 5 --yes`
