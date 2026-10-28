# Milestone Verification Checklist: Milestone 2

Reference Image: `reference/shield-os.png`
Capture Path: `tests/captures/milestone-2.png`
Side-by-Side Path: `tests/captures/compare-2.png`

## Automated Regression
- [ ] `tests/run-ticket.sh` (Gates 1 & 2) passes with exit code 0
- [ ] `tests/check-gate3-golden.sh check 2` passes against approved golden

## Programmatic Geometry & Thickness Assertions (`measure`)
- [ ] Outer bevel highlight `#5A5C60` thickness assertions pass (`tests/check-gate3-golden.sh measure 2 '#5A5C60'`)
- [ ] Inner groove `#18191B` dimension assertions pass (`tests/check-gate3-golden.sh measure 2 '#18191B'`)
- [ ] Steel-grey panel perimeter bounds `#2C2D2F` wrap all four screen edges (`tests/check-gate3-golden.sh measure 2 '#2C2D2F'`)

## Visual Fidelity Review (Milestone 2)
- [ ] Continuous chamfered steel-grey framing across top, bottom, left, and right screen rails
- [ ] Chamfered corner housings with 45° step cuts without blocking center canvas
- [ ] Bevel highlight (`$border-panel-outer` `#5A5C60`) and inner groove (`$border-panel-groove` `#18191B`)
- [ ] Bottom-right 4-pointed star emblem in corner bezel

## Approval Decision
- [ ] Approved for golden promotion: `tests/check-gate3-golden.sh approve 2 --yes`
