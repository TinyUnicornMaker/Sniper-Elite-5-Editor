# Sniper Elite 5 Editor

A desktop application for editing weapon, scope, and attachment stats in
Sniper Elite 5 ASR/ASRpatch files.

Built with Python and PySide6 (Qt). Runs on Linux and Windows.

## Features

- **Weapon Editor** — Edit damage, recoil, fire rate, effective range,
  muzzle velocity, sway, and more for all primary/secondary weapons
- **Scope Editor** — Adjust zoom levels, scope-in speed, aim stability,
  and sway for all 14 scopes
- **Attachment Editors** — Edit barrels, magazines, suppressors,
  ironsights, chokes, and stocks/grips with the same stat controls
- **Ammo & Damage Editor** — Dynamically lists every entity with a
  Damage property; edit damage, ballistics, and stealth stats
- **Display Names** — Combo boxes show in-game names
  (e.g. "Karabiner 98") instead of internal entity names (e.g. "Kar98K")
- **Preset System** — Apply "Extended Strengths & Weaknesses" to all
  weapons at once, or reset everything to defaults
- **Safety** — Automatic `.bak` backup on first file open; restore from
  backup at any time
- **Warning Indicators** — Green/yellow/red color coding shows how far
  each value deviates from the original

## Quick Start

### Prerequisites

- Python 3.10+
- PySide6

### Install

```bash
git clone https://github.com/YOUR_USERNAME/Sniper-Elite-5-Editor.git
cd Sniper-Elite-5-Editor
pip install -r requirements.txt
```

### Run

```bash
python se5editor.py
```

### Which file to open

The editor works with:

```
Sniper Elite 5/misc/common.asr.asrpatch
```

This single file contains all weapon, scope, and attachment stats.

## Project Structure

| File | Description |
|------|-------------|
| `se5editor.py` | Application entry point (PySide6 launcher) |
| `asr.py` | ASR/ASRpatch file parser and writer (AsuraZlb format) |
| `gui/main_window.py` | Main window with tabbed interface |
| `gui/weapon_editor.py` | Weapon stats editor panel |
| `gui/scope_editor.py` | Scope zoom and aim editor panel |
| `gui/attachment_editor.py` | Generic attachment editor (barrels, magazines, etc.) |
| `gui/ammo_editor.py` | Ammo & damage editor (all entities with Damage) |
| `gui/display_names.py` | Internal entity name → in-game display name mapping |
| `gui/theme.py` | Military olive/amber Qt stylesheet |
| `gui/presets.py` | Preset definitions and application logic |
| `assets/icons/` | Application icons (16–256px) |

## Building a Binary (Windows and Linux)

A PyInstaller spec file and GitHub Actions workflow are included for
building standalone Windows and Linux binaries.

### Local build (Windows)

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
pyinstaller se5editor.spec
```

The executable will be in `dist/SniperElite5Editor/SniperElite5Editor.exe`.

### Local build (Linux)

```bash
# Install system dependencies for PySide6/Qt
sudo apt-get install -y libgl1 libegl1 libxkbcommon0 libdbus-1-3 \
  libfontconfig1 libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
  libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
  libxcb-shape0 libxcb-sync1 libxcb-util1 libxcb-xfixes0 libxfixes3 \
  libxrandr2 libxrender1 libasound2 libpulse0

# Install Python dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Build
pyinstaller se5editor.spec

# Zip the output
cd dist && zip -r SniperElite5Editor-linux.zip SniperElite5Editor
```

The executable will be in `dist/SniperElite5Editor/SniperElite5Editor`.

### GitHub Actions

Push a tag (e.g. `v1.0.0`) to trigger the build workflow, which
produces downloadable Windows (`.zip`) and Linux (`.zip`) binary
artifacts and creates a GitHub Release.

## ASR File Format

The game uses AsuraZlb containers:

- 8-byte magic (`AsuraZlb`)
- 4-byte flags, 4-byte compressed size, 4-byte uncompressed size
- zlib-compressed body (wbits=13)

Properties are 12-byte tuples: `[type:4][value:4][hash:4]`

- Type 0 = int32
- Type 1 = float32
- Type 4 = string

## Warnings

- **Restart the game** after saving `.asrpatch` changes — the game
  loads weapon data at startup
- Changing RPM can cause reload animation pauses
- High recoil values (>3.0) can cause long delays between shots
- Changing magazine capacity can cause reload animation issues
- Some scope entities pick up properties from neighboring weapon
  entities (known limitation)
- Always keep the `.bak` backup so you can restore original stats
