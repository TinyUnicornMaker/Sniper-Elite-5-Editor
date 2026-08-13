# How Sniper Elite 5 enemy AI actually works

Deep file map of **vision / hearing**, **incoming damage**, and **behaviour**.
No game file was treated as off-limits. Raising rifle `Damage` in
`common.asr.asrpatch` still does **not** make AI one-shot the player.

---

## The stack (what actually runs)

```
  senses (runtime, not a metre field)
      vision: LOS + time-on-target  ×  Enemy Perceptiveness
      hearing: movement + gunshot loudness  ×  Perceptiveness
      modifiers: stance, grass, searchlights, soundmask, loud areas
           │
           ▼
  awareness state  (compiled in Sniper5_dx12.exe)
      Passive → Cautious → Suspicious → Alert
           │
           ▼
  last known position (LKP)   — where they last SAW you
           │
           ▼
  goal / role graph   common.asr block 407
      EntityRole_Sniper / EntityRole_EliteSniper
      Search, Investigate, Combat, Hunt LKP, Sniper Ranged Combat, …
           │  "Push BT"
           ▼
  behaviour tree      common.asr block 405
      FireWeapon / LookAtAndFire / SE3 Acquiring Timer (0.362 s)
      combat distances 15–30 m  (NOT sight range)
           │
           ▼
  hit?     Enemy Accuracy / Enemy Sniper Skill
  hurt?    Player Resilience + wounds + bleed − regen
           (NOT asrpatch Kar98K.Damage)
```

Custom Difficulty lives in the **save / runtime blob**, not in `common.asr`.
Block 405 / block 0 **writes crash launch**. Do not re-enable those writers.

---

## 1. What decides if they can see (or hear) you

There is **no stored “sight range = N metres”** anywhere we opened:
all 408 `common.asr` blocks, asrpatch, Parameters, mission `entdata`,
`chars/`, FG3, Stat, Rewards, tactical, or as ASCII/UTF-16 in
`Sniper5_dx12.exe`.

### 1a. Official knobs (Custom Difficulty)

From `text/PC/MENU/menu.asr_en` (HTXT):

| Slider | Official text | What it scales |
|---|---|---|
| **Enemy Perceptiveness** | “Controls the hearing **and vision** of enemies.” | Sense strength (five steps, not metres) |
| **Enemy Responsiveness** | “Controls the speed with which enemies spot and respond to you.” | How fast the awareness meter climbs, and how fast they act after a spot |
| **Enemy Sniper Skill** | “Controls the intelligence and accuracy of enemy snipers.” | Lock / lead / miss once they are in a sniper fight |
| **Enemy Skill** | “Controls the intelligence of enemies.” | Decisions (flank, cover, which goal) |
| **Enemy Aggression** | “Controls the aggression with which enemies search for and attack you.” | How hard they hunt after they know you exist |
| **Enemy Accuracy** | “Controls the accuracy with which enemies shoot.” | Hit chance for everyone |

These identifiers do **not** appear as ASCII in data files or the exe.
They are hashed into the profile save (`PC_ProfileSaves/…/slotN.sav`,
5 MB Asura `cpnf` campaign slots; `user2.dat` is a 1.6 KB sidecar).
Each Combat / toughness slider is a **4-byte runtime token** in the
cpnf trailer (not a 0–4 int). Seven are labelled below. Authentic /
Greatly Increased is the strongest legal vision scale.

### 1b. What the game itself teaches (tutorials)

`text/PC/TUTORIALS/tutorials.asr_en` — this is the real detection model:

| Rule | Quote |
|---|---|
| Vision is a **fill-over-time** meter, not a binary cone | “Enemies become more alert the longer they see you.” |
| Hearing from movement and loud fire | “Enemies will hear you when you move quickly or fire loud weapons.” |
| Hollow `!` on a tag = they can hear **shots** | “An enemy with a hollow exclamation mark over their head will hear any shots you fire.” |
| Stance + grass almost defeats vision | “Crouch or go Prone in Tall Grass to become almost completely hidden — they'll never see you coming.” |
| Searchlights raise visibility | “Searchlights will illuminate you and make you more visible.” |
| Soundmask = they are deaf | “When you or an enemy is in a Soundmask, they cannot hear any sounds you make.” Player prompts also have `Create Soundmask` / `Sabotage Speakers (Soundmask)` — you can make a mask, not only walk into one. |
| Loud area = reduced hearing | “When you or an enemy is in a Loud Area, their hearing is reduced.” |
| LKP is where they last **saw** you | “The spinning triangle … is your Last Known Position. This is where the enemies last saw you, and where they will centre their search.” |
| Alarm → reinforcements | “An enemy that sees you may run to an Alarm… they'll start calling reinforcements.” |
| Snipers prefer long range | “Snipers are very dangerous, and prefer to fight at extreme range.” |
| Hidden bodies | “A body hidden in a crate or long grass will never be found.” |

So a 500 m LOS request is not “set VisionRange=500”. Even with max
Perceptiveness they still need: line of sight, time on target, you not
in grass/prone, no map volume cutting them off, and then a goal that
lets them act at that distance.

### 1c. Awareness states (compiled)

`Sniper5_dx12.exe` goal/state table around VA file offset `0xD6C000`:

```
Passive
Cautious
Suspicious
Alert
```

HUD “Enemy Awareness” markers and awareness-audio cues
(`When enabled, plays audio cues as enemies become aware of you.`)
display this climb. They are **not** the sense itself.

### 1d. LKP events (HUD / map, not the sense)

`Parameters/parameters.asr` is UI tokens only, but it names the LKP
event enum used by the map:

