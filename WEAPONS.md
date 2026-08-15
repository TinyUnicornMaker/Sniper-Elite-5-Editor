# Sniper Elite 5 — Weapons, Stats & Attachments

Reference built from `misc/common.asr.asrpatch` with the fixed SE5 Editor parser.

## How to read this data

| Fact | Implication |
|------|-------------|
| asrpatch = **overrides only** | Missing properties still exist in base `common.asr` (~489 MB) |
| Weapon `Damage` is a **listed score**, not kill HP | 0 or 3× stock (Sjögren 0.2→20) does not change how shots kill |
| Real power scaler is `DamageMod` (“Power ×”) | Overpressure parts store 1.2–1.4; Reduced-Load stores 0.85 |
| Ammo type is a separate layer | Soft Point / AP / Match / buckshot / slug live on their own `common.asr` entities |
| Two encodings share several hashes | Rifles ~100–250 vs SMG/shotgun ~0.05–0.5 — not one HP scale |
| Weapon `MagazineCapacity` can look wrong | Trust `*_DefaultMagazine` entities for real mag size (table below) |
| Attachment numbers are **modifiers** | Applied on equip; not full replacement stat blocks |
| Scope `ZoomMin`/`ZoomMax` | Optical magnification |

### What each weapon hash actually does (2026-08 retest)

Kills in SE5 are **hit location** (head / heart / lungs drop anyone) × Custom Difficulty **Enemy Resilience** × the **loaded ammo type**. The gunsmith string “Base damage dealt upon impact, varies with range.” describes the *idea* of a Damage bar; the hash we labelled `Damage` is not what decides infantry lethality.

| Internal name | Hash | What it actually is |
|---|---|---|
| `Damage` | `0xFFEBCB07` | Listed score. Rifles/AT ~100–250; SMG/pistol/Sjögren stock ~0.05–0.5; Super Thompson 2000. Many bolt rifles **omit** it in the patch. Playtest: 0 / 3× / Sjögren 20 = same kills. |
| `DamageSpread` | `0x171B12B6` | Second listed score. Rifles 75–150 sit next to `Damage` (M.1903 135 beside 130). Sjögren 0.025 looks like a pellet/cone term. **Two encodings, not one unit.** |
| `DamageDropoff` | `0x83BC523F` | Alternate listed score on Kar98K / Mosin / Lee Enfield / Winchester (145–150, and those guns have no `Damage` in the patch). SREM / M12 / Welrod store ~1.0 (fraction). Not a reliable metre drop-off. |
| `CombatDamageScore` | `0x65A440D8` (`D840A465`) | **RIFLES ONLY.** Playtested G43 (105). Kar98K 145, Winchester 235. Does nothing on pistols/SMGs/shotguns — hidden for them. |
| `SidearmDamageScore` | `0xA02EE0D8` | ✅ **PISTOLS — VERIFIED.** Luger 43, Nambu 39, M712 34. Not shotguns/SMGs. |
| `AltDamageScore` | `0x85E90E24` | ✅ **PISTOLS — VERIFIED.** M1911 58, Luger 43. On SMGs it's a decoy duplicate of `SMGDamageScore`. |
| `SMGDamageScore` | `0x14F34760` | 🧪 **SMGs — PLAYTEST.** Gustaf proof (Alt 999 no-op, this 40 untouched). MP.44/Thompson 45, PPSH/Type100 34, Gustaf 40, EMP 46. |
| `DamageMod` (on shotguns) | `0xD02587AE` | 🧪 **SHOTGUNS — PLAYTEST.** Shotgun damage score (base Sjogren 20, M12 5, Auto_Burglar 20). On rifles/mags/ammo it's a 1–2× multiplier; on shotguns it's the damage value. |
| `ShotgunDamageScore` | `0xD1880B7B` | ❌ **DEAD.** Tested 9999 and 0 — no in-game effect. Hidden. |
| `AmmoDamageScale` / `AmmoPowerCand` / `AmmoPenCand` | `0x0C416B3E` / `0xD0E44A75` / `0xD0E44A74` | **Playtested dead** on Soft Point — hidden from the GUI. |
| `AmmoSoftPointCand` | `0x80553FD9` | 🧪 PLAYTEST. SoftPoint 1.5 vs Match 1.0 — best unused Soft Point cand. |
| `DamageMod` / `DamageModB` | `0xD02587AE` / `0xD02587AF` | **Real power multipliers** on magazines, overpressure barrels, chokes, and ammo-type entities (`Match`, `ArmourPiercing`, `24Buckshot`, …). Gunsmith “Boosts Damage” / “Overpressure Power” write these. |
| `PowerMod` | `0x00A32AA1` | Gunsmith power-bar contribution. Overpressure often stores **10–12**, not a 1.x multiplier. |
| `PenetrationMod` | `0xD874D19C` | Penetration multiplier (~1.2 on AP / overpressure). |
| `EffectiveRange` | `0x19B61B3D` | Metres (Sjögren 50, M.1903 600). Reach, not HP. |
| `MuzzleVelocity` | `0x8C6EF316` | m/s. Drop and lead, not HP. |
| `FireRate` | `0x22983F6D` | Usually RPM (Kar98k=32, G43=400). A few guns store seconds (MG42=0.10). |
| `MagazineCapacity` (weapon) | `0x807AAE98` | Reserve / max carry, **not** HUD mag size. |
| `Recoil1_Vertical` | `0x680784A9` | Primary kick when present. Sjögren has **no** override — vertical feel then comes from recovery / sway / Climb / Kick. |
| `Recoil2_Horizontal` | `0xB9CBCCB9` | Second recoil axis. On shotguns this often feels **diagonal** (down-right), not pure left/right. |
| `RecoilRecoveryTime` | `0x99CBF4DF` | Recoil hang. Sjögren vanilla **50** (very long vs rifles). |
| `Sway*` | various | Aim wobble. On guns with no vertical recoil override, sway-per-shot can **feel like vertical kick**. |

To make a gun actually hit harder or softer: edit **Power ×** on the magazine / overpressure part, or change ammo type. Do not expect Listed Damage to do it.

### Attachment slots & typical effects

| Slot | What it usually changes |
|------|-------------------------|
| Scope | Zoom, small sway/recoil bonus |
| Barrel | Velocity, range, recoil, RoF tradeoffs |
| Magazine | Capacity (and sometimes handling) |
| Suppressor / muzzle | Loudness, recoil, velocity |
| Stock / grip / construction | Stability, sway, mobility |
| Ironsight | Default sights (few patch overrides) |
| Choke (shotguns) | Pellet spread / range |

In-game tip: press **Tab** on the gunsmith screen to see live stat deltas.

## Quick stat table (patch overrides)

Only properties present in the asrpatch are shown. Empty cells = not overridden here.

### Primary Rifles

