# S.H.I.E.L.D. OS HUD

A tactical aerospace HUD shell for Wayland desktop environments, built with [Eww](https://github.com/elkowar/eww).

## Quick Start

Start or stop the HUD using the provided control scripts:

```bash
# Launch the HUD
./autostart.sh

# Terminate the HUD and cleanup
./terminate.sh
```

## Development

The project provides a pinned Nix development shell with all required dependencies (`eww`, `dart-sass`, fonts, Wayland tools, etc.).

```bash
# Enter development shell
nix develop

# Or run tests directly
nix develop --command tests/run-ticket.sh
```

## Project Structure

- `yuck/` — Eww widget and window definitions.
- `scss/` — GTK3 styling and theme SCSS rules.
- `scripts/` — Telemetry, compositor integration, and system monitors.
- `bin/` — CLI helpers (`shield-ctl`, `shield-open`).
- `themes/` — Color palettes and tactical SVG assets.
- `layout.json` — Governed layout dimensions and window geometry.
