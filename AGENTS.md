# Agent Rules (`shieldOS-eww`)

1. **Use theme tokens only**: Never hardcode hex or RGB color literals in `.scss` or `.yuck` files; reference semantic variables from `themes/` via `theme.scss`.
2. **One component per file**: Maintain a strict 1:1 module boundary with one `yuck/<module>.yuck` and one `scss/<module>.scss` per component; keep root `eww.yuck` and `eww.scss` limited to shared state, tokens, resets, base classes, and imports/includes.
3. **No new dependencies without asking**: Use only the tools pinned in the Nix devShell (`eww`, `sass`, `sway`, `grim`, `imagemagick`, `python3` with `jsonschema`). Do not add packages or runtime dependencies without explicit user approval.
4. **GTK3-safe CSS only**: Emit only CSS properties supported by GTK3's CSS engine. Never emit CSS custom properties (`--*` / `var(...)`), flexbox/grid layout rules, `position`, `z-index`, `max-width`/`max-height`, `overflow`, `line-height`, pseudo-elements (`::before`/`::after`), or `transition: all` (enforced as a style rule even though GTK3 accepts it).
5. **Never claim a test passes without running it**: Always execute the test suite (`tests/check-seam1-gtk.sh`, etc.) and verify its exit code and output before reporting completion.
