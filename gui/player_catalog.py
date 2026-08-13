"""Player-facing stats the editor can show and write.

Difficulty sliders are the in-game Custom Difficulty knobs. Their *names*
appear in common.asr as loc hashes; the live value is the current preset
(or Custom). We keep one row per named difficulty, same way the weapon
browser keeps one row per gun.

Skill magnitudes (Health Boost, Toughened, …) are real floats in
common.asr block 0 and can be written.
"""
from __future__ import annotations

from dataclasses import dataclass

# Slider steps used by the in-game Custom Difficulty UI.
SLIDER_STEPS = (
    "Greatly Reduced",
    "Reduced",
    "Normal",
    "Increased",
    "Greatly Increased",
)

REGEN_STEPS = (
    "Disabled",
    "Slow (one bar)",
    "Normal (one bar)",
    "Fast (one bar)",
    "Fast (full health)",
)


@dataclass(frozen=True)
class DiffSlider:
    key: str
    label: str
    tip: str
    kind: str = "slider"  # slider | regen
    player: bool = True   # shown on Player Stats (incoming / self)


DIFF_SLIDERS: list[DiffSlider] = [
    DiffSlider(
        "player_resilience", "Player Resilience",
        "How much damage YOU take (including bleeds).\n"
        "This combo is independent of the difficulty name — pick any "
        "step, then Apply.\n"
        "Greatly Reduced = easiest to kill (same as in-game Custom Difficulty).\n"
        "The Custom Difficulty slider is a runtime scale (not stored "
        "as an integer in common.asr). Apply writes the matching "
        "defensive perk *floats* (Health Boost / Toughened / "
        "Juggernaut / Extra Padding). Greatly Reduced uses a very "
        "small non-zero scale — exact 0.0 perk floats crashed launch.",
    ),
    DiffSlider(
        "health_regen", "Health Regeneration",
        "How much of your health bar returns after you stop taking hits, "
        "and how fast.\n"
        "Disabled = no regen (Authentic-style).\n"
        "Shown for reference — not written to common.asr yet.",
        kind="regen",
    ),
    DiffSlider(
        "enemy_resilience", "Enemy Resilience",
        "How much damage enemies take from YOUR shots.\n"
        "Higher = tankier enemies. Shown for reference — not written "
        "to common.asr yet.",
        player=False,
    ),
    DiffSlider(
        "enemy_sniper_skill", "Enemy Sniper Skill",
        "How smart and accurate enemy snipers are (lock, lead, miss chance).\n"
        "Shown for reference. Live sniper aim/lock is edited on "
        "Enemy Modifiers / Sniper Tweaks.",
        player=False,
    ),
    DiffSlider(
        "enemy_accuracy", "Enemy Accuracy",
        "How accurately all enemies shoot.\n"
        "Shown for reference — not a common.asr float we can write yet.",
        player=False,
    ),
    DiffSlider(
        "enemy_skill", "Enemy Skill",
        "General enemy intelligence (flanking, cover, decisions).\n"
        "Shown for reference — not written to common.asr yet.",
        player=False,
    ),
    DiffSlider(
        "enemy_aggression", "Enemy Aggression",
        "How eagerly enemies push or hunt after they know you exist.\n"
        "Shown for reference — not written to common.asr yet.",
        player=False,
    ),
    DiffSlider(
        "enemy_perceptiveness", "Enemy Perceptiveness",
        "How easily enemies spot you (vision, hearing, suspicion).\n"
        "Official loc: “Controls the hearing and vision of enemies.”\n"
        "This is the real sight-range scale (five steps, not metres).\n"
        "There is no 500 m detection float in common.asr.\n"
        "Shown for reference — not written to common.asr.",
        player=False,
    ),
    DiffSlider(
        "enemy_responsiveness", "Enemy Responsiveness",
        "How quickly enemies react after spotting you.\n"
        "Official loc: “Controls the speed with which enemies spot "
        "and respond to you.” In-game Custom Difficulty only.",
        player=False,
    ),
]

