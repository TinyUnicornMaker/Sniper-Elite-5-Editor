# Sniper Elite 5 Editor

A desktop application for editing weapon, scope, and attachment stats in Sniper Elite 5 ASR/ASRpatch files.

## Quick Start

```bash
cd "/home/rapunzel/Documents/AI Projects/Sniper Elite 5 Editor"
python3 se5editor.py
```

## Architecture

- `se5editor.py` — Application entry point (PySide6 launcher)
- `asr.py` — ASR/ASRpatch file parser and writer (AsuraZlb format)
- `gui/theme.py` — Military olive/amber Qt stylesheet
- `gui/main_window.py` — Main window (Weapon Browser + Sniper Tweaks only)
- `gui/weapon_browser.py` — Categorized weapon browser (sidebar tree + per-weapon tabs)
- `gui/weapon_mapping.py` — Weapon-to-attachment mapping (name-based + manual overrides)
- `gui/property_editor.py` — Reusable entity property editor widget with warning colors
- `gui/sniper_tweaks.py` — Sniper Tweaks (scope glint + restore common.asr)
- `gui/display_names.py` — Maps internal entity names to in-game display names
- `gui/weapon_editor.py` / `scope_editor.py` / `attachment_editor.py` / `ammo_editor.py` — Legacy panels / presets
- Research-only (not in UI): `player_stats.py`, `save_difficulty*.py`, `enemy_modifiers.py`, `ai_tree.py`, catalogs

## ASR File Format

The game uses Asura containers. Supported outer formats:

1. **AsuraZlb** (normal Steam `common.asr.asrpatch`, ~5–10 MB)
   - 8-byte magic (`AsuraZlb`)
   - 4-byte flags, 4-byte compressed size, 4-byte uncompressed size
   - zlib-compressed body (wbits=13)

2. **AsuraZbb** — block-compressed base archives (e.g. `common.asr`)
   - 8-byte magic (`AsuraZbb`)
   - 16-byte extra header: `(val1, val2, first_comp, first_uncomp)` as little-endian uint32s
   - `val1` = total file size minus 16; `val2` = total decompressed size
   - Block 0: `first_comp` bytes of zlib data (**wbits=12**, 4KB window, header `48 89`)
   - Subsequent blocks: 8-byte header `(comp_size, uncomp_size)` + `comp_size` bytes of zlib data (wbits=12)
   - Each block decompresses to ~2 MB (2,097,152 bytes)
   - `common.asr` has ~408 blocks (~489 MB compressed → ~854 MB decompressed)
   - **IMPORTANT**: ZBB blocks use wbits=12, NOT wbits=13 like AsuraZlb. Recompressing with the wrong wbits causes game crashes.

3. **Raw `Asura   `** (uncompressed body, ~17 MB)
   - Identical to the *decompressed* ZLB payload
   - Seen on some Windows installs / after third-party tools
   - This was the v1.0.0 "Unknown file format: b'Asura   '" Windows bug
   - On save, rewritten as AsuraZlb so the game can load it

The decompressed body itself starts with `Asura   PNFO...`.

Properties are 12-byte tuples: `[type:4][value:4][hash:4]`
- Type 0 = int32, Type 1 = float32, Type 4 = string
- Properties are NOT 4-byte aligned — scanning must be byte-by-byte
- Properties come BOTH before and after the entity name — the name sits in the middle of the property block
- Entity structure: `[properties][type=3 marker (03000000 999bf855 00000000)][type=4 name][name_hash (4B)][properties][type=3 marker]...`
- The type=3 marker (12 bytes) is the boundary between entities
- The property scanner searches from the end of the previous entity's name+hash to the start of the next entity's type=3 marker
- ALL type=4 strings (not just known entity names) mark boundaries — non-entity strings like 'Tommy_Classic' or 'SafeCode_Coast_Artillery' also separate property blocks
- The asrpatch is a PATCH file — it only contains property overrides, not full weapon definitions. Most weapons only have a few properties defined here; the rest come from the base common.asr

## Known Property Hashes

| Hash | Name | Type |
|------|------|------|
| 0x19B61B3D | EffectiveRange | float (metres) |
| 0x8C6EF316 | MuzzleVelocity | float (m/s) |
| 0xFFEBCB07 | Damage | listed score — **not** infantry HP (see WEAPONS.md) |
| 0x171B12B6 | DamageSpread | 2nd listed score / cone (two encodings) |
| 0xD02587AE | DamageMod | real power × on parts / ammo |
| 0xACB8EA97 | WindDrop | float |
| 0x2699E6A9 | RPM | float |
| 0x680784A9 | Recoil1_Vertical | float |
| 0xB9CBCCB9 | Recoil2_Horizontal | float |
| 0x6539B743 | RecoilMult | float |
| 0xF71A01A6 | ScopeInSpeed | float |
| 0x62CC2933 | ZoomMin | float |
| 0xC0104A2C | ZoomMax | float |
| 0x807AAE98 | MagazineCapacity | int |