| Weapon | Dmg | Range | Velocity | RoF | Vert Recoil | Scope-in | Mag (entity) | Unlock |
|--------|-----|-------|----------|-----|-------------|----------|--------------|--------|
| **M.1903** (`M1903`) | 130 | 600 | 850 | — | 1.223 | 0.68 | 5 | Default primary |
| **SREM-1** (`SREM`) | — | 480 | 760 | — | 0.667 | 0.65 | 1* | Default primary |
| **Karabiner 98** (`Kar98K`) | — | 400 | 740 | 32 | 1.366 | 0.05 | 5 | Mission 2 Kill List (chandelier) |
| **G43** (`G43`) | 128 | 400 | — | 400 | — | 0.61 | 10 | Complete Mission 3 |
| **M1a Carbine** (`M1Carbine`) | 141 | 280 | — | 420 | — | 0.6 | 15 | Complete Mission 5 |
| **RSC 1918** (`RSC1918`) | 128 | 240 | — | 250 | — | 0.7 | — | Mission 7 Kill List (V2) |
| **Mosin-Nagant M91/30** (`Mosin_Nagant`) | — | 550 | 860 | 30 | 1.366 | 0.05 | 5 | Rough Landing DLC |
| **Mosin-Nagant M91/30 (DLC)** (`DLC_Mosin`) | — | 600 | 780 | 28 | 1.366 | 0.05 | 5 | Rough Landing DLC variant |
| **Lee No.4** (`Lee_Enfield`) | — | 600 | 740 | — | 0.933 | 0.7 | 7* | Conqueror DLC |
| **M1 Enfield** (`M1_Enfield`) | — | — | — | — | — | — | — |  |
| **Win & Co 1885** (`Winchester_1885`) | — | 300 | 580 | 40 | — | 0.49 | 1 | Up Close and Personal DLC |
| **Pedersen Rifle** (`Pedersen`) | 1.8 | 420 | — | 280 | — | 0.58 | 10 | DLC semi-auto rifle |
| **Type TERA 1** (`Type1`) | — | 380 | 700 | — | 1.36 | 0.58 | 30 | DLC — Type TERA 1 rifle |
| **D.L. Carbine** (`Delisle`) | 130 | 180 | 290 | — | 1.367 | 0.68 | 7 | Landing Force DLC (primary) |
| Drilling (`Drilling`) | — | — | — | — | — | — | — | DLC shotgun primary (base stats only in common.asr) |
| **Sjögren Inertia** (`Sjogren`) | 0.2 | 50 | 300 | 220 | — | 0.65 | 5 | DLC shotgun primary |
| **Model 1912** (`M12`) | — | 40 | 280 | 58 | 0.733 | 0.68 | 6 | DLC — Model 1912 shotgun (secondary) |
| **Gewehr 1943 Kurz Silenced** (`G43_Kurz_Silenced`) | — | — | — | — | — | — | 10 |  |

\* = capacity taken from weapon entity (may be reserve/pool, not mag size)

### Pistols

| Weapon | Dmg | Range | Velocity | RoF | Vert Recoil | Scope-in | Mag (entity) | Unlock |
|--------|-----|-------|----------|-----|-------------|----------|--------------|--------|
| **M1911** (`M1911`) | 120 | — | — | 500 | — | 0.5 | 12 | Default pistol |
| **M1911 (Extended)** (`M1911_Plus`) | — | — | — | — | — | — | 12 |  |
| **Pistole 08** (`Luger`) | 120 | 80 | — | 440 | — | 0.48 | 56* | Mission 3 Kill List (melee takedown) |
| **Pistole 08 Suppressed** (`Luger_Suppressed`) | — | — | — | — | — | — | 7* |  |
| **Type 14 Nambu** (`Nambu`) | 0.23 | 60 | — | 430 | — | 0.4 | 120* | Mission 8 Kill List (Type 14/100) |
| **Mk VI Revolver** (`Webley`) | 0.45 | 40 | 290 | 110 | — | 0.5 | 15* | Complete Mission 2 |
| **Welrod** (`Welrod`) | — | 30 | — | 44 | 0.9 | 0.46 | 8 | Default pistol |
| **Mk1 Welrod Conversion** (`Mk1_Welrod`) | — | — | — | — | — | — | 8 |  |
| **Mk2 Welrod** (`Mk2_Welrod`) | — | — | — | — | — | — | 8 |  |
| **Double 1866** (`Derringer`) | 0.23 | 25 | 210 | 59 | 0.733 | 0.37 | 3* |  |
| **Mod.712** (`M712`) | 0.29 | — | — | 0.06 | — | — | 20 | DLC machine pistol |
| **Auto Burglar** (`Auto_Burglar`) | — | — | 300 | 0.325 | — | — | 2 | DLC shotgun-pistol |
| **Model D** (`ModelD`) | 0.21 | 60 | — | 420 | — | 0.44 | 9 | Mission 6 Kill List (poison) |
| **High Standard .22 (HS.22)** (`HDM`) | — | 60 | — | 600 | 0.6 | 0.5 | — | DLC — High Standard .22 pistol |
| **Walther P38** (`P38`) | — | 60 | — | 350 | — | 0.5 | — | Free/promo Walther P38 |

\* = capacity taken from weapon entity (may be reserve/pool, not mag size)

### SMGs

| Weapon | Dmg | Range | Velocity | RoF | Vert Recoil | Scope-in | Mag (entity) | Unlock |
|--------|-----|-------|----------|-----|-------------|----------|--------------|--------|
| **M3 Grease Gun** (`GreaseGun`) | 0.25 | 70 | — | — | — | 0.7 | 30 | DLC M3 Grease Gun |
| **Sten Mk2** (`StenMkII`) | 0.044 | 80 | 350 | 530 | — | 0.63 | 32 | Complete Mission 6 |
| **Welgun SMG** (`Welgun`) | 1.7 | 75 | — | 495 | — | 0.6 | 32 | Default secondary |
| **Machine Pist.40** (`MP.40`) | 0.25 | 90 | — | 550 | — | 0.69 | 32 | Mission 1 Kill List (explosion) |
| **Machine Pist.44** (`MP.44`) | 0.11 | 150 | — | 500 | — | 0.7 | 30 | Mission 4 Kill List (rat bomb) |
| **MG42** (`MG42`) | — | — | — | 0.1 | — | 0.15 | 1 | DLC MG |
| **Super Thompson** (`SuperTommy`) | 2000 | — | — | — | — | — | 20 |  |
| **M1A1 Gov. (Extended)** (`Thompson_Plus`) | — | — | — | — | — | — | 20 |  |
| **M1A1 Gov.** (`Thompson`) | 0.35 | 70 | — | 680 | — | 0.68 | 20 | Default secondary |
| **PPSh** (`PPSH`) | 0.25 | 80 | — | — | — | 0.7 | 35 | DLC SMG |
| **Type 100** (`Type100`) | 0.31 | 80 | — | 800 | — | 0.7 | 30 | Mission 5 Kill List (concrete) |
| **Carl Gustav M/1945** (`Gustaf`) | 0.37 | 100 | — | 600 | — | 0.65 | 34 | DLC Carl Gustav SMG |
| **ERMA.36** (`EMP`) | 0.11 | 110 | — | 550 | — | 0.7 | 48* | DLC — ERMA.36 SMG |