`GUNSHOT_HEARD`, `SEARCH_STARTED`, `INVESTIGATE_STARTED`,
`IN_COMBAT`, `REINFORCEMENTS_CALLED`, `BODY_FOUND`.

Menu loc also has `AI_AWARENESS_VOLUME` / `_DESC` — **map-placed
volumes**, not a global radius. Mission `.tac` / `tactical.tacdt` did
not yield a metre field.

### 1e. What is *not* vision

Block 405 distances (Look-At **15 m**, Threat engage **23 m**, Close
Combat **25 m**, Advance **30 m**, plus 10 / 43 m slots) are **combat
engage** after they already know you exist. Writing them does not
extend sight, and every block-405 write still crashes launch.

Block 407 `EntityRole_Sniper` nodes have nearby floats (Search copies
**50 / 50 / 100**, Rescue **15**, Combat **20 / 100**). Those sit in
flowgraph payload. They are **not named**. Do not treat them as a
proven 50 m / 100 m sight radius.

---

## 2. What decides their behaviour

Two layers, both in `misc/common.asr`. Character class entities do
**not** carry combat floats.

### 2a. Goal / role graph — block 407 (~592 KB)

High-level **goals**. Selecting a goal can `Push BT` into block 405.

**Roles seen in data**

| Role | Where |
|---|---|
| `EntityRole_Sniper` | Search, ValidateLKP, Rescue, Combat, Propagate |
| `EntityRole_EliteSniper` | Combat (paired with Sniper), Propagate |
| `iEntityRole_Vehicle_HeavyWeapon` | VehicleCombat |

Campaign saves instantiate these as
`EntityRole_Sniper` / `EntityRole_EliteSniper` plus
`Sniper Ranged Combat CODE CREATED`,
`Sniper Close Combat CODE CREATED`,
`Combat CODE CREATED`, `Advance CODE CREATED`,
`(LEVEL FAIL-SAFE) Defend CODE CREATED`.

The exe’s **complete goal name table** (same names as block 407):

| Goal | Notes |
|---|---|
| Combat | Generic fight |
| Investigate | Stimulus / LKP check |
| Search | After they lose you |
| Hunt LKP | Drive to last seen point (block 405 + 407) |
| ValidateLKP | Confirm the last seen point (sniper-role filtered) |
| Sniper Ranged Combat | Sniper long-range fight loop |
| Sniper Close Combat | Sniper if you close |
| Sniper defend | Overwatch / hold |
| Advance On Position | Push |
| Fall Back To Position | Break contact |
| Lured Advance On Position | Attracted / baited |
| Hold Position / Temporary Defend / Emplacement | Static |
| Passive Patrol | Marked **UNUSED** in the exe table |
| Trigger Alarm | Call reinforcements |
| ReactToGrenade / ReactToSatchel / AlertExplosive / Surprise | Interrupt |
| ShotBySilencedWeapon / PanicShot / CombatMinorReaction | Interrupt |
| Propagate | Share knowledge (both sniper roles) |
| Heal / Heal Self | |
| Conversation / Vehicle* / Survival* / VIP* / Paratrooper / Salute | Special |

Flags on the graph: `SE3 Is Aggressive Combat`,
`SE3 Is Aggressive Searching`. Target filter: `+=Any Humanoid`.
Result codes in the exe: `Normal` / `Success` / `Failure` /
`Unnamed Goal` / `NO ROLE` / ` CODE CREATED`.

`GermanSniper1` vs grunt is **not** a Damage number. It is which
**EntityRole** the placed soldier is given, which goals they are
allowed to pick, and which BT they push. Mission `.pc` files do
**not** contain the ASCII class name.

Character stubs do **not** use the attachment `loc_id` / `att_id` /
`wpn_id` tags (`0x66AD0BDC` / `0x90BC6B2B` / `0xF61039E0`). After the
name they share a common header (`0xBE7C1D46`, `0x56E91D86`,
`0x5E4B28AA`, `0x0011C22D`) then a varying id. That varying id is
**not** the sniper role: `GermanSniper1` and `GermanGrunt` both use
`0x698B5870`. `GermanEliteSniper` / `GermanSpotter` /
`GermanParatrooper` share `0x2326B36A`. Role assignment is on the
mission instance → block 407 `EntityRole_*`, not a weapon id on the
class.

### 2b. Behaviour tree — block 405 (2 MB)

How they **execute** a goal. Internally: **AXBT** tree @ 1,301,483,
**AXBB** blackboard @ 1,321,014, **AIPT** @ 1,326,233. Paths:
`BehaviourTrees\Components\General` (`General_Look` /
`General_LookSlow`), `BehaviourTrees\SE5\Reactions`
(silenced-shot → `WaitTImer` → `Validate LKP`).

`Sniper Combat` is a **selector**, not a range node. Children:
`Location Defend`, `Aggressive Search`. `Elite Sniping` sits beside
`Hold Position` / `Surprise` / `Close Combat`. There are **four**
`SE3 Acquiring Timer` copies (two live 0.362 s wraps + two `*unset*`
siblings).

Designer comments (verbatim): look-at was “taken … out of here”
on grenade/attack leaves and “moved up in the tree for better
attack behaviour,” so aiming is decided **above** `FireWeapon`.

Named nodes:

