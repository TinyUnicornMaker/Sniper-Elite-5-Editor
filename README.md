# Sniper Elite 5 Editor

A desktop application for editing weapon and attachment stats in
Sniper Elite 5 ASR/ASRpatch files.

Built with Python and PySide6 (Qt). Runs on Linux and Windows.

## Features

### Weapon Browser

The main panel is a split view: a **category sidebar** on the left and
a **tabbed detail view** on the right.

**Sidebar** — Weapons are grouped into five categories that mirror the
in-game gunsmith:

- Primary Rifles
- Shotguns
- Pistols
- SMGs
- Special Weapons

Each category header shows the weapon count (e.g. "Primary Rifles · 15").
Weapons are listed under their category using in-game display names
(e.g. "Karabiner 98" instead of the internal "Kar98K").

**Colour-coded weapon roles** — Every weapon in the sidebar is
colour-coded by its role in the game:

| Colour | Meaning | Examples |
|--------|---------|----------|
| Blue | Player loadout / gunsmith weapon | M1903, M1911, Thompson |
| Orange | Mission level pickup (not in gunsmith) | Pzb39, Panzerfaust, MG42 |
| Grey italic | Variant stub (no own stats — edit the parent) | M1911_Plus, Mk1_Welrod |

A colour key at the bottom of the sidebar shows the Loadout and Level
pickup legends.

**Tabbed detail view** — Selecting a weapon opens tabs for each
attachment slot it supports in-game:

- **Stats** — The weapon's own properties (damage, recoil, fire rate,
  effective range, muzzle velocity, sway, aim stability, etc.),
  grouped into labelled categories (Ballistics, Recoil, Sway, etc.).
- **Scope / Ammo / Barrel / Suppressor / Ironsight / Stock / Grip /
  Muzzle / Mechanism / Receiver / Construction** — One tab per
  attachment slot. A dropdown lists the compatible parts for that
  slot; selecting one loads its stats into the same property editor.
  Tabs with no compatible parts are hidden automatically.