\* = capacity taken from weapon entity (may be reserve/pool, not mag size)

### Special Weapons

| Weapon | Dmg | Range | Velocity | RoF | Vert Recoil | Scope-in | Mag (entity) | Unlock |
|--------|-----|-------|----------|-----|-------------|----------|--------------|--------|
| **PzB 39 Anti Tank** (`Pzb39`) | 150 | — | 990 | 15 | 3.4 | 0.3 | 1 loaded; pools 10 / 12 | Level pickup (not gunsmith) |
| **Panzerfaust** (`Panzerfaust`) | — | — | — | — | — | — | 1 rocket; carry limit 10 | Level pickup launcher |
| **MG42** (`MG42`) | — | — | — | 0.1 | — | 0.15 | pool 200 / belt 1 / half 50 | Level special (`WEAPON_SPECIAL_MG42`) |

Weapon-entity `MagazineCapacity` is **not** HUD mag size. It is starting reserve or max inventory stack (Kar98K weapon=60 vs mag entity=5; Panzerfaust=10 vs 1 rocket in the tube; flare gun=10 and mines=12–14 use the same hash). These three are **not** loadout-customisable. The `Damage` column below is a **listed score** (rifles/AT ~100–250, SMG/pistol often 0.05–0.5) — not infantry HP and not comparable 1:1. Empty `Dmg` cells usually mean the patch stores that score on `DamageDropoff` instead (Kar98K / Mosin / Lee Enfield ≈ 145–150).

## Per-weapon detail

### Primary Rifles

#### M.1903 (`M1903`)

- **Unlock:** Default primary
- **Patch stats:** `AimStability=3.7`, `Damage=130`, `DamageSpread=135`, `EffectiveRange=600`, `HoldBreathDuration=0.5`, `MagazineCapacity=7`, `MuzzleVelocity=850`, `Recoil1_Vertical=1.223`, `Recoil2_Horizontal=1.533`, `RecoilRecoveryTime=11`, `RecoilResetSpeed=0.053`, `ScopeInSpeed=0.68`, `ScopeSteadyTime=1.25`, `SwayAmount=0.32`, `SwayCrouch=0.41`, `SwayDecay=0.05`, `SwayDrift=0.35`, `SwayPerShot=0.05`, `SwayProne=0.5`, `SwayRecovery=0.41`, `SwayWalk=0.41`, `WindDrop=0.028`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, M.1903, M.1903, … (+7 more)
  - **Magazine:** 1903 Trench Magazine, M.1903 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### SREM-1 (`SREM`)

- **Unlock:** Default primary
- **Patch stats:** `AimStability=3.3`, `AudibleRangeBase=120`, `DamageDropoff=1`, `DamageSpread=128`, `EffectiveRange=480`, `HoldBreathDuration=0.5`, `MagazineCapacity=1`, `MuzzleVelocity=760`, `Recoil1_Vertical=0.667`, `RecoilRecoveryTime=0.4`, `RecoilResetSpeed=0.086`, `ScopeInSpeed=0.65`, `ScopeSteadyTime=1.1`, `SwayAmount=0.3`, `SwayCrouch=0.26`, `SwayDecay=0.05`, `SwayDrift=0.35`, `SwayPerShot=0.02`, `SwayProne=0.475`, `SwayRecovery=0.26`, `SwayWalk=0.26`, `WindDrop=0.036`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+8 more)
  - **Magazine:** SREM-1
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** SREM-1
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Karabiner 98 (`Kar98K`)

- **Unlock:** Mission 2 Kill List (chandelier)
- **Patch stats:** `AimStability=4`, `DamageDropoff=150`, `EffectiveRange=400`, `FireRate=32`, `HoldBreathDuration=0.5`, `MagazineCapacity=60`, `MuzzleVelocity=740`, `Recoil1_Vertical=1.366`, `Recoil2_Horizontal=1.34`, `RecoilRecoveryTime=0.4`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.05`, `ScopeSteadyTime=1.4`, `SwayAmount=0.49`, `SwayCrouch=0.43`, `SwayDrift=0.4`, `SwayPerShot=0.05`, `SwayProne=0.6`, `SwayRecovery=0.43`, `SwayWalk=0.43`, `WindDrop=0.09`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Karabiner 98, Karabiner 98, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, … (+8 more)
  - **Magazine:** Gew98 Overpressure Magazine, Karabiner 98 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Karabiner 98 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### G43 (`G43`)

- **Unlock:** Complete Mission 3
- **Patch stats:** `AimStability=4.1`, `Damage=128`, `DamageSpread=130`, `EffectiveRange=400`, `FireRate=400`, `HoldBreathDuration=0.38`, `MagazineCapacity=60`, `RecoilRecoveryTime=13`, `RecoilResetSpeed=0.25`, `ScopeInSpeed=0.61`, `ScopeSteadyTime=1.4`, `SwayCrouch=0.38`, `SwayDrift=0.465`, `SwayPerShot=0.15`, `SwayRecovery=0.38`, `SwayWalk=0.38`, `WindDrop=0.084`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Gewehr 1943, Gewehr 1943, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, … (+7 more)
  - **Magazine:** Gewehr 1943
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Gewehr 1943
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### M1a Carbine (`M1Carbine`)

- **Unlock:** Complete Mission 5
- **Patch stats:** `AimStability=2.7`, `Damage=141`, `DamageSpread=105`, `EffectiveRange=280`, `FireRate=420`, `HoldBreathDuration=0.4`, `MagazineCapacity=7`, `RecoilRecoveryTime=14`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.6`, `ScopeSteadyTime=0.92`, `SwayCrouch=0.2`, `SwayDecay=0.7`, `SwayDrift=0.375`, `SwayPerShot=0.52`, `SwayRecovery=0.2`, `SwayWalk=0.2`, `WindDrop=0.044`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, M1a Carbine, M1a Carbine, … (+7 more)
  - **Magazine:** M1a Carbine Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M1a Carbine
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### RSC 1918 (`RSC1918`)

- **Unlock:** Mission 7 Kill List (V2)
- **Patch stats:** `AimStability=4.9`, `Damage=128`, `DamageSpread=150`, `EffectiveRange=240`, `FireRate=250`, `HoldBreathDuration=0.38`, `RecoilRecoveryTime=15`, `RecoilResetSpeed=0.25`, `ScopeInSpeed=0.7`, `ScopeSteadyTime=1.7`, `SwayCrouch=0.46`, `SwayDecay=0.55`, `SwayDrift=0.465`, `SwayPerShot=0.68`, `SwayRecovery=0.46`, `SwayWalk=0.46`, `WindDrop=0.076`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+8 more)
  - **Magazine:** RSC 1918
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** RSC 1918
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Mosin-Nagant M91/30 (`Mosin_Nagant`)

