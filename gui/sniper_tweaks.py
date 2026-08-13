"""Sniper Tweaks panel — scope glint disable only.

What was removed (do not re-add without a proven safe write path):
--------------------------------------------------------------
1. "Make All Snipers One-Shot Lethal" / Reset Sniper AI
   Did nothing the base game cannot already do. Incoming one-shots and
   sniper aim are Custom Difficulty (Player Resilience, Enemy Sniper
   Skill / Accuracy / Responsiveness, Health Regen). The editor never
   found a safe file write for that path. See ENEMY_STATS.md layer 3.

2. AI Acquiring Timer (spin + Apply / Reset)
   SE3 Acquiring Timer lives in common.asr block 405 (default 0.362 s,
   bytes 6d58b93e). Every write method crashed launch: full recompress,
   same-size padded recompress, and a 14-byte in-place Huffman patch.
   Closest in-game knobs: Enemy Responsiveness / Enemy Sniper Skill.
   Research and the disabled writers stay in gui/ai_tree.py.

3. Sniper detection / sight range (e.g. 500 m LOS)
   No stored metre field in common.asr (all 408 blocks), character
   stubs, Parameters, mission entdata, or the exe as ASCII. Block 405
   "ranges" are 15–30 m combat engage, not vision. Real control is
   in-game Enemy Perceptiveness. See ENEMY_STATS.md §2b.

This tab only keeps scope glint (block 406) and restore-from-.bak.
"""
from __future__ import annotations

import json
import os
import struct
import zlib
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QGroupBox, QScrollArea, QPushButton, QMessageBox,
)

from gui.theme import (
    TEXT_MUTED, SUCCESS, WARNING, muted_style,
)
from gui.asr_backup import ensure_backup, restore_backup
from gui.zbb_util import rewrite_block, validate_zbb
from asr import AsrFile


# ── Scope Glint ───────────────────────────────────────────────────────────
#
# The scope glint effect is defined in ZBB block 406 of common.asr.
# It consists of several sub-effects (Glint_VClose, Glint_Far, Glint_Close,
# Glint_Mid, Round_VClose, Round_Far, Round_Close, Round_Mid) that each
# reference a glint texture and have scale/intensity float values.
#
# To disable glint, we modify block 406:
# 1. Replace the glint texture path with a subtle alternative of the same length
# 2. Zero out ALL glint-unique float values (scale, intensity, color)
#
# The glint-unique floats were identified by scanning the entire 2 MB block
# and finding every float value that appears ONLY within 300 bytes of a
# "Glint", "Round_", or "Scope_Glint" string.  These 17 byte patterns
# (appearing 4+ times each) are all glint-specific and zeroing them makes
# the glint particles have zero scale/intensity = completely invisible.

GLINT_BLOCK_NUMBER = 406
GLINT_TEXTURE_ORIGINAL = b'\\specialfx\\pfx\\glow\\pfx_glow_cross_a.tga'
GLINT_TEXTURE_REPLACEMENT = b'\\specialfx\\pfx\\heathaze\\pfx_heathaze.tga'