# Official-style presets (0=Greatly Reduced … 4=Greatly Increased).
# Regen uses REGEN_STEPS (0=Disabled … 4=Fast full).
DIFFICULTY_PRESETS: dict[str, dict[str, int]] = {
    "Cadet": {
        "player_resilience": 4,
        "health_regen": 4,
        "enemy_resilience": 1,
        "enemy_sniper_skill": 0,
        "enemy_accuracy": 0,
        "enemy_skill": 0,
        "enemy_aggression": 0,
        "enemy_perceptiveness": 0,
        "enemy_responsiveness": 0,
    },
    "Marksman": {
        "player_resilience": 3,
        "health_regen": 3,
        "enemy_resilience": 2,
        "enemy_sniper_skill": 1,
        "enemy_accuracy": 1,
        "enemy_skill": 1,
        "enemy_aggression": 1,
        "enemy_perceptiveness": 1,
        "enemy_responsiveness": 1,
    },
    "Sniper Elite": {
        "player_resilience": 1,
        "health_regen": 2,
        "enemy_resilience": 3,
        "enemy_sniper_skill": 3,
        "enemy_accuracy": 3,
        "enemy_skill": 3,
        "enemy_aggression": 3,
        "enemy_perceptiveness": 3,
        "enemy_responsiveness": 3,
    },
    "Authentic": {
        "player_resilience": 0,
        "health_regen": 0,
        "enemy_resilience": 4,
        "enemy_sniper_skill": 4,
        "enemy_accuracy": 4,
        "enemy_skill": 4,
        "enemy_aggression": 4,
        "enemy_perceptiveness": 4,
        "enemy_responsiveness": 4,
    },
}

DIFFICULTY_ORDER = ("Cadet", "Marksman", "Sniper Elite", "Authentic")

# One-shot preset: you die, they don't miss.
LETHAL_DIFFICULTY: dict[str, int] = {
    "player_resilience": 0,
    "health_regen": 0,
    "enemy_resilience": 2,
    "enemy_sniper_skill": 4,
    "enemy_accuracy": 4,
    "enemy_skill": 3,
    "enemy_aggression": 3,
    "enemy_perceptiveness": 3,
    "enemy_responsiveness": 4,
}


@dataclass(frozen=True)
class PlayerSkill:
    name: str
    display: str
    category: str
    hash: int
    default: float
    tip: str
    vmin: float = 0.01
    vmax: float = 200.0
    # Scales with Player Resilience (higher resilience → larger value)
    resilience: bool = False