## AI Behavior Tree (common.asr block 405)

The AI behavior tree is stored in **ZBB block 405** of the base `common.asr` file (~850 MB decompressed offset). It contains named nodes like `Sniper Combat`, `FireWeapon`, `SE3 Acquiring Timer`, `Elite Sniping`, `Panic Shot`, `LookAtAndFire`, etc.

### SE3 Acquiring Timer (research only — not exposed in UI)

The **SE3 Acquiring Timer** controls how fast enemy AI acquires/locks onto a target. Key details:

- **Default value:** 0.362 seconds (stored as float bytes `6d 58 b9 3e` = 0.362003)
- **Location:** Block 405, at decompressed offsets ~1,303,047 / 1,303,181 / 1,309,033 / 1,309,167 (4 occurrences, one per behavior tree node instance)
- **Context:** Each occurrence is within 300 bytes of the string `"Acquiring Timer"`
- **Do not write:** Recompress, same-size pad, and in-place Huffman patch of this float all crashed launch. Writers in `gui/ai_tree.py` refuse all block-405 writes. Closest in-game control: Custom Difficulty → Enemy Responsiveness / Enemy Sniper Skill. UI for this timer and the “Make Snipers Lethal” button were removed from Sniper Tweaks because they either crashed or only mirrored base-game difficulty sliders.

### Other behavior tree nodes (not yet modifiable)

The behavior tree also contains nodes for `Movement Speed`, `Aggressive Search`, `Sniper Defend`, `React To Grenade`, etc. These use a custom serialized binary format (not the asrpatch property tuple format), so they cannot be edited via the same mechanism. The float values associated with these nodes are embedded in the binary structure and would require further reverse engineering of the Asura behavior tree serialization format.

## Game File Location

```
~/.steam/debian-installation/steamapps/common/Sniper Elite 5/misc/common.asr.asrpatch
```

Always create a `.bak` backup before modifying. The editor snapshots only a healthy file and refuses to restore a damaged `.bak`. After a Steam verify, delete leftover `.bak` files so the next edit snapshots the verified stock.

## Warnings

- Changing RPM can cause reload animation pauses
- High recoil values (>3.0) can cause long delays between shots
- Changing magazine capacity can cause reload animation issues
- **Restart the game** after saving .asrpatch changes — the game loads weapon data at startup
- Weapon-level `MagazineCapacity` is reserve / max carry, **not** HUD mag size (Kar98K 60 vs mag 5; Panzerfaust 10 vs 1 rocket in the tube). Edit the magazine entity for real mag size. The Panzerfaust has no magazine entity and no stored chamber=1 field.

## Sniper Tweaks Tab

Sniper Tweaks is **scope glint only** (plus restore `common.asr` from `.bak`).

### Removed: lethal button + acquire timer

- **Make All Snipers One-Shot Lethal** — did not expose anything beyond Custom Difficulty (Player Resilience, Enemy Sniper Skill / Accuracy / Responsiveness, Health Regen). When it still wrote block 405, it crashed launch. Removed from UI; notes remain here and in `gui/sniper_tweaks.py` / `gui/ai_tree.py`.
- **AI Acquiring Timer** — unique in theory (file float 0.362 s in block 405) but every write method crashed. Not available in the base game as a free float, but Enemy Responsiveness / Sniper Skill cover the same design goal. Removed from UI.

### Research modules (not in the UI)

These remain in the tree for documentation / reverse-engineering notes but
are **not** loaded as tabs:

- **Player Stats** (`gui/player_stats.py`, `player_catalog.py`, `player_io.py`) — Cadet…Authentic + skill floats. Block-0 perk writes crash launch.
- **Save Difficulty** (`gui/save_difficulty.py`, `save_difficulty_panel.py`) — Custom Difficulty tokens in campaign/profile `.sav`. See `ENEMY_STATS.md`.
- **Enemy Modifiers** (`gui/enemy_modifiers.py`, `enemy_catalog.py`, `ai_tree.py`) — AI-tree role floats; block-405 writes refuse/crash. Full map: `ENEMY_STATS.md`.

### Disable Scope Glint