# All glint-unique float byte patterns (appear 4+ times, only near glint strings)
GLINT_FLOAT_PATTERNS = [
    bytes.fromhex('ca7b7e3f'),  # 0.9941 — 36x, Round_XXX color/intensity
    bytes.fromhex('cb7b7e3f'),  # 0.9941 — 36x, Round_XXX color/intensity
    bytes.fromhex('cc7b7e3f'),  # 0.9941 — 12x, Round_XXX color/intensity
    bytes.fromhex('c87b7e3f'),  # 0.9941 — 12x, Round_XXX color/intensity
    bytes.fromhex('8806553e'),  # 0.2080 — 4x,  Glint_XXX scale
    bytes.fromhex('185ee43e'),  # 0.4460 — 4x,  Glint_XXX scale
    bytes.fromhex('69a62d3f'),  # 0.6783 — 4x,  Glint_XXX scale
    bytes.fromhex('e2855e3f'),  # 0.8692 — 4x,  Glint_XXX scale
    bytes.fromhex('a1ab7b3f'),  # 0.9831 — 4x,  Glint_XXX scale
    bytes.fromhex('15ad6e3f'),  # 0.9323 — 4x,  Glint_XXX scale
    bytes.fromhex('c510003f'),  # 0.5003 — 4x,  Glint_XXX scale
    bytes.fromhex('7ea24a3e'),  # 0.1979 — 4x,  Round_XXX scale
    bytes.fromhex('dc49d83e'),  # 0.4224 — 4x,  Round_XXX scale
    bytes.fromhex('de43213f'),  # 0.6299 — 4x,  Round_XXX scale
    bytes.fromhex('60d4463f'),  # 0.7767 — 4x,  Round_XXX scale
    bytes.fromhex('7cb24f3f'),  # 0.8113 — 4x,  Round_XXX scale
    bytes.fromhex('4bd7f13e'),  # 0.4723 — 4x,  Round_XXX scale
]
GLINT_FLOAT_ZEROED = bytes.fromhex('00000000')  # 0.0 — invisible
GLINT_UNDO_SUFFIX = ".glint_undo.json"


def _find_base_asr_path(asrpatch_path: str) -> Optional[str]:
    """Derive the base common.asr path from the asrpatch path."""
    if not asrpatch_path:
        return None
    directory = os.path.dirname(asrpatch_path)
    base_path = os.path.join(directory, "common.asr")
    if os.path.isfile(base_path):
        return base_path
    return None


def _disable_glint_in_base_file(base_path: str) -> tuple[bool, str]:
    """Disable scope glint by modifying ZBB block 406 of common.asr.

    Returns (success, message).
    """
    with open(base_path, "rb") as f:
        raw = f.read()

    magic = raw[:8]
    if magic != b"AsuraZbb":
        return False, (
            f"Base file is not AsuraZbb format (got {magic!r}). "
            "Cannot safely modify."
        )

    tex_replacements = 0
    float_replacements = 0
    float_undo: list[list] = []

    def mutate(block_data: bytearray) -> None:
        nonlocal tex_replacements, float_replacements
        pos = 0
        while True:
            pos = block_data.find(GLINT_TEXTURE_ORIGINAL, pos)
            if pos < 0:
                break
            block_data[pos:pos + len(GLINT_TEXTURE_ORIGINAL)] = (
                GLINT_TEXTURE_REPLACEMENT)
            tex_replacements += 1
            pos += len(GLINT_TEXTURE_ORIGINAL)
        for pattern in GLINT_FLOAT_PATTERNS:
            pos = 0
            while True:
                pos = block_data.find(pattern, pos)
                if pos < 0:
                    break
                nearby = block_data[max(0, pos - 300):pos]
                if (b'Glint' in nearby or b'Round_' in nearby
                        or b'Scope_Glint' in nearby):
                    float_undo.append([pos, pattern.hex()])
                    block_data[pos:pos + 4] = GLINT_FLOAT_ZEROED
                    float_replacements += 1
                pos += 4

    try:
        out = rewrite_block(raw, GLINT_BLOCK_NUMBER, mutate)
    except Exception as exc:
        return False, f"Block {GLINT_BLOCK_NUMBER} rewrite failed: {exc}"

    if tex_replacements == 0 and float_replacements == 0:
        return False, (
            "No glint effect data found in block 406 of common.asr. "
            "The file may have already been modified or uses a different format."
        )

    err = validate_zbb(out)
    if err:
        return False, f"Refused to save — archive index would break ({err})."

    with open(base_path, "wb") as f:
        f.write(out)

    undo_path = base_path + GLINT_UNDO_SUFFIX
    try:
        with open(undo_path, "w", encoding="utf-8") as fh:
            json.dump({"texture": tex_replacements > 0, "floats": float_undo}, fh)
    except OSError as exc:
        return False, (
            "Glint was written but the undo map could not be saved "
            f"({exc}). Re-enable will not be able to restore block 406 "
            "in isolation."
        )

    return True, (
        f"Disabled scope glint — replaced {tex_replacements} texture "
        f"reference(s) and zeroed {float_replacements} float value(s) "
        f"across {len(GLINT_FLOAT_PATTERNS)} glint-unique patterns "
        f"in block {GLINT_BLOCK_NUMBER} (same compressed slot, later "
        f"blocks not shifted)."
    )