# type=1 tuples in common.asr block 0 after the skill name.
PLAYER_SKILLS: list[PlayerSkill] = [
    PlayerSkill(
        "Health Boost 1", "Health Boost 1", "Body",
        0x9D63692A, 20.0, "Extra max health from this perk.",
        resilience=True,
    ),
    PlayerSkill(
        "Health Boost 2", "Health Boost 2", "Body",
        0x111F9BFF, 25.0, "Further extra max health.",
        resilience=True,
    ),
    PlayerSkill(
        "Toughened (Level 1)", "Toughened 1", "Body",
        0xC3A193BD, 25.0, "Damage resistance (perk).",
        resilience=True,
    ),
    PlayerSkill(
        "Toughened (Level 2)", "Toughened 2", "Body",
        0x9D63692A, 15.0, "Damage resistance (perk).",
        resilience=True,
    ),
    PlayerSkill(
        "Juggernaut (Level 1)", "Juggernaut 1", "Body",
        0x947E55E3, 40.0, "Heavy survivability perk.",
        resilience=True,
    ),
    PlayerSkill(
        "Juggernaut (Level 2)", "Juggernaut 2", "Body",
        0x947E55E3, 50.0, "Heavy survivability perk.",
        resilience=True,
    ),
    PlayerSkill(
        "Extra Padding (Level 2)", "Extra Padding 2", "Body",
        0x9D63692A, 10.0, "Padding / damage soak.",
        resilience=True,
    ),
    PlayerSkill(
        "Extra Padding (Level 3)", "Extra Padding 3", "Body",
        0xADC7A2B1, 30.0, "Padding / damage soak.",
        resilience=True,
    ),
    PlayerSkill(
        "Irrepressible (Level 1)", "Irrepressible 1", "Body",
        0x121B9E5B, 50.0, "Suppression / stagger resistance.",
    ),
    PlayerSkill(
        "Irrepressible (Level 2)", "Irrepressible 2", "Body",
        0x121B9E5B, 75.0, "Suppression / stagger resistance.",
    ),
    PlayerSkill(
        "Deep Breath", "Deep Breath", "Focus",
        0xC3A193BD, 50.0, "Empty-lung / hold-breath pool.",
    ),
    PlayerSkill(
        "Breath Training (Level 1)", "Breath Training 1", "Focus",
        0x9892918B, 15.0, "Hold-breath duration.",
    ),
    PlayerSkill(
        "Maintain Focus", "Maintain Focus", "Focus",
        0xC3A193BD, 1.0, "Focus sustain multiplier.",
        vmax=5.0,
    ),
    PlayerSkill(
        "Concentration (Level 1)", "Concentration 1", "Focus",
        0x7070C982, 25.0, "Focus / aim concentration.",
    ),
    PlayerSkill(
        "Concentration (Level 2)", "Concentration 2", "Focus",
        0x7070C982, 30.0, "Focus / aim concentration.",
    ),
    PlayerSkill(
        "Steady Hand", "Steady Hand", "Focus",
        0x1CEDF563, 30.0, "Aim stability perk.",
    ),
    PlayerSkill(
        "No Time To Bleed", "No Time To Bleed", "Recovery",
        0xF24887A6, 7.5, "Bleed duration / severity.",
        vmax=50.0,
    ),
    PlayerSkill(
        "Speedy Recovery", "Speedy Recovery", "Recovery",
        0x9D63692A, 1.0, "Health regen multiplier (perk).",
        vmax=10.0,
    ),
    PlayerSkill(
        "Athlete (Level 1)", "Athlete 1", "Body",
        0x121B9E5B, 33.0, "Stamina / movement perk.",
    ),
    PlayerSkill(
        "Athlete (Level 2)", "Athlete 2", "Body",
        0x121B9E5B, 50.0, "Stamina / movement perk.",
    ),
    PlayerSkill(
        "Light Footed (Level 1)", "Light Footed 1", "Body",
        0x640AB8FC, 50.0, "Stealth movement perk.",
    ),
    PlayerSkill(
        "Cardio", "Cardio", "Body",
        0x640AB8FC, 1.0, "Sprint / stamina perk.",
        vmax=10.0,
    ),
]

SKILL_CATEGORIES = ("Body", "Focus", "Recovery")


def skills_in(category: str) -> list[PlayerSkill]:
    return [s for s in PLAYER_SKILLS if s.category == category]


# Exact 0.0 on Health Boost / Toughened / Juggernaut / Padding crashed
# the game on launch. Treat resilience as a float scale, never zero.
MIN_SKILL_FLOAT = 0.01
MIN_RESILIENCE_SCALE = 0.02


def resilience_scale(step: int) -> float:
    """Map slider 0–4 to a multiplier on defensive perk magnitudes.

    Step 0 (Greatly Reduced) is a small positive float, not 0.
    """
    return {
        0: MIN_RESILIENCE_SCALE,
        1: 0.35,
        2: 1.0,
        3: 1.5,
        4: 2.0,
    }.get(step, 1.0)


def clamp_skill_float(value: float, vmin: float = MIN_SKILL_FLOAT,
                      vmax: float = 200.0) -> float:
    """Keep perk magnitudes in range and never write exact 0.0."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = MIN_SKILL_FLOAT
    if v != v:  # NaN
        v = MIN_SKILL_FLOAT
    floor = max(MIN_SKILL_FLOAT, vmin) if vmin <= 0 else max(vmin, MIN_SKILL_FLOAT)
    if v < floor:
        v = floor
    if v > vmax:
        v = vmax
    return v