Modifies the base `common.asr` file (489 MB, AsuraZbb format) to disable the scope glint particle effect. The glint effect definitions are in **ZBB block 406** (not block 0, which only contains the asset manifest). Only block 406 is decompressed, modified, and recompressed — the rest of the file is preserved unchanged. A `.bak` backup is created automatically.

**Critical**: The ZBB blocks use **wbits=12** (4KB zlib window, header `48 89`), NOT wbits=13. Recompressing with the wrong wbits produces a different zlib header that the game's decompressor cannot handle, causing crashes.

Two modifications are applied to block 406:

1. **Texture replacement**: The glint texture path `\specialfx\pfx\glow\pfx_glow_cross_a.tga` is replaced with `\specialfx\pfx\heathaze\pfx_heathaze.tga` (same length, subtle heat-haze effect).

2. **Float zeroing**: 17 glint-unique float byte patterns (148 total occurrences) are zeroed. These were identified by scanning the entire 2 MB block and finding every float value that appears ONLY within 300 bytes of a "Glint", "Round_", or "Scope_Glint" string. This covers both the `Glint_XXX` sub-effects (VClose, Far, Close, Mid) and the `Round_XXX` sub-effects (VClose, Far, Close, Mid) that render the purple circle outlines.

The inter-block header before block 406 and the `val1` field in the extra header are updated to reflect the new compressed size.

Effect: Disables glint for ALL scoped weapons (player and enemy). Restart the game after applying.

### Enemy AI Behaviour (Info)

Full AI map is `ENEMY_STATS.md`. Short version: vision/hearing is a runtime meter (LOS + time-on-target + stance/grass/soundmask) scaled by Custom Difficulty **Enemy Perceptiveness** — no metre sight-range in any file. Goals/roles live in `common.asr` **block 407** (`EntityRole_Sniper`, Sniper Ranged Combat). Fight loops are **block 405** (acquire 0.362 s, combat ranges 15–30 m). Incoming hurt is Player Resilience + bleed + regen, not weapon `Damage`. Block 0 / 405 writes crash launch.

## Preset System

The preset bar sits **above the tabs** in the main window and applies to ALL panels at once (weapons, scopes, barrels, magazines, suppressors, ironsights, chokes, stocks/grips).

- **Apply to All & Save** — applies the selected preset to every entity in every panel, then auto-saves the file

### Presets

- **Default (Reset All to Original)** — reverts all properties to their original values
- **Extended Strengths & Weaknesses** — exaggerates strengths (1.2x–1.5x) and slightly worsens weaknesses (10–20%)

### Exempt properties

`MagazineCapacity` and `ZoomDefault` are **exempt from presets**. Modifying `MagazineCapacity` via preset breaks ammo pickup in-game, so it can only be changed manually per-entity. `ZoomMin` and `ZoomMax` ARE modified by the Extended preset.

### How it works

1. Median values are computed across all entities of the same type
2. Each property is classified as "higher is better" or "lower is better"
3. If the entity's value is a strength (≥ median for higher-better, ≤ median for lower-better), it's multiplied by 1.2–1.5x
4. If it's a weakness, it's worsened by 10–20%
5. The preset applies to the CURRENT value, not the original — use "Default (Reset All)" or "Restore from Backup" first if you want to start from defaults

## Entity Categories

The editor recognizes these weapon/attachment types (defined in `asr.py`):

- **Primary weapons** (RIFLE_ENTITIES): M1903, SREM, Kar98K, G43, M1Carbine, RSC1918, Mosin_Nagant, DLC_Mosin, Lee_Enfield, M1_Enfield, Winchester_1885, Pedersen, Type1 (TERA 1), Delisle (D.L. Carbine), G43_Kurz_Silenced
- **Shotguns** (SHOTGUN_ENTITIES): Sjogren, Drilling, M12 (Model 1912), Auto_Burglar
- **Pistols** (PISTOL_ENTITIES): M1911, M1911_Plus, Luger, Luger_Suppressed, Nambu, Webley, Welrod, Mk1_Welrod, Mk2_Welrod, Derringer, M712, ModelD, HDM, P38
- **SMGs/secondaries** (SMG_ENTITIES): GreaseGun, StenMkII, Welgun, MP.40, MP.44, SuperTommy, Thompson_Plus, Thompson, PPSH, Type100, Gustaf, EMP (ERMA.36)
- **Special / level-only** (SPECIAL_WEAPON_ENTITIES): Pzb39, Panzerfaust, MG42 — not in the pre-mission gunsmith. No attachment tabs. Linked stat sources: `Pzb39Ammo`, `MG42_DefaultMagazine`, `MG42(HalfAmmo)`. See `gui/weapon_mapping.py` (`LOADOUT_WEAPONS` vs `LEVEL_ONLY_WEAPONS`).
- **Scopes**: base optics + DLC (Model2 NV, PK Berlin, PPCo, Zf39, Type99 LMG, PU Mosin)
- **Attachments**: barrels, magazines (incl. 1903_Trench / GEW_98_Overpressure conversions), suppressors, ironsights, chokes, stocks/grips/brakes

