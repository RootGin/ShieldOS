# Coding Standards (`shieldOS-eww`)

## Eww Geometry & Layout Rules

1. **Read docs/eww-geometry.md before any chamfered/angled component**: Consult `docs/eww-geometry.md` before writing or modifying any chamfered, angled, or polygon widget.
2. **Pin explicit `:width`/`:height` on every overlay layer**: An `overlay` stretches its first child and positions subsequent children at natural size; always pin `:width` and `:height` on all layers to prevent alignment drift and seams.
3. **Understand overlay constraints**: An `overlay` stretches its first child, ignores its own margin, paints no background, and has no properties.
4. **Put a label inside its box, not as a sibling overlay child**: Sibling overlay children collapse container `min-height`/`min-width`; place labels inside the child box container.
5. **Never set `:width`/`:height` on a border-only triangle**: Setting dimensions on a `.triangle` turns the border into a trapezoid. Let border widths alone size the triangle.
6. **`min-width` is content-box**: Rendered width = `min-width` + padding + border; subtract horizontal padding and border when matching target pixel dimensions.
7. **Measure rendered pixels before tuning any offset**: Use `tests/check-seam3-golden.sh measure` and `crop` to verify exact rendered pixel boundaries rather than guessing offsets.
