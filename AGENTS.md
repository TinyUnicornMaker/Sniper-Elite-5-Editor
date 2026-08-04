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
- `gui/main_window.py` — Main window with tabbed interface
- `gui/weapon_editor.py` — Weapon stats editor panel
- `gui/scope_editor.py` — Scope zoom and aim editor panel
- `gui/attachment_editor.py` — Generic attachment editor (barrels, magazines, suppressors, ironsights, chokes, stocks/grips)
- `gui/display_names.py` — Maps internal entity names to in-game display names (extracted from `text/PC/LOADOUT/loadout.asr_en`)
- `gui/ammo_editor.py` — Ammo & damage editor panel (dynamically lists all entities with a Damage property)

## ASR File Format

The game uses AsuraZlb containers:
- 8-byte magic (`AsuraZlb`)
- 4-byte flags, 4-byte compressed size, 4-byte uncompressed size
- zlib-compressed body (wbits=13)

Properties are 12-byte tuples: `[type:4][value:4][hash:4]`
- Type 0 = int32, Type 1 = float32, Type 4 = string
- Properties are NOT 4-byte aligned — scanning must be byte-by-byte

## Known Property Hashes

| Hash | Name | Type |
|------|------|------|
| 0x19B61B3D | EffectiveRange | float |
| 0x8C6EF316 | MuzzleVelocity | float |
| 0xFFEBCB07 | Damage | float |
| 0x171B12B6 | DamageSpread | float |
| 0xACB8EA97 | WindDrop | float |
| 0x2699E6A9 | RPM | float |
| 0x680784A9 | Recoil1_Vertical | float |
| 0xB9CBCCB9 | Recoil2_Horizontal | float |
| 0x6539B743 | RecoilMult | float |
| 0xF71A01A6 | ScopeInSpeed | float |
| 0x62CC2933 | ZoomMin | float |
| 0xC0104A2C | ZoomMax | float |
| 0x807AAE98 | MagazineCapacity | int |

## Game File Location

```
~/.steam/debian-installation/steamapps/common/Sniper Elite 5/misc/common.asr.asrpatch
```

Always create a `.bak` backup before modifying. The editor does this automatically.

## Warnings

- Changing RPM can cause reload animation pauses
- High recoil values (>3.0) can cause long delays between shots
- Changing magazine capacity can cause reload animation issues
- Some scope entities pick up properties from neighboring weapon entities (known limitation)
- **Restart the game** after saving .asrpatch changes — the game loads weapon data at startup

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

- **Primary weapons** (RIFLE_ENTITIES): M1903, SREM, Kar98K, Mosin_Nagant, G43, M1Carbine, RSC1918, Winchester_1885, Drilling, Pedersen, ModelD, Thompson, PPSH, Type100, Sjogren, Gustaf, Lee_Enfield, M1_Enfield, DLC_Mosin, Type1, GEW_98_Overpressure, 1903_Trench, G43_Kurz_Silenced
- **Secondary weapons** (PISTOL_ENTITIES): M1911, M1911_Plus, Luger, Luger_Suppressed, Nambu, Webley, Welrod, Mk1_Welrod, Mk2_Welrod, Derringer, Delisle, M712, Auto_Burglar, Geret_06_Experimental_P_Plus
- **SMGs/auto** (SMG_ENTITIES): GreaseGun, StenMkII, Welgun, MP.40, MP.44, MG42, SuperTommy, Thompson_Plus
- **Special** (SPECIAL_WEAPON_ENTITIES): Pzb39, Panzerfaust
- **Scopes** (SCOPE_ENTITIES): 14 scopes
- **Attachments**: Barrels (49), Magazines (40), Suppressors (6), Ironsights (32), Chokes (11), Stocks & Grips (27)

## Dependencies

- Python 3.12+
- PySide6