- **Unlock:** Rough Landing DLC
- **Patch stats:** `AimStability=4.3`, `DamageDropoff=150`, `DamageSpread=140`, `EffectiveRange=550`, `FireRate=30`, `HoldBreathDuration=0.6`, `MagazineCapacity=112`, `MuzzleVelocity=860`, `Recoil1_Vertical=1.366`, `Recoil2_Horizontal=1.34`, `RecoilRecoveryTime=0.6`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.05`, `ScopeSteadyTime=1.4`, `SwayAmount=0.425`, `SwayCrouch=0.42`, `SwayDrift=0.375`, `SwayPerShot=0.05`, `SwayProne=0.52`, `SwayRecovery=0.42`, `SwayWalk=0.42`, `WindDrop=0.036`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+9 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, Mosin-Nagant M91/30, Mosin-Nagant M91/30, … (+7 more)
  - **Magazine:** Mosin-Nagant Standard Magazine, Mosin-Nagant M91/30
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Mosin-Nagant M91/30 (DLC) (`DLC_Mosin`)

- **Unlock:** Rough Landing DLC variant
- **Patch stats:** `AimStability=4.9`, `DamageDropoff=150`, `EffectiveRange=600`, `FireRate=28`, `HoldBreathDuration=0.5`, `MagazineCapacity=7`, `MuzzleVelocity=780`, `Recoil1_Vertical=1.366`, `Recoil2_Horizontal=1.34`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.05`, `ScopeSteadyTime=1.7`, `SwayAmount=0.55`, `SwayCrouch=0.43`, `SwayDrift=0.41`, `SwayPerShot=0.05`, `SwayProne=0.6`, `SwayWalk=0.25`, `WindDrop=0.123`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+9 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, Mosin-Nagant M91/30, Mosin-Nagant M91/30, … (+7 more)
  - **Magazine:** Mosin-Nagant Standard Magazine, Mosin-Nagant M91/30
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Lee No.4 (`Lee_Enfield`)

- **Unlock:** Conqueror DLC
- **Patch stats:** `AimStability=2.9`, `DamageDropoff=145`, `DamageSpread=105`, `EffectiveRange=600`, `HoldBreathDuration=0.5`, `MagazineCapacity=7`, `MuzzleVelocity=740`, `Recoil1_Vertical=0.933`, `Recoil2_Horizontal=1.2`, `RecoilRecoveryTime=0.25`, `RecoilResetSpeed=6`, `ScopeInSpeed=0.7`, `ScopeSteadyTime=0.95`, `SwayAmount=0.3`, `SwayCrouch=0.29`, `SwayDecay=0.05`, `SwayDrift=0.25`, `SwayProne=0.35`, `SwayRecovery=0.29`, `SwayWalk=0.29`, `WindDrop=0.02`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### M1 Enfield (`M1_Enfield`)

- **Patch stats:** `Recoil2_Horizontal=0.85`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Win & Co 1885 (`Winchester_1885`)

- **Unlock:** Up Close and Personal DLC
- **Patch stats:** `AimStability=4.1`, `DamageDropoff=150`, `EffectiveRange=300`, `FireRate=40`, `HoldBreathDuration=0.5`, `MagazineCapacity=3`, `MuzzleVelocity=580`, `RecoilRecoveryTime=0.4`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.49`, `ScopeSteadyTime=1.5`, `SwayCrouch=0.4`, `SwayDrift=0.4`, `SwayPerShot=0.6`, `SwayProne=0.6`, `SwayRecovery=0.4`, `SwayWalk=0.4`, `WindDrop=0.044`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, A5 Win & Co Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, … (+9 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+6 more)
  - **Magazine:** Win & Co 1885
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Win & Co 1885 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Pedersen Rifle (`Pedersen`)

- **Unlock:** DLC semi-auto rifle
- **Patch stats:** `AimStability=3.6`, `Damage=1.8`, `DamageSpread=120`, `EffectiveRange=420`, `FireRate=280`, `MagazineCapacity=2`, `RecoilRecoveryTime=13`, `RecoilResetSpeed=0.25`, `ScopeInSpeed=0.58`, `ScopeSteadyTime=1.25`, `SwayCrouch=0.28`, `SwayDecay=0.49`, `SwayRecovery=0.28`, `SwayWalk=0.28`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+8 more)
  - **Magazine:** Pedersen Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Type TERA 1 (`Type1`)

- **Unlock:** DLC — Type TERA 1 rifle
- **Patch stats:** `AimStability=2.9`, `DamageDropoff=125`, `DamageSpread=110`, `EffectiveRange=380`, `HoldBreathDuration=0.5`, `MagazineCapacity=96`, `MuzzleVelocity=700`, `Recoil1_Vertical=1.36`, `RecoilRecoveryTime=0.4`, `RecoilResetSpeed=5.5`, `ScopeInSpeed=0.58`, `ScopeSteadyTime=0.95`, `SwayCrouch=0.18`, `SwayDecay=0.3`, `SwayDrift=1.6`, `SwayProne=0.375`, `SwayRecovery=0.18`, `SwayWalk=0.18`, `WindDrop=0.028`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+7 more)
  - **Magazine:** Type 100 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Type 100 Iron Sights, Type TERA 1 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### D.L. Carbine (`Delisle`)

- **Unlock:** Landing Force DLC (primary)
- **Patch stats:** `AimStability=3.7`, `Damage=130`, `DamageDropoff=9`, `DamageSpread=14`, `EffectiveRange=180`, `HoldBreathDuration=0.5`, `MagazineCapacity=7`, `MuzzleVelocity=290`, `Recoil1_Vertical=1.367`, `RecoilRecoveryTime=0.4`, `RecoilResetSpeed=1`, `ScopeInSpeed=0.68`, `ScopeSteadyTime=1.25`, `SwayAmount=0.5`, `SwayDecay=0.05`, `SwayDrift=0.25`, `SwayProne=0.35`, `SwayRecovery=0.32`, `SwayWalk=0.32`, `WindDrop=0.028`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, D.L. Carbine, D.L. Carbine, D.L. Carbine, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, … (+8 more)
  - **Magazine:** 11rd D.L. Magazine, 20rd D.L. Magazine, D.L. Carbine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** D.L. Carbine
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Drilling (`Drilling`)

- **Unlock:** DLC shotgun primary (base stats only in common.asr)
- _Not in asrpatch — open base `common.asr` for full stats._

#### Sjögren Inertia (`Sjogren`)

- **Unlock:** DLC shotgun primary
- **Patch stats:** `AimStability=6.8`, `Damage=0.2`, `DamageSpread=0.025`, `EffectiveRange=50`, `FireRate=220`, `MagazineCapacity=1`, `MuzzleVelocity=300`, `Recoil2_Horizontal=1.133`, `RecoilRecoveryTime=50`, `RecoilResetSpeed=0.95`, `ScopeInSpeed=0.65`, `ScopeSteadyTime=2.7`, `SwayDecay=0.49`, `SwayProne=1.15`, `SwayRecovery=0.36`, `SwayWalk=0.36`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Quick Load Mod, Sjögren Inertia
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Sjögren Inertia
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+25 more)
  - **Choke:** Higins Range Full Choke, Cuts Full Accuracy Choke, Cuts Modified Choke, Improved Cylinder Choke

#### Model 1912 (`M12`)

- **Unlock:** DLC — Model 1912 shotgun (secondary)
- **Patch stats:** `AimStability=6`, `AudibleRangeBase=30`, `DamageDropoff=0.96`, `DamageSpread=100`, `EffectiveRange=40`, `FireRate=58`, `MagazineCapacity=1`, `MuzzleVelocity=280`, `Recoil1_Vertical=0.733`, `Recoil2_Horizontal=1.1`, `RecoilRecoveryTime=0.3`, `RecoilResetSpeed=0.97`, `ScopeInSpeed=0.68`, `ScopeSteadyTime=2.4`, `SwayAmount=0.58`, `SwayDecay=0.05`, `SwayProne=0.97`, `SwayRecovery=0.3`, `SwayWalk=0.3`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Quick Load Mod, Model 1912 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Model 1912 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Gewehr 1943 Kurz Silenced (`G43_Kurz_Silenced`)

- **Patch stats:** _(none — base file only)_
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Gewehr 1943, Gewehr 1943, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, … (+7 more)
  - **Magazine:** Gewehr 1943
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Gewehr 1943
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

### Pistols

#### M1911 (`M1911`)

- **Unlock:** Default pistol
- **Patch stats:** `AimStability=1.8`, `Damage=120`, `DamageSpread=75`, `FireRate=500`, `MagazineCapacity=3`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.5`, `ScopeSteadyTime=1`, `SwayCrouch=0.18`, `SwayDecay=0.5`, `SwayPerShot=0.375`, `SwayRecovery=0.18`, `SwayWalk=0.18`, `WindDrop=0.5`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** M1911 Standard Magazine, M1911 Stealth Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M1911 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### M1911 (Extended) (`M1911_Plus`)