| Node | Role |
|---|---|
| `Sniper Combat` / `Elite Sniping` / `Sniping` | Fight loops |
| `Sniper Defend` | Hold / overwatch |
| `FireWeapon` | Pull the trigger — **zero** Damage hash `0xFFEBCB07` |
| `LookAtAndFire` | Aim then fire (0.25 s delay slot) |
| `SE3 Acquiring Timer` | Lock-on **0.362 s** (`6d 58 b9 3e`) |
| `RangeCheckToCurrentThreat` | Combat threat distance **23 m** |
| `RangeCheckGrenadeImpactToThreat` | Grenade vs threat **43 m** and **10 m** (the leftover 10/43 slots) |
| `Look At` | **15 m** |
| `Hunt LKP` | Nearby **25 m** (search around last seen) |
| `Close Combat` / `Machine Gun Combat` / `Artillery Combat` | Other archetypes; Close Combat **25 m** is a real 03-04-03. Artillery “25 m” in the editor is a heuristic — raw bytes next to that name look like junk. |
| `Passive Patrol` / `Suspicious Search` / `Aggressive Search` | Search styles |
| `Hunt LKP` / `Has Threat` / `Panic Shot` | |
| `ShotBySilencedWeaponReaction` / `React To Grenade` | |

Designer note next to FireWeapon (verbatim):

> Interrim solution as "current threat" is a bit of a nonsense
> property for how we've got Sniper3 set up; however, I don't want
> to start fixing up the FireWeapon behaviour just yet…

`BehaviourTrees\Components\General` and `BehaviourTrees\SE5\Reactions`
are the only `BehaviourTrees\` paths in the archive (block 405).

**Writable floats we can read today** (writes still refuse — crash):

| Key | Default | Meaning |
|---|---|---|
| acquiring_timer | 0.362 s | Time to commit a shot after they are already on you |
| lookat_fire_delay | 0.25 s | LookAtAndFire pause |
| threat_range | 23 m | Combat threat, **not** vision |
| look_at_range | 15 m | Combat look, **not** vision |
| close_combat_range | 25 m | Infantry close loop |
| advance_range | 30 m | Advance On Position |
| movement_speed | 0.5 | Move scale |
| artillery_range | 25 m | Artillery combat |

### 2c. Who they are (character stubs)

Named in `text/PC/CHARACTERS/characters.asr_en`, registered in
`common.asr` block 0. **Identity only** — no Damage, HP, or vision.

| Entity | Loc blurb (short) |
|---|---|
| `GermanSniper1` | “A Type 1 German Sniper.” |
| `GermanSniper2` | “A Type 2 German Sniper.” |
| (sniper apparel text) | “finest marksmen… unstinting accuracy and patience… apparel provides essential camouflage but also crucial flexibility.” |
| `GermanEliteSniper` | “deadliest sharpshooters… superb reactions and deadly accuracy… **lethal at any range**.” |
| `GhillieSuit` | “near-complete camouflage… covert crack shots.” |
| `GermanSpotter` | mortar crew; “formidable up close as they are at range.” |
| `GermanGrunt` | “Infantry provide the backbone… Highly trained and well disciplined.” |
| `GermanElite` | veterans of “countless battlefields.” |

“Lethal at any range” is **flavour**. It is not a 500 m sight float
and not a one-shot damage scalar.

Community HP guesses (ordinary ~125, elite ~183) appear in a Reddit
post only. **They are not in any game file we opened.** Those numbers
would be *their* HP vs *your* shots anyway.

### 2d. Mission placement

`envs/M01_Coast/m_coast.pc` (458 MB) and `entdata_*` do not store
`GermanSniper1` as ASCII. Placed AI is hashed prefab + role.

Live campaign save `slot3.sav` (Asura `cpnf`, mission
`Envs\M03_Island\M_Island.pc_entdata_10`) **does** contain:

- map labels `Town_Right_Ramparts_Sniper`, `Town_Right_SniperSchool`
- `EntityRole_Sniper` / `EntityRole_EliteSniper`
- `Sniper` / `EliteSniper` / `Grunt` / `Officer` tokens
- `Sniper Ranged Combat CODE CREATED` (the goal instance)

So the bind is: **mission instance → role → goal → BT**.

---

## 3. What decides their damage (AI → you)

### 3a. Not the weapon table

`0xFFEBCB07` Damage on Kar98K / G43 / magazines is the **player
outbound** table (what *you* deal). Typical encoding:

- rifles / AT: ~100–250
- SMG / pistol: ~0.05–0.5

AI share the **weapon visual / ballistic entity**. They do **not**
use that Damage on the player. Character stubs have no Damage.
`FireWeapon` has zero Damage hashes.

### 3b. What a hit actually does

Official loc:

| Slider | Text |
|---|---|
| **Player Resilience** | “Controls how resistant you are to damage, including Bleeding Wounds.” |
| **Health Regeneration** | “Controls how much of your Health will regenerate, and how fast.” |
| **Enemy Resilience** | “Controls the resilience of enemies.” (how tanky *they* are vs you) |

Player model is **health bars + heartrate + bleeding wounds**, not
`Health=100`. Hits apply wounds; leftover can bleed.

Tutorials:

- “You are Bleeding! Until you Heal, you'll keep taking Bleeding damage.”
- “Some Ammunition and Perks can inflict Bleeding, which will continuously drain the target's health.”
- “Soft Point Ammo causes Bleeding.”
- Survival modifier: “All Enemy fire soft point rounds. Any hit on a player will cause bleeding wounds.”

Authentic also turns on **Damage Ends Empty Lung** / **Damage Ends
Focus** (interrupt, not HP math) and **disables regen**.

Cadet vs Authentic changes how deadly the *same* AI shot feels
because Resilience + regen + bleed change, not because Kar98K.Damage
changed.

### 3c. Perk floats (block 0 — present, writes crash)

Name-scoped type-1 magnitudes (hashes are **shared**, do not
search-and-replace by hash alone):

| Perk | Hash | Default | Effect |
|---|---|---|---|
| Health Boost 1 / 2 | `0x9D63692A` / `0x111F9BFF` | 20 / 25 | Extra **bars**, not +20 HP |
| Toughened 1 / 2 | `0xC3A193BD` / `0x9D63692A` | 25 / 15 | Damage resistance |
| Juggernaut 1 / 2 | `0x947E55E3` | 40 / 50 | Heavy survivability |
| Extra Padding 2 / 3 | `0x9D63692A` / `0xADC7A2B1` | 10 / 30 | Soak |
| No Time To Bleed | `0xF24887A6` | 7.5 | Bleed duration |
| Speedy Recovery | `0x9D63692A` | 1.0 | Regen perk |

Exact `0.0` on the resilience perks crashed launch. Recompressing
block 0 crashed launch. Writers stay refused.

The editor’s Player Stats “Apply Resilience” only scaled these perk
floats. That is **not** the Custom Difficulty slider.

### 3d. Incoming pipeline

```
spot (Perceptiveness + time-on-target + LOS + stance/grass/light)
  → awareness climbs (Responsiveness)
  → goal Combat / Sniper Ranged Combat  (block 407, role filter)
  → BT FireWeapon after Acquiring Timer 0.362 s  (block 405)
  → hit / miss  (Enemy Accuracy / Enemy Sniper Skill)
  → if hit:
       unnamed incoming wound
         × Player Resilience
         × Toughened / Juggernaut / Padding (if skills on)
         + bleed  (always possible; Survival soft-point = bleed on any hit)
         − No Time To Bleed / bandage
         − Health Regeneration  (Authentic = 0)