def _enable_glint_in_base_file(base_path: str) -> tuple[bool, str]:
    """Reverse a prior glint disable using the sidecar undo map.

    Only block 406 is rewritten — never copy common.asr.bak over the
    live file for re-enable (that would undo unrelated changes).
    """
    undo_path = base_path + GLINT_UNDO_SUFFIX
    if not os.path.isfile(undo_path):
        return False, (
            "No glint undo map (common.asr.glint_undo.json). "
            "Re-enable cannot restore only block 406. Use "
            "'Restore common.asr from .bak' if you want the whole "
            "archive rolled back, or verify game files in Steam."
        )
    try:
        with open(undo_path, "r", encoding="utf-8") as fh:
            undo = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        return False, f"Could not read glint undo map: {exc}"

    with open(base_path, "rb") as f:
        raw = f.read()
    if raw[:8] != b"AsuraZbb":
        return False, f"Base file is not AsuraZbb format (got {raw[:8]!r})."

    tex_restored = 0
    float_restored = 0

    def mutate(block_data: bytearray) -> None:
        nonlocal tex_restored, float_restored
        if undo.get("texture"):
            pos = 0
            while True:
                pos = block_data.find(GLINT_TEXTURE_REPLACEMENT, pos)
                if pos < 0:
                    break
                block_data[pos:pos + len(GLINT_TEXTURE_ORIGINAL)] = (
                    GLINT_TEXTURE_ORIGINAL)
                tex_restored += 1
                pos += len(GLINT_TEXTURE_ORIGINAL)
        for item in undo.get("floats") or []:
            try:
                off, hex_bytes = int(item[0]), str(item[1])
            except (TypeError, ValueError, IndexError):
                continue
            original = bytes.fromhex(hex_bytes)
            if off < 0 or off + 4 > len(block_data) or len(original) != 4:
                continue
            if block_data[off:off + 4] == GLINT_FLOAT_ZEROED:
                block_data[off:off + 4] = original
                float_restored += 1

    try:
        out = rewrite_block(raw, GLINT_BLOCK_NUMBER, mutate)
    except Exception as exc:
        return False, f"Block {GLINT_BLOCK_NUMBER} rewrite failed: {exc}"
    err = validate_zbb(out)
    if err:
        return False, f"Refused to save — archive index would break ({err})."
    with open(base_path, "wb") as f:
        f.write(out)
    try:
        os.remove(undo_path)
    except OSError:
        pass
    return True, (
        f"Re-enabled scope glint — restored {tex_restored} texture "
        f"reference(s) and {float_restored} float value(s) in block "
        f"{GLINT_BLOCK_NUMBER} only."
    )


def _navigate_to_block(raw: bytes, block_number: int) -> tuple[int, int]:
    """Navigate to a ZBB block; return (data_offset, comp_size)."""
    extra = raw[8:24]
    _, _, first_comp, _ = struct.unpack('<IIII', extra)

    pos = 24
    comp_size = first_comp

    for i in range(block_number):
        pos += comp_size
        if pos + 8 > len(raw):
            raise ValueError(f"Block {block_number} not found (file too short)")
        comp_size, _ = struct.unpack('<II', raw[pos:pos + 8])
        pos += 8

    return pos, comp_size


