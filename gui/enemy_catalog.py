"""Catalog of Sniper Elite 5 enemy (and combatant) character classes.

These names live in ``common.asr`` / ``common.asr.asrpatch`` as identity
stubs. Combat numbers are *not* on the entity — they come from the AI
behaviour tree role this class uses. See ``ENEMY_STATS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EnemyType:
    entity: str
    display: str
    category: str
    role: str
    blurb: str
    is_sniper: bool = False


# Roles map onto named nodes in common.asr block 405.
ROLE_SNIPER = "sniper"
ROLE_ELITE_SNIPER = "elite_sniper"
ROLE_INFANTRY = "infantry"
ROLE_ELITE = "elite"
ROLE_OFFICER = "officer"
ROLE_SUPPORT = "support"
ROLE_NAMED = "named"

ENEMY_TYPES: list[EnemyType] = [
    # ── Snipers ──────────────────────────────────────────────────────────
    EnemyType(
        "GermanSniper1", "German Sniper 1", "Snipers", ROLE_SNIPER,
        "Type 1 German sniper. Uses the Sniper Combat behaviour.",
        True,
    ),
    EnemyType(
        "GermanSniper2", "German Sniper 2", "Snipers", ROLE_SNIPER,
        "Type 2 German sniper. Same combat role as Type 1.",
        True,
    ),
    EnemyType(
        "GermanEliteSniper", "German Elite Sniper", "Snipers", ROLE_ELITE_SNIPER,
        "Elite sniper — loc text: superb reactions, deadly at any range.",
        True,
    ),
    EnemyType(
        "InvasionGermanSniper1", "Invasion Sniper 1", "Snipers", ROLE_SNIPER,
        "Axis Invasion variant of German Sniper 1.",
        True,
    ),
    EnemyType(
        "InvasionGermanEliteSniper", "Invasion Elite Sniper", "Snipers",
        ROLE_ELITE_SNIPER,
        "Axis Invasion elite sniper (Sniper Jäger-class).",
        True,
    ),
    EnemyType(
        "GermanSpotter", "German Spotter", "Snipers", ROLE_SNIPER,
        "Spotter attached to a sniper team.",
        True,
    ),
    EnemyType(
        "GhillieSuit", "Ghillie Suit Sniper", "Snipers", ROLE_ELITE_SNIPER,
        "Ghillie-suited sniper.",
        True,
    ),
    EnemyType(
        "GhillieSuit_Invasion", "Invasion Ghillie Sniper", "Snipers",
        ROLE_ELITE_SNIPER,
        "Axis Invasion ghillie sniper.",
        True,
    ),
    # ── Infantry ─────────────────────────────────────────────────────────
    EnemyType(
        "GermanGrunt", "German Infantry", "Infantry", ROLE_INFANTRY,
        "Standard Wehrmacht infantry (ordinary unit, ~125 HP).",
    ),
    EnemyType(
        "InvasionGermanGrunt", "Invasion Infantry", "Infantry", ROLE_INFANTRY,
        "Axis Invasion infantry.",
    ),
    EnemyType(
        "GermanEngineer", "German Engineer", "Infantry", ROLE_INFANTRY,
        "Engineer / sapper.",
    ),
    EnemyType(
        "GermanScientist", "German Scientist", "Infantry", ROLE_INFANTRY,
        "Scientist — lightly armed combatant.",
    ),
    EnemyType(
        "KriegsmarineInfantry", "Kriegsmarine Infantry", "Infantry",
        ROLE_INFANTRY,
        "Naval infantry.",
    ),
    EnemyType(
        "ResistanceFighterMale", "Resistance Fighter (M)", "Infantry",
        ROLE_INFANTRY,
        "Male resistance fighter (usually allied).",
    ),
    EnemyType(
        "ResistanceFighterFemale", "Resistance Fighter (F)", "Infantry",
        ROLE_INFANTRY,
        "Female resistance fighter (usually allied).",
    ),
    # ── Elites ───────────────────────────────────────────────────────────
    EnemyType(
        "GermanElite", "German Elite", "Elites", ROLE_ELITE,
        "Elite infantry (Jäger / ~183 HP).",
    ),
    EnemyType(
        "InvasionGermanElite", "Invasion Elite", "Elites", ROLE_ELITE,
        "Axis Invasion elite infantry.",
    ),
    EnemyType(
        "GermanEliteSupport", "German Elite Support", "Elites", ROLE_SUPPORT,
        "Support Jäger — loc: elite support troops.",
    ),
    EnemyType(
        "GermanParatrooper", "Fallschirmjäger", "Elites", ROLE_ELITE,
        "German paratrooper.",
    ),
    # ── Officers ─────────────────────────────────────────────────────────
    EnemyType(
        "GermanOfficer", "German Officer", "Officers", ROLE_OFFICER,
        "Wehrmacht officer.",
    ),
    EnemyType(
        "GermanFieldOfficer", "German Field Officer", "Officers", ROLE_OFFICER,
        "Field officer — leads from the front.",
    ),
    EnemyType(
        "GermanFieldOfficer_Invasion", "Invasion Field Officer", "Officers",
        ROLE_OFFICER,
        "Axis Invasion field officer.",
    ),
    EnemyType(
        "KriegsmarineOfficer", "Kriegsmarine Officer", "Officers", ROLE_OFFICER,
        "Naval officer.",
    ),
    EnemyType(
        "JapaneseOfficer", "Japanese Officer", "Officers", ROLE_OFFICER,
        "Imperial Japanese Navy officer.",
    ),
    EnemyType(
        "Ausland_SD", "SD Agent", "Officers", ROLE_OFFICER,
        "Sicherheitsdienst (SS security service) agent.",
    ),
    EnemyType(
        "Vogel", "Vogel", "Officers", ROLE_NAMED,
        "Named antagonist (Vogel).",
    ),
    # ── Other combatants ─────────────────────────────────────────────────
    EnemyType(
        "US_Paratrooper", "US Paratrooper", "Other", ROLE_INFANTRY,
        "US airborne (usually allied).",
    ),
    EnemyType(
        "USRanger1", "US Ranger", "Other", ROLE_INFANTRY,
        "US Ranger (usually allied).",
    ),
    EnemyType(
        "CharlieBarton", "Charlie Barton", "Other", ROLE_NAMED,
        "Named allied character.",
    ),
    EnemyType(
        "HarryHawker", "Harry Hawker", "Other", ROLE_NAMED,
        "Named allied character.",
    ),
    EnemyType(
        "JeffSullivan", "Jeff Sullivan", "Other", ROLE_NAMED,
        "Named allied character.",
    ),
    EnemyType(
        "MarieChevalier", "Marie Chevalier", "Other", ROLE_NAMED,
        "Named allied character.",
    ),
]

CATEGORIES = ["Snipers", "Infantry", "Elites", "Officers", "Other"]

ROLE_LABELS = {
    ROLE_SNIPER: "Sniper Combat",
    ROLE_ELITE_SNIPER: "Elite Sniping",
    ROLE_INFANTRY: "Close Combat / infantry",
    ROLE_ELITE: "Elite advance / close combat",
    ROLE_OFFICER: "Officer (infantry combat)",
    ROLE_SUPPORT: "Support Elite Advance",
    ROLE_NAMED: "Named NPC",
}

# Which AI-tree params apply when this role is selected.
ROLE_PARAMS: dict[str, tuple[str, ...]] = {
    ROLE_SNIPER: (
        "lookat_fire_delay", "threat_range", "look_at_range",
    ),
    ROLE_ELITE_SNIPER: (
        "lookat_fire_delay", "threat_range", "look_at_range",
    ),
    ROLE_INFANTRY: (
        "close_combat_range", "movement_speed", "threat_range",
    ),
    ROLE_ELITE: (
        "close_combat_range", "movement_speed", "advance_range", "threat_range",
    ),
    ROLE_OFFICER: (
        "close_combat_range", "movement_speed", "threat_range",
    ),
    ROLE_SUPPORT: (
        "movement_speed", "advance_range", "threat_range",
    ),
    ROLE_NAMED: (
        "movement_speed", "threat_range",
    ),
}


def types_in_category(category: str) -> list[EnemyType]:
    return [t for t in ENEMY_TYPES if t.category == category]


def sniper_types() -> list[EnemyType]:
    return [t for t in ENEMY_TYPES if t.is_sniper]


def get_type(entity: str) -> EnemyType | None:
    for t in ENEMY_TYPES:
        if t.entity == entity:
            return t
    return None