- **Patch stats:** _(none — base file only)_
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** M1911 Standard Magazine, M1911 Stealth Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M1911 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Pistole 08 (`Luger`)

- **Unlock:** Mission 3 Kill List (melee takedown)
- **Patch stats:** `AimStability=2`, `Damage=120`, `DamageSpread=0.1`, `EffectiveRange=80`, `FireRate=440`, `HoldBreathDuration=1.1`, `MagazineCapacity=56`, `RecoilRecoveryTime=9`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.48`, `SwayCrouch=0.21`, `SwayDecay=0.49`, `SwayPerShot=0.3`, `SwayRecovery=0.21`, `SwayWalk=0.21`, `WindDrop=0.8`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Pistole 08
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Pistole 08
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Pistole 08 Suppressed (`Luger_Suppressed`)

- **Patch stats:** `MagazineCapacity=7`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Pistole 08
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Pistole 08
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Type 14 Nambu (`Nambu`)

- **Unlock:** Mission 8 Kill List (Type 14/100)
- **Patch stats:** `AimStability=1.2`, `Damage=0.23`, `DamageSpread=65`, `EffectiveRange=60`, `FireRate=430`, `MagazineCapacity=120`, `Recoil2_Horizontal=1.6`, `RecoilRecoveryTime=50`, `RecoilResetSpeed=0.7`, `ScopeInSpeed=0.4`, `SwayCrouch=0.125`, `SwayDecay=0.3`, `SwayPerShot=0.325`, `SwayRecovery=0.125`, `SwayWalk=0.125`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Type 14 Nambu
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Type 14 Nambu
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Mk VI Revolver (`Webley`)

- **Unlock:** Complete Mission 2
- **Patch stats:** `AimStability=3`, `Damage=0.45`, `DamageSpread=75`, `EffectiveRange=40`, `FireRate=110`, `MagazineCapacity=15`, `MuzzleVelocity=290`, `Recoil2_Horizontal=1.4`, `RecoilResetSpeed=3`, `ScopeInSpeed=0.5`, `ScopeSteadyTime=1.7`, `SwayCrouch=0.4`, `SwayDecay=0.8`, `SwayProne=0.825`, `SwayRecovery=0.4`, `SwayWalk=0.4`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Mk VI Revolver
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Mk VI Revolver
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Welrod (`Welrod`)

- **Unlock:** Default pistol
- **Patch stats:** `AimStability=1.2`, `AudibleRangeBase=0.21`, `DamageDropoff=1`, `DamageSpread=12`, `EffectiveRange=30`, `FireRate=44`, `MagazineCapacity=15`, `Recoil1_Vertical=0.9`, `RecoilRecoveryTime=0.32`, `RecoilResetSpeed=0.5`, `ScopeInSpeed=0.46`, `SwayAmount=0.425`, `SwayCrouch=0.135`, `SwayDecay=0.1`, `SwayPerShot=0.05`, `SwayRecovery=0.135`, `SwayWalk=0.135`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Welrod, Welrod Variant Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Welrod
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Mk1 Welrod Conversion (`Mk1_Welrod`)

- **Patch stats:** _(none — base file only)_
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Welrod, Welrod Variant Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Welrod
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Mk2 Welrod (`Mk2_Welrod`)

- **Patch stats:** _(none — base file only)_
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Welrod, Welrod Variant Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Welrod
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Double 1866 (`Derringer`)

- **Patch stats:** `AimStability=1.6`, `AudibleRangeBase=-0.5`, `Damage=0.23`, `DamageDropoff=1`, `DamageSpread=0.026`, `EffectiveRange=25`, `FireRate=59`, `MagazineCapacity=3`, `MuzzleVelocity=210`, `Recoil1_Vertical=0.733`, `Recoil2_Horizontal=1.4`, `RecoilResetSpeed=0.5`, `ScopeInSpeed=0.37`, `ScopeSteadyTime=0.9`, `SwayCrouch=0.2`, `SwayDecay=0.425`, `SwayPerShot=0.325`, `SwayProne=0.325`, `SwayRecovery=0.2`, `SwayWalk=0.2`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Double 1866
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Mod.712 (`M712`)

- **Unlock:** DLC machine pistol
- **Patch stats:** `AimStability=1.2`, `Damage=0.29`, `DamageSpread=0.05`, `FireRate=0.06`, `MagazineCapacity=56`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=1`, `SwayCrouch=0.4`, `SwayDecay=0.5`, `SwayPerShot=0.475`, `SwayRecovery=0.5`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Mod.712 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Mod.712 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+25 more)

#### Auto Burglar (`Auto_Burglar`)