```

The **base incoming wound size** (the number Resilience scales) is
still not in any file we can name. Soft-point Survival is loc + a
runtime mode bit — no implementing entity.

---

## 4. What the editor can and cannot change

| Wanted | Real control | File-editable? |
|---|---|---|
| See you at 500 m | Perceptiveness + LOS + time-on-target + grass/stance | **No** metre field. Save tab can write Reduced / Normal only |
| Spot / react faster | Responsiveness; acquire timer 0.362 s | Timer is in 405; **writes crash**. Responsiveness: two save tokens |
| Hit more often | Enemy Accuracy / Enemy Sniper Skill | Two observed tokens each via Save Difficulty |
| Hunt harder | Enemy Aggression / Enemy Skill | Two observed tokens each via Save Difficulty |
| One-shot the player | Player Resilience Greatly Reduced + regen off (+ Survival soft-point) | Two observed Resilience / Regen tokens via Save Difficulty. Full Greatly Reduced / regen-off not mapped. Perk-zero and block-0 writes crash |
| Sniper vs grunt AI | `EntityRole_*` + goals in block 407 / mission instance | Readable; **not** wired; 407 writes untested (assume crash) |
| Your damage to *them* | Weapon Damage / Enemy Resilience | Weapon table **yes** (asrpatch). Their HP not in files |
| Scope glint | Block 406 | **Yes** (Sniper Tweaks) |

Removed from UI on purpose: “Make snipers lethal” and the acquire-timer
control. They either duplicated Custom Difficulty or crashed launch.

---

## 5. External research (engine / interviews / next hunts)

SE5 is **not** Unreal/Unity. It runs Rebellion’s in-house **Asura** engine
(since *Aliens vs Predator*, 1999). There is **no public AI SDK**, no
exported perception asset, and no community decoder for combat senses.
Community tools (Luigi’s `asura.bms`, Watto Game Extractor, older
“Asura Engine Extractor”) unpack **archives / textures / audio / HTXT**,
not behaviour or vision.

### What Rebellion has actually said

| Source | Claim that matters for AI |
|---|---|
| Jordan Woodward (Head of Design), [Wccftech Q&A, May 2022](https://wccftech.com/sniper-elite-5-qa-fsr-1-0-support-engine-advancements-and-game-improvements/) | SE5 AI is “far more reactive”: they **alert nearby soldiers**, **call reinforcements**, use **spotlights**. Vehicle AI can **leave rails** and hunt. They “added more realistic **audio and audio detection** … which sounds they hear … such as when weapons are fired.” Tools/materials improved; **no** ray tracing. |
| Tom Field (Invasion design), [Game Developer, Sep 2022](https://www.gamedeveloper.com/design/building-sniper-elite-5-invasion-mode) | “We have AI snipers, but none would ever reach” a player hunter. Invader can **mark AI**; a marked NPC that spots the host reveals him. Invaders must not “disrupt the AI too much.” |
| [MCV, 2017](https://mcvuk.com/development-news/rebellion-building-and-testing-an-in-house-cross-platform-triple-a-game-engine/) | Asura is ~90% cross-platform; file I/O / decompression is per-platform (matches our ZBB wbits-12 pain). |
| GDC Vault *Automated Game Testing Using a Numeric Domain Independent AI Planner* | Rebellion test **bots** combine a numeric planner **with behaviour trees**. That is QA, not the combat sense — but it confirms BT + planner is how they think about AI in this engine. |
| In-file comments | `SE3 Acquiring Timer`, “Sniper3” — combat BT is an evolution of **Sniper Elite 3**, not a new SE5-only format. |

So the missing “how do they see” layer is officially a **runtime sense**
(especially **audio detection**, new/improved in SE5), not a designer
metre on the weapon or class.

### Asura chunks we can name

| Tag | Where | What |
|---|---|---|
| `AsuraZbb` / `AsuraZlb` | almost everything | zlib block archive (wbits 12 / 13) |
| `FNFO` | common.asr block 0 start | file info |
| `RSCF` | older Asura “resource file”; end of block 407 | resource container |
| `HTXT` | `*.asr_en` | hashed UTF-16 loc |
| `AXBT` | block 405 @ 1,301,483 | behaviour **tree** |
| `AXBB` | block 405 @ 1,321,070 | **blackboard** (what the tree reads) |
| `AIPT` | block 405 @ 1,326,233 | AI extra (name table / params) |
| `GS2` | block 405 (17+) | **Gamescene 2** nodes/splines (Asura scene/flow) |
| `AITT` | `tactical.tacdt` | tactical overlay, not senses |
| `cpnf` | campaign `slotN.sav` | live goals + hashed difficulty |
| `CMAP` / `GUAT` | component_map / Parameters | UI / component map |
| `FXPT` / `FSX2` | 405/407 tails | particle / fullscreen FX (not AI) |

`AXBB` is the important next parse: perception almost certainly
**writes the blackboard**; the tree only reads `Has Threat` /
`CurrentThreatNotSet`. The metre lives in the writer, not the tree.

### SE4 vs SE5 (executed)

SE4 `Misc/Common.asr` (356 MB, 311 blocks) still has the **designer
names** SE5 stripped. Re-run: `python3 research_se4_ai.py`.

| | SE4 | SE5 |
|---|---|---|
| Behaviour tree | block **306** (`AXBT` @ 466479, `AXBB` @ 617310, no `AIPT`) | block **405** (`AXBT` / `AXBB` / `AIPT`) |
| Goal / `Push BT` graph | block **309** | block **407** |
| Tree paths | `BehaviourTrees\Sniper3\Members\{Attack,Defend,Patrol,Investigate,SearchForPlayer,MoveTo,Location,Support(coop)}` plus `\Squad\…` and `\Sniper\AlertOrAggressive` | Only `\Components\General` and `\SE5\Reactions` left as ASCII |
| Class ASCII | `SE4_GermanGrunt_01` (mesh/BT), not `GermanSniper1` | `GermanSniper1` stubs in block 0; role is `EntityRole_*` |
| Named roles | none (`EntityRole_Sniper` absent) | `EntityRole_Sniper` / `EliteSniper` |
| Named long-range fight | `SniperCloseCombat` + `MoveInToPlayerLOS` | **`Sniper Ranged Combat`** (new) + Close Combat |
| Custom Difficulty loc | Accuracy, Aggression, **Responsiveness**. **No “Perceptiveness” / “hearing and vision” string** | Adds **Enemy Perceptiveness** (“hearing and vision”) — matches the SE5 “audio detection” interview |
| Exe | 60 MB; `HearingScore` **not** in the exe (hashed) | 389 MB; same names stripped; goal table still lists `Sniper Ranged Combat` |

**Sense model (SE4 ASCII, SE5 hashed):**

| Blackboard / node | What it is |
|---|---|
| `HasVisualThreat` / `HadVisualThreatRecently` / `TimeSinceVisualThreat` / `TrackNoVisualThreatTime` | Vision is a **flag + recency timer**, not a metre |
| `HearingScore` / `HearingScoreBB` / `LastHearingScore` | Hearing is a **score** |
| `Timer - 30 seconds and then reset Hearing Score` | Hearing **decays in 30 s** if nothing new is heard |
| `Set Variable - Reset Hearing Knowledge` | Squad search clears hearing |
| `LookAtAndShootWhenLOS` | They only fire when they have LOS |
| `IfNoLineOfSightCloseFurther` → `PositionWithLOF` | No LOS → close until they have a line of fire |
| `Is Position In Field Of Fire?` | Separate FoF test (cover / angle) |
| `Is Inside Goal Volume` + child `?Range` | **100 m**, **300 m**, and **500 m** (the 500 m copy also has `?Waypoint Zone`) |

The **500 m** is a **goal-volume / waypoint-zone check** (search or
defend area), **not** “eyesight = 500 m”. Same node family as
“Move to goal volume” / “Default support at goal volume”.

SE5 405/407 have **zero** leftover `HearingScore` / `HasVisualThreat`
/ `Goal Volume` strings and **no** 300/500 in the 03-04-03 slots we
scanned. The logic is still there (tutorials + Perceptiveness +
`Hunt LKP`); the names were hashed or moved into the exe.

Designer comments that only survive in SE4 (hearing/search):

- “Use the 'Is Content With Role' flag … to determine when they have
  'searched' the estimated player position.”
- “Timer - 30 seconds and then reset Hearing Score”
- “While we're looking at our threat, we'll want to walk, but the
  moment we don't need to, we can go back to running.”

### Hash hunt (executed)

`?Range` was a mis-read: the `?` is the last byte of float `1.0`
(`00 00 80 3f`). The property is **`Range`** on
`Is Inside Goal Volume`.

After each condition name SE4 stores:

```
ff ff 00 00   <u32 id>   07 00 00 00   …
```

Those IDs are **not** `hash(name)`:

- `HasVisualThreat` uses **two** IDs (`74E4DB51`, `EDE4DC63`) — one
  per tree copy → **instance IDs**.
- CRC32 / FNV / djb2 / Murmur / JOAAT of the English names do **not**
  match known weapon hashes *or* these IDs.
- IDs that **do** survive SE4→SE5 are the nodes that still have ASCII
  in both trees:

| Node | ID | SE5 405 |
|---|---|---|
| `RangeCheckToCurrentThreat` | `9E0CDA57` | yes (7) |
| `Has Threat` | `45DC0022` | yes (7) |
| `Has Threat` (other copy) | `6DF6FB61` | yes |

**Not in SE5** (all 408 `common.asr` blocks, exe, asrpatch — the one
`9BBE95BC` hit is VFX noise in block 190 / asrpatch):

| Name | SE4 ID |
|---|---|
| `HasVisualThreat` family | `74E4DB51`, `EDE4DC63` |
| `Hearing Score > ZERO` | `9BBE95BC` |
| Goal-volume `Range` 100/300/500 | no separate id; floats gone from SE5 405 AI span |
| `LookAtAndShootWhenLOS` | `74D0C9A9` |
| `IfNoLineOfSightCloseFurther` | `8B59BCFD` |

SE5 AXBB also changed magic: SE4 `CPAN`, SE5 **`AMRO`**. The
blackboard was rebuilt, not just renamed. Vision/hearing left the
named tree and sit in the compiled sense + Perceptiveness LUT.

### Save diffs (mission 3, 2026-08-13 — executed)

Island `cpnf` slots from one session. The game also autosaves on
difficulty change (`DIFFICULTY_CHANGE_WILLMAKEAUTOSAVE`), so each
manual often has a twin a few seconds earlier. Offsets below are
**file offset − 16** (skip the 16-byte `Asura   cpnf` header).

| Slot (mtime) | Token / change | Meaning |
|---|---|---|
| `slot10` 01:24:44 | @3424 `0x97617C4C` | **Reduced** Perceptiveness, undetected |
| `slot6` 01:25:34 | @3424 `0xA3CB2E99` | **Normal** Perceptiveness, undetected |
| `slot7` 01:26:28 | same `0xA3CB2E99` | **Normal** Perceptiveness, **detected** |
| `slot8` 01:35:51 | @3448 `0x3AD9E73D` → `0x35C38F87` | Sniper Skill **+1**, undetected |
| `slot9` 01:39:20 | @3428 `0xA5326FEB` → `0x302E451E` | Responsiveness **+1** |
| `slot11` 01:39:45 | @3408 `0x0DCBFB91` → `0x5562CAA0` | Accuracy **+1** |
| `slot12` 01:40:17 | @3404 `0x0A9717DB` → `0x8EBC652A` | Aggression **+1** |
| `slot13` 01:44:02 (auto `slot3` 01:43:55) | @3416 `0x5BE71758` → `0x0C56C54B` | **Enemy Skill +1** |
| `slot14` 01:44:30 (auto `slot4` 01:44:24) | @3384 `0x349D2BE6` → `0x642D90B0` | **Player Resilience +1** (more vulnerable) |
| `slot15` 01:51:55 (auto `slot5` 01:51:49) | @3388 `0xF0CD89E9` → `0x1208795C` | **Enemy Resilience +1** |
| `slot16` 01:53:05 (auto `slot3` 01:52:55) | table shifted +96; token @+64 `0xB619DE2B` → `0x3D802D75` | **Health Regeneration +1** (less / slower). cpnf 3504→3600 |

The trailer is **two blocks of independent 4-byte tokens** (separator
`00000000` at 3420 and 3460). Each +1 step flipped **only that
dword** in the 3320–3480 window:

| cpnf off | Token example | Slider (proven by +1 step) |
|---|---|---|
| 3384 | `0x349D2BE6` → `0x642D90B0` | **Player Resilience** (higher token = more vulnerable in this pair) |
| 3388 | `0xF0CD89E9` → `0x1208795C` | **Enemy Resilience** |
| 3404 | `0x0A9717DB` → `0x8EBC652A` | **Enemy Aggression** |
| 3408 | `0x0DCBFB91` → `0x5562CAA0` | **Enemy Accuracy** |
| 3416 | `0x5BE71758` → `0x0C56C54B` | **Enemy Skill** |
| 3424 | `0xA3CB2E99` / `0x97617C4C` | **Enemy Perceptiveness** |
| 3428 | `0xA5326FEB` → `0x302E451E` | **Enemy Responsiveness** |
| 3432 | `0xB619DE2B` → `0x3D802D75` | **Health Regeneration** (second token = less / slower) |
| 3448 | `0x3AD9E73D` → `0x35C38F87` | **Enemy Sniper Skill** |

Tokens are **not** 0–4 integers, **not** in the exe or `common.asr`,
and **not** `crc32("Reduced")`. Named step (Normal vs Increased) is
still unknown except Perceptiveness Reduced / Normal above.

All nine Combat / toughness loc sliders are labelled. Remaining
constant trailer dwords (HUD / Radar / tagging / wind / empty-lung
candidates): 3368, 3372, 3376, 3380, 3392, 3396, 3400, 3412, 3436,
3440, 3444, 3452, 3456.

The same 96-byte table also sits in **profile `slot0.sav`** at file
offset 260 (no `cpnf` wrapper). Locate by signature `0x3FA777FE` +
separators, not a fixed offset — Health Regen grew the cpnf header
and shifted the campaign table +96. The editor’s **Save Difficulty**
tab patches these tokens in place.

**Detected** (`slot7`) vs undetected normal (`slot6`):

- `cpnf` grows **3504 → 3677** (+173 bytes) in the mid-blob
  (~offset 552): extra hashed records + more `0xC8E624FA` value
  slots (**5 → 14**). That tag appears 60× in the exe (serializer
  type), not a name.
- Goal graph ASCII is unchanged (`Combat CODE CREATED` ×5,
  `Sniper Ranged Combat` ×1, `EntityRole_Sniper` bytes identical).
  Awareness is **not** stored on those strings.

So each Custom Difficulty Combat slider is a **4-byte token in the
cpnf trailer**. Detection is a **growing list of hashed runtime
records**, not `HasVisualThreat` coming back as ASCII.

### Highest-value next hunts (updated)

1. **Named-step LUT** — tokens are not in the exe (one float
   collision only). Full Greatly Reduced → Greatly Increased needs
   either the hash function or more step pairs. The Save Difficulty
   tab writes the two observed values per slider.
2. **Audio pack** — SE5’s new slider + interview.
3. **Exe xrefs** from surviving IDs `9E0CDA57` / `45DC0022`.
4. **Mission goal volumes** in `m_*.pc` (SE4’s 100/300/500 `Range`).
5. **Survival end-of-wave enemy outline** — see section 5b below.

---

## 5b. Survival end-of-wave enemy highlight (“detective vision”)

Players call this **Batman detective vision**: when a Survival wave is
nearly cleared (community: **last ~5 enemies**), remaining hostiles get
an automatic **through-cover silhouette / outline**. Purpose is QoL so
stragglers do not soft-lock the wave counter.

### What it is *not*

| Feature | Menu / system | Can disable? | Same as wave-end outline? |
|---|---|---|---|
| **Focus** | Custom Difficulty → Focus | Yes | No — manual hold, any mode |
| **Tagging** | Custom Difficulty → Tagging | Yes | No — player/bino tags |
| **HUD Object / Player outlines** | HUD advanced | Yes | No — interactables / foliage on *you* |
| **Extra Information** | Tactical HUD | Yes | No — interactable + alarm icons |
| **AMP PenetrationShowOutline** | Multiplayer lobby (`SE.AMPSettings.*`) | MP only | No — ricochet/penetration assists |
| **Empty Lung Assists / BulletDropMarker** | Sniping / AMP | Yes | No — ballistic marker |

Community reports the Survival outline still appears on **Authentic /
realistic** setups; Steam threads request a **togglable** “detective
vision for final enemies,” which implies **no first-party off switch**.

### Where the logic lives (static reverse eng, 2026-08-13)

| Layer | Finding |
|---|---|
| `common.asr` / asrpatch | **No** `SurvivalGameManager`, outline threshold, or remaining-enemy highlight string/property |
| Map `.pc` / `.tac` / entdata | **No** plaintext highlight / remaining-enemy script knobs |
| `Parameters/parameters.asr` | Opaque; no outline keys |
| `GraphicsOptions.ini` | Display only — no HUD outline flag |
| Loc (`menu.asr_en`) | `ENEMIES_REMAINING`, `SURVIVAL_WAVE_*`, Focus / HUD outline **labels only** — no “disable last enemies outline” string. Loc hashes (`Enemies Remaining` `0xF95B8F1D`, `Wave Ending Time` `0xC5CD2F01`) are **not** in the exe (HTXT lookup). |
| Exe entity class | **`SE_ENTITYCLASS_SURVIVALGAMEMANAGER`** — factory `0x140966100`, vtable `0x140d8cbd0`, object size **0x48** (embedded in a larger parent; methods use `rcx-0x80`) |
| Exe AI goals | `Survival Advance`, `Survival Search`, `Survival Support`, `Survival Command Post Defend/Advance` (behaviour goals, not the outline) |
| Unpacked Survival methods | Message handler `0x140966300` walks a global object list; wave-stage compares at `0x140966d30` (`cmp ecx, 1` / `cmp ecx, 4`, sentinel `0x3E7`). **No `cmp *, 5` in the unpacked Survival cluster** (`0x140960000–0x140970000`) |
| Packed / `.sdata` | Several vfuncs `jmp` into `.sdata` (e.g. `0x152044c60` serialize, `0x152031fa0` parent ctor). Real tick / outline submit is **not** in the small unpacked cluster |
| Exe render | Shared **`Asura_XRay_Skin_Outline_*`** — no RIP/`u64` xrefs from `.debug` (submit is elsewhere / hashed) |
| Exe cvars (full UTF-16 dump) | **No** Survival outline / remaining-highlight variable. Closest: `AMPSettings.PenetrationShowOutline*` (AMP), `Game.IsDevMode`, `Cheat.*`, `Goal.ShowDebugInfo` |
| Console | Real Asura console (`ListVars` / `SearchVars` / `Input.CommandConsoleUsingTextEntry` @ `0x140321014`). SE3 used `~` or Ctrl+Tab. Retail may still open; listed vars will not include a Survival highlight switch |
| Difficulty trailer (`0x3FA777FE`) | Combat sliders mapped; **unmapped dwords remain** — **none proven** to gate this outline |

**Conclusion:** not a data-driven editor knob. Unpacked `SurvivalGameManager` is a thin 0x48-byte façade. The remaining-count → outline path is either on the **parent object** or a **shared highlight submit** (same family as Focus), with no `5` compare sitting in the obvious unpacked methods. Loc string **Wave Ending Time** is a hint the game treats a **wave-ending phase**, not only a raw count.

### Binary anchors (SE5 2.41 / Jun 2025 build)

| Item | VA |
|---|---|
| Class name string | `0x140d8bf18` |
| Factory | `0x140966100` |
| Vtable | `0x140d8cbd0` |
| Message / object-walk | `0x140966300` / `0x140966340` |
| Wave-stage helper | `0x140966d30` |
| Console input bind helper | `0x140321014` |

### Unmapped difficulty-table slots (still worth A/B)

Relative to table signature `0x3FA777FE` (96 bytes). Mapped combat
offsets: +16, +20, +36, +40, +48, +56, +60, +64, +80. Separators at
+52 and +92.

| Rel | Example (profile slot0) | Likely class (unproven) |
|---|---|---|
| +04, +08 | `0x1AE6D591`, `0x5376C869` | Table / schema constants |
| +12 | `0xC475E7AB` / campaign `0xA33D9C23` | Preset / mode hash (varies) |
| +24, +28, +32 | `0xBD7D48B8`, `0xC7BA07A6`, `0x1443E682` | Sniping or tactical bools (candidates) |
| +44 | `0x10C2C8D7` | Unknown |
| +68, +72, +76 | `0xFD86EAD4`, `0xBE8564A0`, `0xA483D99C` | HUD / Radar / Tagging cluster? |
| +84, +88 | `0x3EA835D2`, `0xDDE5C37C` | Unknown |

Even if HUD tokens are mapped, community evidence says the wave-end
outline is **mode-scripted**, not “HUD Authentic”.

### Ways to turn it off (ranked)

| # | Approach | Feasibility | Risk | Notes |
|---|---|---|---|---|
| 0 | In-game menu | **None found** | — | No “Survival last-enemy outline” toggle in loc |
| 1 | **In-game console `SearchVars`** | High value next step | Low | Exe has full console (`ListVars`, `SearchVars`, `ListCmds`, `Game.IsDevMode`, `Cheat.*`). Search `outline`, `highlight`, `surviv`, `xray`. May need dev mode / retail unlock unknown |
| 2 | **Save A/B of unmapped trailer slots** | Medium for other HUD flags; **low** for this feature | Low | Flip one token while mid-Survival with ≤5 left; snapshot before/after |
| 3 | **Binary: threshold compare → 0** | Medium–high if found | High | Patch `SurvivalGameManager` remaining-count gate so outline never enables. Needs live RE (x64 PE heavily nonstandard section layout) |
| 4 | **Binary: NOP outline-enable call** | Medium | High | Prefer over nuking all X-Ray if call site is Survival-only |
| 5 | **Binary: break `Asura_XRay_Skin_Outline_*`** | Easy-ish | **Very high** | Breaks kill-cam / Focus-like silhouettes / other outlines |
| 6 | **`common.asr` / asrpatch** | **None** | — | No data surface found |
| 7 | **Editor weapon/stat write** | **None** | — | Wrong layer |

### Next experiments (ordered)

1. **Playtest confirm** — note exact remaining count when outline starts; whether it is wall-see X-Ray vs edge outline; whether Focus-off / HUD-off changes it (expected: no).
2. **Console** — open command console (keybind TBD; strings exist for `CommandConsole`, `consbk.dds`, `ListVars` / `SearchVars`). Dump vars matching outline/highlight/surviv.
3. **Difficulty A/B** — Custom Difficulty Authentic HUD + Focus off during end of wave; if outline remains, data-path is not the trailer HUD tokens.
4. **Live RE** — attach debugger on remaining-count HUD updates or X-Ray outline submit when count hits threshold; locate `cmp` immediate and Survival-only call.
5. Only then consider a **safe retail binary patch** (backup exe) or a future editor “Survival outline off” that applies that patch.

Helper: `gui/survival_highlight_research.py` dumps the difficulty table and unmapped slots from a `.sav`.

---

## 6. Still unknown

1. Numeric table behind Perceptiveness steps (what “Greatly Increased”
   multiplies). SE4 did not even *name* this slider.
2. Hash of `HasVisualThreat` / `HearingScore` / goal-volume `?Range`
   in SE5 (plaintext only in SE4).
3. Whether SE5 still has 300/500 m **goal volumes** under a hash.
4. Prefab hash `GermanSniper1` → `EntityRole_Sniper`.
5. Base incoming wound points per AI weapon / ammo.
6. Named step LUT for each token (which hash is Greatly Reduced vs
   Increased). Layout is the cpnf trailer; values are not 0–4 ints.
7. Soft-point Survival implementation.
8. Safe write path for blocks 0, 405, 407. Do not write SE4 either.

---

## File index

| File | Role |
|---|---|
| `misc/common.asr` block 0 | Weapon tables, perk floats, character **name stubs** |
| `misc/common.asr` block 405 | Behaviour trees (how they fight) |
| `misc/common.asr` block 406 | Scope glint VFX |
| `misc/common.asr` block 407 | Goal / role graph (`EntityRole_*`, Sniper Ranged Combat) |
| `misc/common.asr.asrpatch` | Player weapon/attachment overrides; character stubs |
| `bin/Sniper5_dx12.exe` | Awareness states, full goal name table (compiled) |
| `text/PC/MENU/menu.asr_en` | Difficulty slider names + official descriptions |
| `text/PC/TUTORIALS/tutorials.asr_en` | Detection / LKP / bleed / sniper-range teaching |
| `text/PC/CHARACTERS/characters.asr_en` | Class flavour (not numbers) |
| `Parameters/parameters.asr` | UI tokens + `AILKPEvent_Values` names |
| `envs/MXX_*/m_*.pc` + `entdata_*` | Placed AI by hash; no class ASCII |
| `PC_ProfileSaves/…/slotN.sav` | Live goals + roles + (hashed) difficulty |
| `Stat/`, `Rewards/`, `FG3/`, `chars/` | Telemetry / GUI / empty MP stubs — not combat math |

---

## Historical (keep)

- Rifle-Damage “lethal” was a no-op (wrong layer).
- Block 0 perk zeros and recompress: crash.
- Block 405 recompress / padded recompress / in-place Huffman: crash.
- Restore must copy `common.asr.bak` onto `common.asr`, not the patch;
  poisoned backups need Steam verify (app **1029690**).