See `WEAPONS.md` for the full stats + attachment reference extracted from the asrpatch.

## Parser pitfalls (fixed 2026-08)

Root causes of “missing stats / wrong attachments” that were fixed in `asr.py` / `weapon_mapping.py`:

1. **3-character entity names dropped** — scan used `3 < str_len`, so `G43`, `EMP`, `HDM`, `M12`, `P38` never loaded. Now `3 <= str_len`.
2. **Property bleeding** — windows used every type=4 string as a boundary and scanned *past* the entity name, so scopes/ironsights inherited neighbouring weapon Damage/Range/etc. Now windows are bounded by the entity marker `03 00 00 00 99 9b f8 55 00 00 00 00` and only cover the block *before* the name.
3. **Duplicate names kept last occurrence** — shared parts like `Blued_Lightened_Barrel` (8×) overwrote a clean first record. First marker-linked occurrence wins.
4. **Misclassification** — Thompson/PPSH/Type100/Gustaf were listed as rifles; Delisle was listed as a pistol; magazine conversions (`1903_Trench`, `GEW_98_Overpressure`) were listed as weapons.
5. **Incomplete attachment mapping** — only scopes/suppressors included generic (non-prefixed) parts; barrels/stocks/grips from workbenches were missing. Magazines like `Springfield_*` for M1903 needed name variants.
6. **asrpatch is overrides only** — sparse property lists are expected. On load the editor merges stats from sibling `common.asr` (ZBB blocks 0–1) as **read-only** fill-ins for any property missing from the patch. Edits still write only to the asrpatch.
7. **Attachment allow-lists** — per-weapon lists use name-matching + *curated* class shared pools (not “every stock in the file”). Pistols never receive rifle stocks; revolvers/integrally suppressed weapons skip suppressors/muzzles.

## Taskbar Icon Integration

The app icon (military olive crosshair) appears in the taskbar/dash on both Windows and Linux:

- **Windows**: `SetCurrentProcessExplicitAppUserModelID` is called before `QApplication` creation so Windows groups the app under its own identity (not `python.exe`). The `.exe` icon is set via the PyInstaller spec (`icon=assets/icons/se5editor.ico`).
- **Linux**: At startup, a `.desktop` file and hicolor icons are installed to `~/.local/share/` (no root needed). `setDesktopFileName` maps the window to the desktop entry so GNOME 46+ and Wayland compositors can find the icon. `setWindowIcon` sets `_NET_WM_ICON` for X11 fallback.

App identity: `com.tinyunicornmaker.se5editor`

## Dependencies

- Python 3.12+
- PySide6

## Building Binaries

The editor is distributed as a PyInstaller-built binary for Windows and Linux.

### Local build

```bash
# Install build dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt

# Build the binary
pyinstaller se5editor.spec --noconfirm

# Output is in dist/SniperElite5Editor/
```

### GitHub Actions (automated builds)

The workflow in `.github/workflows/build-binaries.yml` builds binaries for both platforms on every `v*` tag push or manual dispatch.

**To create a release:**

```bash
git tag v1.0.0
git push origin v1.0.0
```

This triggers builds on `windows-latest` and `ubuntu-22.04`. Both jobs:
1. Install Python 3.12 + dependencies
2. Build with PyInstaller using `se5editor.spec`
3. Package as `.zip` (Windows) or `.tar.gz` (Linux)
4. Upload as build artifacts (30-day retention)
5. Create a draft GitHub Release with both binaries attached

**Manual dispatch** (no tag needed): Go to Actions → Build Binaries → Run workflow. Produces artifacts with a `dev-<sha>` version label.

### PyInstaller spec (`se5editor.spec`)

- Cross-platform: uses `.ico` on Windows, `.png` on Linux
- Bundles `assets/icons/` and `gui/vanilla_defaults.json` as data files
- Excludes unused Qt modules (Qt3D, QtQml, QtWebEngine, etc.) to reduce size
- Single-folder distribution (not onefile) for faster startup
- Output: ~169 MB uncompressed, ~66 MB compressed (Linux)