- **Unlock:** DLC shotgun-pistol
- **Patch stats:** `AimStability=7.3`, `DamageSpread=0.1`, `FireRate=0.325`, `MagazineCapacity=3`, `MuzzleVelocity=300`, `Recoil2_Horizontal=1.566`, `RecoilRecoveryTime=30`, `RecoilResetSpeed=0.5`, `ScopeSteadyTime=2.6`, `SwayCrouch=0.2`, `SwayProne=0.65`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Auto Burglar
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Auto Burglar
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Model D (`ModelD`)

- **Unlock:** Mission 6 Kill List (poison)
- **Patch stats:** `AimStability=1.6`, `Damage=0.21`, `DamageSpread=70`, `EffectiveRange=60`, `FireRate=420`, `MagazineCapacity=60`, `RecoilRecoveryTime=50`, `RecoilResetSpeed=0.7`, `ScopeInSpeed=0.44`, `SwayCrouch=0.15`, `SwayDecay=0.378`, `SwayPerShot=0.28`, `SwayRecovery=0.15`, `SwayWalk=0.15`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Model D
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Model D
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### High Standard .22 (HS.22) (`HDM`)

- **Unlock:** DLC — High Standard .22 pistol
- **Patch stats:** `AimStability=1`, `DamageSpread=13`, `EffectiveRange=60`, `FireRate=600`, `Recoil1_Vertical=0.6`, `RecoilResetSpeed=0.5`, `ScopeInSpeed=0.5`, `ScopeSteadyTime=0.5`, `SwayCrouch=0.2`, `SwayDecay=0.425`, `SwayPerShot=2.5`, `SwayRecovery=0.2`, `SwayWalk=0.2`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** High Standard .22 (HS.22)
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Walther P38 (`P38`)

- **Unlock:** Free/promo Walther P38
- **Patch stats:** `AimStability=1.6`, `DamageSpread=18`, `EffectiveRange=60`, `FireRate=350`, `RecoilResetSpeed=0.7`, `ScopeInSpeed=0.5`, `SwayCrouch=0.2`, `SwayDecay=0.425`, `SwayPerShot=0.325`, `SwayRecovery=0.2`, `SwayWalk=0.2`
- **Attachments found:**
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

### SMGs

#### M3 Grease Gun (`GreaseGun`)

- **Unlock:** DLC M3 Grease Gun
- **Patch stats:** `AimStability=0.31`, `Damage=0.25`, `DamageSpread=70`, `EffectiveRange=70`, `Recoil2_Horizontal=1.4`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=0.33`, `ScopeInSpeed=0.7`, `SwayCrouch=0.2`, `SwayDecay=0.425`, `SwayPerShot=0.56`, `SwayRecovery=0.2`, `SwayWalk=0.2`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, M3 Grease Gun, M3 Grease Gun, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, … (+7 more)
  - **Magazine:** M3 Grease Gun
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M3 Grease Gun
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, M3 Grease Gun, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, … (+25 more)

#### Sten Mk2 (`StenMkII`)

- **Unlock:** Complete Mission 6
- **Patch stats:** `AimStability=0.48`, `Damage=0.044`, `DamageSpread=0.1`, `EffectiveRange=80`, `FireRate=530`, `HoldBreathDuration=0.35`, `MuzzleVelocity=350`, `Recoil2_Horizontal=1.3`, `RecoilRecoveryTime=-0.6`, `RecoilResetSpeed=1.7`, `ScopeInSpeed=0.63`, `SwayCrouch=0.25`, `SwayDecay=0.3`, `SwayDrift=0.2`, `SwayPerShot=0.62`, `SwayProne=0.57`, `SwayRecovery=0.25`, `SwayWalk=0.25`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Quad M31 Magazine (Sten), Quad M31 Magazine (ERMA.36), Sten Mk2 Standard Magazine, Sten Mk5 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor, Sten Mk2 Special Silencer
  - **Ironsight:** Sten Mk2 Iron Sights, Sten Mk5 Iron Sights
  - **Stock:** Austen Control Foregrip, MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, … (+27 more)

#### Welgun SMG (`Welgun`)

- **Unlock:** Default secondary
- **Patch stats:** `AimStability=0.5`, `Damage=1.7`, `DamageSpread=98`, `EffectiveRange=75`, `FireRate=495`, `Recoil2_Horizontal=1.4`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=1`, `ScopeInSpeed=0.6`, `SwayCrouch=0.2`, `SwayDecay=0.55`, `SwayPerShot=0.65`, `SwayRecovery=0.2`, `SwayWalk=0.2`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Welgun SMG Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Welgun SMG Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Machine Pist.40 (`MP.40`)

- **Unlock:** Mission 1 Kill List (explosion)
- **Patch stats:** `AimStability=0.48`, `Damage=0.25`, `DamageSpread=90`, `EffectiveRange=90`, `FireRate=550`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=0.1`, `ScopeInSpeed=0.69`, `SwayCrouch=0.27`, `SwayDecay=0.425`, `SwayPerShot=0.53`, `SwayRecovery=0.27`, `SwayWalk=0.27`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** Machine Pist.40 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Machine Pist.40 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Machine Pist.44 (`MP.44`)

- **Unlock:** Mission 4 Kill List (rat bomb)
- **Patch stats:** `AimStability=0.73`, `Damage=0.11`, `DamageSpread=100`, `EffectiveRange=150`, `FireRate=500`, `HoldBreathDuration=0.5`, `RecoilMult=0.64`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=1.2`, `ScopeInSpeed=0.7`, `SwayCrouch=0.4`, `SwayDecay=0.67`, `SwayDrift=0.37`, `SwayPerShot=0.1`, `SwayRecovery=0.4`, `SwayWalk=0.4`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** 25rd Marksmen MP44 Magazine, Machine Pist.44 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Machine Pist.44 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Walnut Stability Stock, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, … (+25 more)

#### MG42 (`MG42`)

- **Unlock:** DLC MG
- **Patch stats:** `AimStability=0.7`, `DamageSpread=0.1`, `FireRate=0.1`, `MagazineCapacity=200`, `RecoilResetSpeed=1`, `ScopeInSpeed=0.15`, `ScopeSteadyTime=0.4`, `SwayWalk=0.6`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** MG42
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Super Thompson (`SuperTommy`)

- **Patch stats:** `Damage=2000`, `MagazineCapacity=3`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** 30rd Thompson Stick, M1A1 Gov. Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M1A1 Gov. Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### M1A1 Gov. (Extended) (`Thompson_Plus`)

- **Patch stats:** _(none — base file only)_
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** 30rd Thompson Stick, M1A1 Gov. Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M1A1 Gov. Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### M1A1 Gov. (`Thompson`)

- **Unlock:** Default secondary
- **Patch stats:** `AimStability=0.6`, `Damage=0.35`, `DamageSpread=100`, `EffectiveRange=70`, `FireRate=680`, `RecoilRecoveryTime=90`, `RecoilResetSpeed=0.45`, `ScopeInSpeed=0.68`, `SwayCrouch=0.3`, `SwayDecay=0.613`, `SwayPerShot=0.6`, `SwayRecovery=0.3`, `SwayWalk=0.3`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** 30rd Thompson Stick, M1A1 Gov. Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** M1A1 Gov. Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### PPSh (`PPSH`)