def _check_glint_status(base_path: str) -> str:
    """Return 'enabled', 'disabled', or 'unknown'."""
    try:
        with open(base_path, "rb") as f:
            raw = f.read()

        block_pos, block_comp = _navigate_to_block(raw, GLINT_BLOCK_NUMBER)
        block_data = zlib.decompress(
            raw[block_pos:block_pos + block_comp], 12)

        if GLINT_TEXTURE_ORIGINAL in block_data:
            return "enabled"
        if GLINT_TEXTURE_REPLACEMENT in block_data:
            return "disabled"
        return "unknown"
    except Exception:
        return "unknown"


class SniperTweaksPanel(QWidget):
    """Panel for sniper-specific tweaks: scope glint disable."""

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.asrpatch_path: str = ""
        self.base_asr_path: str = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(4, 4, 4, 4)
        scroll.setWidget(content)
        layout.addWidget(scroll)

        glint_group = QGroupBox("Disable Scope Glint")
        glint_layout = QVBoxLayout(glint_group)

        glint_info = QLabel(
            "Hides scope glint on all scoped weapons (writes "
            "<code>common.asr</code> block 406). Restart after applying. "
            "There is no equivalent in-game option."
        )
        glint_info.setWordWrap(True)
        glint_info.setStyleSheet(muted_style())
        glint_layout.addWidget(glint_info)

        detect_info = QLabel(
            "Sniper sight range is not a file field (no 500 m LOS value "
            "in common.asr). Use Custom Difficulty → Enemy Perceptiveness "
            "(hearing and vision) and Enemy Responsiveness (spot speed)."
        )
        detect_info.setWordWrap(True)
        detect_info.setStyleSheet(muted_style())
        glint_layout.addWidget(detect_info)

        self.glint_status_label = QLabel("No base file detected")
        self.glint_status_label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;")
        glint_layout.addWidget(self.glint_status_label)

        glint_btn_row = QHBoxLayout()
        self.disable_glint_btn = QPushButton("Disable Scope Glint")
        self.disable_glint_btn.setToolTip(
            "Modify common.asr to disable scope glint.\n"
            "A backup will be created automatically.")
        self.disable_glint_btn.setEnabled(False)
        self.disable_glint_btn.clicked.connect(self._disable_glint)
        glint_btn_row.addWidget(self.disable_glint_btn)

        self.enable_glint_btn = QPushButton("Re-enable Scope Glint")
        self.enable_glint_btn.setToolTip(
            "Restore block 406 only (glint). Does not roll back "
            "other common.asr edits.")
        self.enable_glint_btn.setEnabled(False)
        self.enable_glint_btn.clicked.connect(self._enable_glint)
        glint_btn_row.addWidget(self.enable_glint_btn)

        self.restore_asr_btn = QPushButton("Restore common.asr from .bak")
        self.restore_asr_btn.setToolTip(
            "Replace common.asr with a validated common.asr.bak. "
            "Refuses a damaged backup. Undoes glint and any other "
            "common.asr writes together.")
        self.restore_asr_btn.clicked.connect(self._restore_common_asr)
        glint_btn_row.addWidget(self.restore_asr_btn)
        glint_btn_row.addStretch()
        glint_layout.addLayout(glint_btn_row)

        content_layout.addWidget(glint_group)
        content_layout.addStretch()

    def set_asr_file(self, asr_file: AsrFile, asrpatch_path: str = ""):
        """Set the current ASR file and update the panel state."""
        self.asr_file = asr_file
        self.asrpatch_path = asrpatch_path
        self.base_asr_path = _find_base_asr_path(asrpatch_path)
        has_base = bool(self.base_asr_path)
        if has_base:
            self.restore_asr_btn.setEnabled(
                os.path.isfile(self.base_asr_path + ".bak"))
            self._refresh_glint_status()
        else:
            self.restore_asr_btn.setEnabled(False)
            self.glint_status_label.setText(
                "Base common.asr not found in the same directory")
            self.glint_status_label.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;")
            self.disable_glint_btn.setEnabled(False)
            self.enable_glint_btn.setEnabled(False)

    def _refresh_glint_status(self):
        if not self.base_asr_path or not os.path.isfile(self.base_asr_path):
            self.glint_status_label.setText("Base common.asr not found")
            self.glint_status_label.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;")
            self.disable_glint_btn.setEnabled(False)
            self.enable_glint_btn.setEnabled(False)
            return

        status = _check_glint_status(self.base_asr_path)
        can_undo = os.path.isfile(self.base_asr_path + GLINT_UNDO_SUFFIX)

        if status == "enabled":
            self.glint_status_label.setText(
                "Scope glint: ENABLED (default)")
            self.glint_status_label.setStyleSheet(
                f"color: {SUCCESS}; font-size: 13px; font-weight: 600;")
            self.disable_glint_btn.setEnabled(True)
            self.enable_glint_btn.setEnabled(False)
        elif status == "disabled":
            self.glint_status_label.setText(
                "Scope glint: DISABLED")
            self.glint_status_label.setStyleSheet(
                f"color: {WARNING}; font-size: 13px; font-weight: 600;")
            self.disable_glint_btn.setEnabled(False)
            self.enable_glint_btn.setEnabled(can_undo)
        else:
            self.glint_status_label.setText(
                "Scope glint status: unknown")
            self.glint_status_label.setStyleSheet(
                f"color: {TEXT_MUTED}; font-size: 13px; font-weight: 600;")
            self.disable_glint_btn.setEnabled(True)
            self.enable_glint_btn.setEnabled(can_undo)

    def _disable_glint(self):
        if not self.base_asr_path or not os.path.isfile(self.base_asr_path):
            QMessageBox.warning(
                self, "File Not Found",
                "Could not find common.asr in the same directory as "
                "the asrpatch file.")
            return

        reply = QMessageBox.question(
            self, "Disable Scope Glint",
            f"This will modify the base file:\n\n"
            f"  {self.base_asr_path}\n\n"
            f"({os.path.getsize(self.base_asr_path) / 1024 / 1024:.0f} MB)\n\n"
            f"Only block 406 is rewritten. A healthy .bak is created if "
            f"missing. Re-enable restores glint only.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        ok, bak_msg = ensure_backup(self.base_asr_path)
        if not ok:
            QMessageBox.warning(self, "Backup failed", bak_msg)
            return

        try:
            success, message = _disable_glint_in_base_file(self.base_asr_path)
            if success:
                QMessageBox.information(
                    self, "Glint Disabled", message)
            else:
                QMessageBox.warning(
                    self, "Operation Failed", message)
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to modify common.asr:\n{e}")
            restore_backup(self.base_asr_path)

        self._refresh_glint_status()

    def _restore_common_asr(self):
        if not self.base_asr_path:
            return
        bak = self.base_asr_path + ".bak"
        if not os.path.isfile(bak):
            QMessageBox.warning(
                self, "No backup",
                "common.asr.bak was not found next to common.asr.")
            return
        reply = QMessageBox.question(
            self, "Restore common.asr",
            "Replace common.asr with a validated common.asr.bak?\n"
            "This undoes glint and any other common.asr writes.\n"
            "A damaged backup is refused — verify game files in Steam "
            "instead of forcing a bad copy.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        ok, msg = restore_backup(self.base_asr_path)
        self._refresh_glint_status()
        if ok:
            QMessageBox.information(self, "Restored", msg + " Restart the game.")
        else:
            QMessageBox.critical(self, "Restore failed", msg)

    def _enable_glint(self):
        if not self.base_asr_path:
            return

        reply = QMessageBox.question(
            self, "Re-enable Scope Glint",
            "Restore scope glint in block 406 only?\n\n"
            "This does not copy common.asr.bak over the live file.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            success, message = _enable_glint_in_base_file(self.base_asr_path)
            if success:
                QMessageBox.information(self, "Glint Re-enabled", message)
            else:
                QMessageBox.warning(self, "Could not re-enable glint", message)
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"Failed to modify common.asr:\n{e}")

        self._refresh_glint_status()
