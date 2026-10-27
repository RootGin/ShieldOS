# Agent Rules (`shieldOS-eww`)

Run all commands inside `nix develop` (or `nix develop --command <cmd>`).

1. **Use theme tokens only**: Never hardcode hex or RGB color literals in `.scss` or `.yuck` files; reference semantic variables from `themes/` via `theme.scss`.
2. **One component per file**: Maintain a strict 1:1 module boundary with one `yuck/<module>.yuck` and one `scss/<module>.scss` per component; keep root `eww.yuck` and `eww.scss` limited to shared state, tokens, resets, base classes, and imports/includes.
3. **No new dependencies without asking**: Use only the tools pinned in the Nix devShell (`eww`, `sass`, `sway`, `grim`, `imagemagick`, `python3` with `jsonschema`). Do not add packages or runtime dependencies without explicit user approval.
4. **GTK3-safe CSS only**: Emit only CSS properties supported by GTK3's CSS engine. Never emit:
   - CSS custom properties (`--*` / `var(...)`), flexbox/grid layout rules, `position`, `z-index`, `max-width`/`max-height`, `overflow`, `line-height`, pseudo-elements (`::before`/`::after`), or `transition: all` (style rule).
   - `!important` (unsupported by GTK3; causes stylesheet discard).
   - Comma-separated `@keyframes` selectors (e.g. `0%, 24% {`).
   - `animation-delay` (silently ignored; bake timing into keyframe percentages).
   - `steps(` (unsupported; use adjacent percentage stops).
   - 8-digit hex colors (`#RRGGBBAA`).
   - `to top right` in gradients (use `to bottom right` or explicit angles).
   - Two-position gradient color stops (`$c 0 3px`).
   - Any `url()` in compiled CSS (relative `url()` does not resolve in SCSS; load assets via Yuck `image :path`).
5. **Never claim a test passes without running it**: Always execute the test suite (`tests/check-seam1-gtk.sh`, etc.) and verify its exit code and output before reporting completion.
6. **Every ticket must end with tests/run-ticket.sh passing**: Execute `tests/run-ticket.sh` (which runs Seam 1 then Seam 2) and verify its exit code is 0 before completing any ticket.
7. **Geometry & layout standards**: Consult `docs/eww-geometry.md` before writing or modifying any chamfered, angled, or polygon widget; see `CODING_STANDARDS.md` for geometry rules and layout constraints.