- **Unlock:** DLC SMG
- **Patch stats:** `AimStability=0.45`, `Damage=0.25`, `DamageSpread=88`, `EffectiveRange=80`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=0.33`, `ScopeInSpeed=0.7`, `SwayCrouch=0.4`, `SwayDecay=0.55`, `SwayPerShot=0.59`, `SwayRecovery=0.4`, `SwayWalk=0.4`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+5 more)
  - **Magazine:** PPSh 50rd Drum, PPSh Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** PPSh
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Type 100 (`Type100`)

- **Unlock:** Mission 5 Kill List (concrete)
- **Patch stats:** `AimStability=0.35`, `Damage=0.31`, `DamageSpread=90`, `EffectiveRange=80`, `FireRate=800`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=0.25`, `ScopeInSpeed=0.7`, `SwayCrouch=0.32`, `SwayDecay=0.55`, `SwayPerShot=0.55`, `SwayRecovery=0.32`, `SwayWalk=0.32`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, Lightened and Blued Barrel Liner, OSS Rifled Barrel, Heavy Parkerized Barrel, … (+7 more)
  - **Magazine:** Type 100 Standard Magazine
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Type 100 Iron Sights, Type TERA 1 Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, Laminated Beech Construction, … (+24 more)

#### Carl Gustav M/1945 (`Gustaf`)