Level-only weapons (Pzb39, Panzerfaust, MG42) show only the Stats tab
plus a notice explaining their role, and stack any linked stat-source
editors underneath (e.g. the PzB 39's ammo entity). Variant stubs show
a notice pointing to the parent weapon to edit instead.

### Property Editor

Each Stats and attachment tab uses the same property editor widget:

- **±% vs game defaults** — Every field shows a compact percentage
  label next to the spinbox, always comparing the current value to the
  shipped vanilla default (loaded from `gui/vanilla_defaults.json`).
  The label is green for increases, red for decreases, and dim grey
  when no vanilla default is known. This makes it immediately visible
  how far any value has drifted from the factory setting.
- **Warning colours** — Each spinbox has a coloured border showing
  deviation from the vanilla default: **green** (within 1.5×),
  **yellow** (within 2×), **red** (beyond 2×). A legend at the top of
  the editor shows the thresholds. MagazineCapacity, ZoomMin, ZoomMax,
  and ZoomDefault are exempt from colour coding.
- **Power / penetration markers** — Fields that actually scale
  stopping power (DamageMod, DamageModB, PenetrationMod, PressureMod)
  are marked with a 💥 icon. The listed "Damage" field is deliberately
  excluded from this marker — playtests show it does not change kills.
- **Read-only base fill-ins** — When a property exists only in the base
  `common.asr` (not in the asrpatch), it is shown as a read-only
  greyed-out field labelled "(base)" so you can see the full weapon
  profile. Only asrpatch overrides can be edited.
- **Reset** — Revert any entity to its shipped vanilla values in
  memory. Save (Ctrl+S) writes the changes to the game file.

### Sniper Tweaks

- **Disable Scope Glint** — Rewrites `common.asr` block 406 to replace
  the four glint particle-effect asset strings with dummies. Hides
  glint on all scoped weapons (player and enemy). Creates a `.bak`
  backup automatically. Includes **Re-enable Scope Glint** (restores
  block 406 only) and **Restore common.asr from .bak** (full rollback).

### Safety

- **Automatic `.bak` backup** — A snapshot of a healthy file is taken
  before the first edit. Restore refuses a damaged backup.
- **Honest limitations notice** — On first launch (and via
  Help → Limitations), the editor explains what it can and cannot
  change. Many "damage" fields do not control kills — hit location,
  Custom Difficulty, and ammo type matter more. The notice lists what
  usually still works (magazine capacity, scope zoom, handling feel).
- **Open Game Folder** — Point the editor at the Sniper Elite 5
  install (or its `misc/` folder); it finds `common.asr.asrpatch` and
  `common.asr` automatically.

## Quick Start

### Prerequisites

- Python 3.12+
- PySide6

### Install from source

```bash
git clone https://github.com/TinyUnicornMaker/Sniper-Elite-5-Editor.git
cd Sniper-Elite-5-Editor
pip install -r requirements.txt
```

### Run

```bash
python se5editor.py
```

### Opening game data

Use **Open Game Folder…** (Ctrl+O) and pick the `Sniper Elite 5`
install (or its `misc/` folder). The editor finds:

- `misc/common.asr.asrpatch` — editable weapon / attachment overrides
- `misc/common.asr` — base stats (used for scope glint disable)

### Download a prebuilt binary

Go to the [Releases page](https://github.com/TinyUnicornMaker/Sniper-Elite-5-Editor/releases)
and download the latest build for your platform:

- **Windows**: `SniperElite5Editor-vX.Y.Z-windows.zip`
- **Linux**: `SniperElite5Editor-vX.Y.Z-linux.tar.gz`

Extract and run `SniperElite5Editor` (Linux) or
`SniperElite5Editor.exe` (Windows). No Python installation required.

## Project Structure

| File | Description |
|------|-------------|
| `se5editor.py` | Application entry point (PySide6 launcher, taskbar icon setup) |
| `asr.py` | ASR/ASRpatch file parser and writer (AsuraZlb / AsuraZbb / Raw) |
| `gui/main_window.py` | Main window: toolbar, Weapon Browser tab, Sniper Tweaks tab |
| `gui/weapon_browser.py` | Sidebar tree + per-weapon tabbed attachment editor |
| `gui/weapon_mapping.py` | Weapon ↔ attachment compatibility (name-based + manual overrides) |
| `gui/property_editor.py` | Reusable property editor widget with warning colours and vanilla % |
| `gui/sniper_tweaks.py` | Scope glint disable (common.asr block 406) |
| `gui/display_names.py` | Internal entity name → in-game display name mapping |
| `gui/vanilla_defaults.py` | Shipped vanilla values (loaded from `vanilla_defaults.json`) |
| `gui/theme.py` | Military olive/amber Qt stylesheet |
| `gui/asr_backup.py` | Backup creation and validated restore |
| `gui/zbb_util.py` | AsuraZbb block-level read/rewrite utilities |
| `gui/deflate_patch.py` | In-place deflate patching helpers |
| `assets/icons/` | Application icons (16–256 px hicolor + .ico) |
| `WEAPONS.md` | Full weapons / stats / attachments reference from game data |
| `ENEMY_STATS.md` | Research notes on enemy AI, damage, and what the editor cannot change |

### Research modules (not wired into the UI)

These modules contain research and disabled writers for features that
could not be safely implemented. They are kept for reference but are
not imported by the running application:

- `gui/ai_tree.py` — AI behaviour tree research (SE3 Acquiring Timer)
- `gui/enemy_modifiers.py`, `gui/enemy_catalog.py` — Enemy stat research
- `gui/player_stats.py`, `gui/player_catalog.py`, `gui/player_io.py` — Save file research
- `gui/save_difficulty.py`, `gui/save_difficulty_panel.py` — Difficulty research
- `gui/weapon_editor.py`, `gui/scope_editor.py`, `gui/attachment_editor.py`,
  `gui/ammo_editor.py` — Legacy editors (replaced by the weapon browser)
- `gui/presets.py` — Legacy preset system (removed from UI)

## Building a Binary (Windows and Linux)

A PyInstaller spec file and GitHub Actions workflow are included for
building standalone Windows and Linux binaries.

### Local build

```bash
# Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate    # Linux
# .venv\Scripts\activate     # Windows

pip install -r requirements.txt
pip install -r requirements-dev.txt

# Build
pyinstaller se5editor.spec --noconfirm
```

Output is in `dist/SniperElite5Editor/`:

- **Linux**: `dist/SniperElite5Editor/SniperElite5Editor`
- **Windows**: `dist/SniperElite5Editor/SniperElite5Editor.exe`

#### Linux system dependencies

PySide6/Qt requires these shared libraries at build and run time:

```bash
sudo apt-get install -y libgl1 libegl1 libxkbcommon0 libdbus-1-3 \
  libfontconfig1 libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 \
  libxcb-image0 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 \
  libxcb-shape0 libxcb-sync1 libxcb-util1 libxcb-xfixes0 libxfixes3 \
  libxrandr2 libxrender1 libasound2 libpulse0 \
  libglib2.0-0 libfreetype6 libharfbuzz0b
```

### GitHub Actions (automated releases)

Push a tag to trigger the build workflow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

This builds binaries on `windows-latest` and `ubuntu-22.04` in
parallel, produces downloadable Windows (`.zip`) and Linux
(`.tar.gz`) artifacts, and creates a **draft GitHub Release** with
both binaries attached.

You can also trigger a build manually from the Actions tab
(Build Binaries → Run workflow) without creating a tag — the
artifacts get a `dev-<sha>` version label.

## ASR File Format

The game uses Asura containers. The editor accepts:

- **AsuraZlb** — normal compressed `common.asr.asrpatch` (~5–10 MB)
- **AsuraZbb** — block-compressed base archives (e.g. `common.asr`,
  ~467 MB)
- **Raw `Asura   `** — uncompressed body (~17 MB). Some Windows installs
  or third-party tools leave the patch in this form; the editor loads
  it and re-saves as AsuraZlb so the game can use the changes.

Properties are 12-byte tuples: `[type:4][value:4][hash:4]`

- Type 0 = int32
- Type 1 = float32
- Type 4 = string

Entity structure in the body:

```
[properties][type=3 marker (12 B)][type=4 name (8 B + string)]
[name_hash (4 B)][properties][type=3 marker]...
```

Properties come both before and after the entity name. The type=3
marker (`03000000 999bf855 00000000`) is the boundary between
entities. The property scanner searches between the previous and next
type=4 string boundaries to correctly attribute properties.

## Warnings

- **Restart the game** after saving — Sniper Elite 5 loads weapon
  data at startup.
- Changing RPM can cause reload animation pauses.
- High recoil values (>3.0) can cause long delays between shots.
- Changing magazine capacity can cause reload animation issues.
- Always keep the `.bak` backup so you can restore original stats.
- Prefer editing magazine entities for capacity — weapon-level
  capacity in the patch can be a reserve/pool value, not the true
  magazine size.
- Many "damage" fields do not control kills. Hit location, Custom
  Difficulty, and ammo type matter more. See **Help → Limitations**
  in the editor for details.
