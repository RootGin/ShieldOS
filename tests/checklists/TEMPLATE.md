# Milestone Verification Checklist: Milestone <N>

Reference Image: `reference/shield-os.png`
Capture Path: `tests/captures/milestone-<N>.png`
Side-by-Side Path: `tests/captures/compare-<N>.png`

## Automated Regression
- [ ] `tests/run-ticket.sh` (Gates 1 & 2) passes with exit code 0
- [ ] `tests/check-gate3-golden.sh check <N>` passes against approved golden

## Programmatic Geometry & Thickness Assertions (`measure`)
- [ ] Geometry/thickness assertions pass (`tests/check-gate3-golden.sh measure <N> '<hex>'`)

## Visual Fidelity Review
- [ ] Visual fidelity item 1
- [ ] Visual fidelity item 2
- [ ] Visual fidelity item 3

## Approval Decision
- [ ] Approved for golden promotion: `tests/check-gate3-golden.sh approve <N> --yes`