- **Unlock:** DLC Carl Gustav SMG
- **Patch stats:** `AimStability=0.51`, `Damage=0.37`, `DamageSpread=90`, `EffectiveRange=100`, `FireRate=600`, `HoldBreathDuration=0.38`, `MagazineCapacity=15`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=20`, `ScopeInSpeed=0.65`, `SwayCrouch=0.25`, `SwayDecay=0.513`, `SwayPerShot=0.7`, `SwayRecovery=0.25`, `SwayWalk=0.25`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Carl Gustav M/1945, Carl Gustav M/1945, Carl Gustav M/1945, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, … (+8 more)
  - **Magazine:** Carl Gustav M/1945, Quad M31 Magazine (Gustav)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** Carl Gustav Iron Sights
  - **Stock:** MK2 Recoil Brake, FG Compensator, Featherweight Frame Stock, Fixed Frame, Carl Gustav M/1945, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, … (+25 more)

#### ERMA.36 (`EMP`)

- **Unlock:** DLC — ERMA.36 SMG
- **Patch stats:** `AimStability=0.67`, `Damage=0.11`, `DamageSpread=31`, `EffectiveRange=110`, `FireRate=550`, `HoldBreathDuration=0.48`, `MagazineCapacity=48`, `RecoilRecoveryTime=10`, `RecoilResetSpeed=1.5`, `ScopeInSpeed=0.7`, `SwayCrouch=0.35`, `SwayDecay=0.58`, `SwayDrift=0.37`, `SwayPerShot=0.55`, `SwayRecovery=0.35`, `SwayWalk=0.35`
- **Attachments found:**
  - **Scope:** A1 Optical Scope, A2 Optical Scope, B4 Win & Co Scope, W&S M1913 Scope, M81 Scope, M84 Telescopic Scope, Model 2 Night Vision Scope, No.32 Mk1 Scope, No.32 Mk2 Scope, PK Berlin Scope, … (+8 more)
  - **Barrel:** Lightened and Blued Barrel Liner, Default Barrel, ERMA.36 Standard Suppressed Barrel, ERMA.36 Extended Suppressed Barrel, ERMA.36 Muzzle Brake Barrel, Extended Artillery Barrel, Extended Carbine Barrel, Hi-Rate Heat Sink Barrel, Heavy Parkerized Barrel, Lightened and Blued Barrel Liner, … (+8 more)
  - **Magazine:** Quad M31 Magazine (ERMA.36)
  - **Suppressor:** Bramit Suppressor, Hub 23 Suppressor, Maxin 1910 Suppressor, Maxin 30 Suppressor, Moore-1 Suppressor, OSS III Suppressor
  - **Ironsight:** ERMA.36 Iron Sights
  - **Stock:** MK2 Recoil Brake, Modified ERMA.36 Foregrip, FG Compensator, Featherweight Frame Stock, Fixed Frame, Halcon Compensator, Heavy Oak Construction, Heavy Steel Assembly, Heavy Walnut Construction, Heavy Walnut Construction, … (+25 more)

### Special Weapons

#### PzB 39 Anti Tank (`Pzb39`)

- **Unlock:** Level pickup only (`WEAPON_RIFLE_PZB39`). Not in the workbench; no attachments.
- **Patch stats:** `AimStability=7`, `Damage=150`, `FireRate=15`, `MagazineCapacity=10`, `MuzzleVelocity=990`, `Recoil1_Vertical=3.4`, `RecoilResetSpeed=2`, `ScopeInSpeed=0.3`, `SwayCrouch=0.5`, `SwayProne=0.6`, `SwayWalk=0.5`, `WindDrop=0.5`
- **Linked ammo entity** `Pzb39Ammo`: `MagazineCapacity=12` plus attachment-style mods (`DamageMod=0.8`, `HandlingMod`, `StabilityMod`, `ControlMod`, `DropMod`, `VelocityMod`, `SwayMod`, `SpreadMod`, `BulletDropMod`, `PenetrationMod`). Loc key `AMMO_TYPE_PZB39` / “Anti Tank Rounds”.

#### Panzerfaust (`Panzerfaust`)

- **Unlock:** Level pickup launcher (`WEAPON_LAUNCHER_PANZERFAUST`). Not in the workbench; no attachments.
- **In-game:** 1 rocket per launcher. `MagazineCapacity=10` is the **max carry / inventory stack**, same hash as the flare gun (10) and mines (12–14). There is **no** stored chamber-size field of 1 — the tube is implicit. Loc `BASE_AMMO_PANZERFAUST_*`. No `Damage` hash on the weapon; leftover unmapped floats are shown as extras. No separate warhead entity in `common.asr` blocks 0–1.

#### MG42 (`MG42`)

- **Unlock:** Level special (`WEAPON_SPECIAL_MG42`), not an SMG gunsmith weapon.
- **Patch stats:** `AimStability=0.7`, `DamageSpread=0.1`, `FireRate=0.1`, `MagazineCapacity=200`, `RecoilResetSpeed=1`, `ScopeInSpeed=0.15`, `ScopeSteadyTime=0.4`, `SwayWalk=0.6`
- **Linked:** `MG42_DefaultMagazine` (`MagazineCapacity=1`), `MG42(HalfAmmo)` (`MagazineCapacity=50`).

## Scopes

| Scope | ZoomMin | ZoomMax | ZoomMax2 | Other |
|-------|---------|---------|----------|-------|
| M81 Scope | 5 | 10 | 1 | Recoil2_Horizontal=-0.04 |
| M84 Telescopic Scope | 4 | 8 | 1 | Recoil2_Horizontal=-0.07 |
| A1 Optical Scope | 10 | — | 14 | Recoil2_Horizontal=-0.09 |
| A2 Optical Scope | 12 | — | 16 | Recoil2_Horizontal=-0.09 |
| No.32 Mk1 Scope | 3 | 8 | — | Recoil2_Horizontal=-0.07 |
| No.32 Mk2 Scope | 4 | 8 | — | Recoil2_Horizontal=-0.06 |
| A5 Win & Co Scope | 8 | — | — | Recoil2_Horizontal=-0.05 |
| B4 Win & Co Scope | 7 | — | — | Recoil2_Horizontal=-0.05 |
| ZF41 CQB Scope | 2 | 9 | 1 | Recoil2_Horizontal=-0.09 |
| ZF4 Advanced | 2 | 4 | 26 | Recoil2_Horizontal=-0.07 |
| PU Scope | 3 | — | — | Recoil2_Horizontal=-0.02 |
| Arisaka T-99 Scope | — | — | — | DamageSpread=0.2, Recoil2_Horizontal=-0.02, AimStability=0.2, SwayCrouch=0.15 |
| Arisaka T-97 Scope | — | — | — | Recoil2_Horizontal=-0.02 |
| W&S M1913 Scope | 2 | — | 11.8 | Recoil1_Vertical=70, Recoil2_Horizontal=-0.1, SwayCrouch=40 |
| Model 2 Night Vision Scope | — | — | — | Recoil2_Horizontal=-0.1 |
| PK Berlin Scope | 300 | — | 500 | Recoil2_Horizontal=-0.04 |
| PPCo Scope | 4 | 9 | 2 | Recoil2_Horizontal=-0.03 |
| ZF39 Scope | 300 | — | 500 | Recoil2_Horizontal=-0.09 |
| Type 99 LMG Scope | 2 | 13.2 | 11.8 | Recoil2_Horizontal=-0.01, RecoilMult=0.4 |
| PU Scope (Mosin) | — | — | — | — |

## Suppressors

| Suppressor | Patch modifiers |
|------------|-----------------|
| Maxin 30 Suppressor | Recoil2_Horizontal=0.9 |
| Maxin 1910 Suppressor | Recoil2_Horizontal=1 |
| Moore-1 Suppressor | Recoil2_Horizontal=1 |
| Bramit Suppressor | RPM=-90, Recoil2_Horizontal=-14 |
| Hub 23 Suppressor | Recoil2_Horizontal=1 |
| OSS III Suppressor | Recoil2_Horizontal=0.75 |
| Sten Mk2 Special Silencer | Recoil2_Horizontal=1 |

## Magazine capacities (from magazine entities)

| Magazine | Capacity |
|----------|----------|
| Auto Burglar (`Auto_Burglar_DefaultMagazine`) | 2 |
| M1911 Stealth Magazine (`Colt_Stealth_DefaultMagazine`) | 12 |
| D.L. Carbine (`Delisle_DefaultMagazine`) | 7 |
| Drilling Standard Magazine (`Drilling_DefaultMagazine`) | 3 |
| Gewehr 1943 (`G43_DefaultMagazine`) | 10 |
| M3 Grease Gun (`GreaseGun_DefaultMagazine`) | 30 |
| Carl Gustav M/1945 (`Gustaf_DefaultMagazine`) | 34 |
| Karabiner 98 Standard Magazine (`Kar98k_DefaultMagazine`) | 5 |
| M1a Carbine Standard Magazine (`M1_Carbine_DefaultMagazine`) | 15 |
| MG42 (`MG42_DefaultMagazine`) | 1 |
| Machine Pist.40 Standard Magazine (`MP40_DefaultMagazine`) | 32 |
| Machine Pist.44 Standard Magazine (`MP44_DefaultMagazine`) | 30 |
| Mod.712 Standard Magazine (`Mauser_M712_DefaultMagazine`) | 20 |
| Model D (`ModelD_DefaultMagazine`) | 9 |
| Mosin-Nagant Standard Magazine (`Mosin_DefaultMagazine`) | 5 |
| Mosin-Nagant M91/30 (`Mosin_Nagant_DefaultMagazine`) | 5 |
| PPSh Standard Magazine (`PPSh_DefaultMagazine`) | 35 |
| Pedersen Standard Magazine (`Pederson_DefaultMagazine`) | 10 |
| Sjögren Inertia (`Sjogren_DefaultMagazine`) | 5 |
| M.1903 Standard Magazine (`Springfield_DefaultMagazine`) | 5 |
| Sten Mk2 Standard Magazine (`StenMkII_DefaultMagazine`) | 32 |
| Sten Mk5 Standard Magazine (`StenMkV_DefaultMagazine`) | 32 |
| M1A1 Gov. Standard Magazine (`Thompson_DefaultMagazine`) | 20 |
| Type 100 Standard Magazine (`Type100_DefaultMagazine`) | 30 |
| Welgun SMG Standard Magazine (`Welgun_DefaultMagazine`) | 32 |
| Welrod (`Welrod_DefaultMagazine`) | 8 |
| Win & Co 1885 (`Winchester_1885_DefaultMagazine`) | 1 |
| Model 1912 Standard Magazine (`m12_DefaultMagazine`) | 6 |

## Shared barrel upgrades (examples)

| Barrel | Patch modifiers |
|--------|-----------------|
| Lightened and Blued Barrel Liner | Recoil2_Horizontal=1.25 |
| Heavy Parkerized Barrel | Recoil2_Horizontal=0.75 |
| Specialised Stargauge Sniper Barrel | Recoil2_Horizontal=1.2 |
| Extended Artillery Barrel | RPM=70, Recoil2_Horizontal=1.15 |
| Extended Carbine Barrel | RPM=150, Recoil2_Horizontal=0.75 |
| Hi-Rate Heat Sink Barrel | Recoil2_Horizontal=1.16 |
| Overpressure Power Barrel | Recoil2_Horizontal=1.3 |
| Precision Rifled Barrel | — |
| Lightened and Blued Barrel Liner | — |
| Polished Smoothbore Barrel | Recoil2_Horizontal=4 |
| Heavy Parkerized Barrel | Recoil2_Horizontal=1.35 |

## Attachment modifier patterns

| Pattern in patch | Meaning |
|------------------|---------|
| `Recoil2_Horizontal` 0.66–1.35 on parts | Horizontal recoil when that part is equipped |
| `RPM` 0.8–1.3 on parts | Fire-rate **multiplier** |
| `ZoomMin`/`ZoomMax` on scopes | Magnification |
| Int `MagazineCapacity` on magazines | Rounds per magazine |
| Negative recoil on suppressors/scopes | Kick reduction / stability |
