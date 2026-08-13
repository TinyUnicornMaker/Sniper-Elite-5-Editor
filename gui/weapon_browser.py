"""Weapon browser panel — categorized weapon selection with per-weapon tabs.

Replaces the old dropdown-based editors with a sidebar showing weapon
categories (Primary Rifles, Shotguns, Pistols, SMGs, Special) and a tabbed
detail view showing the selected weapon's stats, scopes, ammo, and
attachments — mirroring the in-game customization page.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTabWidget, QLabel,
    QPushButton, QComboBox, QMessageBox, QHeaderView,
)

from gui.theme import TEXT_MUTED, ACCENT, PLAYER_WEAPON, LEVEL_WEAPON
from gui.display_names import format_entity_label
from gui.property_editor import EntityPropertyEditor
from gui.weapon_mapping import (
    WEAPON_CATEGORIES, get_all_weapons_in_category,
    get_attachments_for_weapon,
    is_level_only_weapon, is_loadout_weapon, LEVEL_ONLY_STAT_SOURCES,
)
from asr import AsrFile

# Patch names with no stat block of their own (unlock / mesh variants).
# Edit the parent weapon instead.
_VARIANT_STUBS: dict[str, str] = {
    "G43_Kurz_Silenced": "G43",
    "M1911_Plus": "M1911",
    "Thompson_Plus": "Thompson",
    "Mk1_Welrod": "Welrod",
    "Mk2_Welrod": "Welrod",
}


class AttachmentTab(QWidget):
    """A tab showing a list of attachments with property editors.

    Contains a dropdown to select which attachment to edit, and an
    EntityPropertyEditor for the selected attachment.

    When the game stores multiple entity names for one UI attachment
    (weapon mesh variants, empty stubs), *aliases* maps the displayed
    representative → every entity that should receive the same writes.
    """

    modified = Signal()

    def __init__(self, prop_set: str = "attachment", parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.entity_names: list[str] = []
        self.aliases: dict[str, list[str]] = {}
        self.current_entity: str = ""
        self.prop_set = prop_set
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Attachment selector
        selector_layout = QHBoxLayout()
        self.combo = QComboBox()
        self.combo.setMinimumWidth(300)
        self.combo.currentIndexChanged.connect(
            lambda idx: self._on_entity_selected(self.combo.itemData(idx)))
        selector_layout.addWidget(QLabel("Select:"))
        selector_layout.addWidget(self.combo, 1)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setToolTip(
            "Revert this part to shipped vanilla values in the editor.\n"
            "Does not write the game files — Save (Ctrl+S) and restart "
            "the game for the change to apply in-game."
        )
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._reset_entity)
        selector_layout.addWidget(self.reset_btn)
        layout.addLayout(selector_layout)

        self.alias_label = QLabel("")
        self.alias_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 11px;")
        self.alias_label.setWordWrap(True)
        layout.addWidget(self.alias_label)

        # Property editor
        self.editor = EntityPropertyEditor(prop_set=self.prop_set)
        self.editor.modified.connect(self._on_editor_modified)
        layout.addWidget(self.editor)

    def set_asr_file(self, asr_file: AsrFile):
        self.asr_file = asr_file
        self.editor.set_asr_file(asr_file)
        self.combo.clear()
        self.entity_names = []
        self.aliases = {}
        self.current_entity = ""
        self.reset_btn.setEnabled(False)
        self.alias_label.setText("")

    def set_entities(
        self,
        entity_names: list[str],
        aliases: dict[str, list[str]] | None = None,
    ):
        """Populate the attachment dropdown with *entity_names*."""
        self.combo.blockSignals(True)
        self.combo.clear()
        self.entity_names = entity_names
        self.aliases = aliases or {}
        for name in entity_names:
            self.combo.addItem(format_entity_label(name), name)
        self.combo.blockSignals(False)

        if entity_names:
            self.combo.setCurrentIndex(0)
            self._on_entity_selected(entity_names[0])
        else:
            self.current_entity = ""
            self.reset_btn.setEnabled(False)
            self.alias_label.setText("")
            self.editor.load_entity("")

    def _alias_group(self, entity_name: str) -> list[str]:
        if entity_name in self.aliases:
            return list(self.aliases[entity_name])
        try:
            from gui.attachment_compat import get_aliases_for
            return get_aliases_for(entity_name)
        except Exception:
            return [entity_name]

    def _on_entity_selected(self, entity_name: str):
        if not entity_name:
            self.current_entity = ""
            self.reset_btn.setEnabled(False)
            self.alias_label.setText("")
            self.editor.load_entity("")
            return
        self.current_entity = entity_name
        self.reset_btn.setEnabled(True)
        group = self._alias_group(entity_name)
        if len(group) > 1:
            others = [n for n in group if n != entity_name]
            self.alias_label.setText(
                f"Linked entities (same values applied): {', '.join(others)}"
            )
        else:
            self.alias_label.setText("")
        self.editor.load_entity(entity_name)

    def _on_editor_modified(self):
        """Fan property writes out to every alias of the current attachment."""
        if self.asr_file and self.current_entity:
            group = self._alias_group(self.current_entity)
            if len(group) > 1:
                src = self.asr_file.entities.get(self.current_entity)
                if src is not None:
                    for other in group:
                        if other == self.current_entity:
                            continue
                        dst = self.asr_file.entities.get(other)
                        if dst is None:
                            continue
                        # Copy each property value by hash from source → dest
                        src_by_hash = {p.hash: p for p in src.properties}
                        for p in dst.properties:
                            if p.hash in src_by_hash:
                                try:
                                    p.value = src_by_hash[p.hash].value
                                except Exception:
                                    pass
        self.modified.emit()

    def _reset_entity(self):
        """Revert this attachment (+ aliases) to vanilla in memory only."""
        if not self.asr_file or not self.current_entity:
            return
        from gui.vanilla_defaults import reset_entity_to_defaults

        n = 0
        for name in self._alias_group(self.current_entity):
            n += reset_entity_to_defaults(self.asr_file, name)
        # Reload spins from body so UI matches memory
        self.editor.load_entity(self.current_entity)
        if n:
            self.modified.emit()

    def has_entities(self) -> bool:
        return len(self.entity_names) > 0


class WeaponBrowserPanel(QWidget):
    """Main weapon browser with sidebar categories and per-weapon tabs.

    Layout:
        +-------------------+------------------------------------+
        | Category sidebar  |  [Stats] [Scope] [Ammo] [Barrel]   |
        |  Primary Rifles   |                                    |
        |    > M.1903       |  (property editors for selected    |
        |    > Karabiner 98 |   tab)                             |
        |  Pistols          |                                    |
        |    > M1911        |                                    |
        |  SMGs             |                                    |
        |  Special Weapons  |                                    |
        +-------------------+------------------------------------+
    """

    modified = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.asr_file: Optional[AsrFile] = None
        self.current_weapon: str = ""
        self.current_category: str = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # ── Left: weapon category tree + colour key ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Weapons")
        self.tree.setUniformRowHeights(True)
        self.tree.setIndentation(16)
        self.tree.header().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setMinimumWidth(200)
        self.tree.setMaximumWidth(350)
        self.tree.itemClicked.connect(self._on_weapon_clicked)
        left_layout.addWidget(self.tree, 1)

        key = QHBoxLayout()
        key.setContentsMargins(4, 0, 4, 4)
        key.addWidget(self._legend_chip(PLAYER_WEAPON, "Loadout"))
        key.addWidget(self._legend_chip(LEVEL_WEAPON, "Level pickup"))
        key.addStretch()
        left_layout.addLayout(key)
        splitter.addWidget(left)

        # ── Right: per-weapon tabs ──
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 4, 4, 4)

        title_row = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        self.weapon_label = QLabel("Select a weapon")
        self.weapon_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {TEXT_MUTED};"
            f"padding: 2px 4px 0 4px;")
        title_col.addWidget(self.weapon_label)
        self.weapon_meta = QLabel("")
        self.weapon_meta.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px; padding: 0 4px 4px 4px;"
        )
        title_col.addWidget(self.weapon_meta)
        title_row.addLayout(title_col, 1)

        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setToolTip(
            "Revert this weapon and its listed attachments to shipped "
            "vanilla values in the editor.\n"
            "Does NOT write game files alone — you must Save (Ctrl+S) "
            "and fully restart Sniper Elite 5."
        )
        self.reset_btn.setEnabled(False)
        self.reset_btn.clicked.connect(self._reset_weapon)
        title_row.addWidget(self.reset_btn, 0, Qt.AlignmentFlag.AlignTop)
        right_layout.addLayout(title_row)

        self.level_only_notice = QLabel("")
        self.level_only_notice.setWordWrap(True)
        self.level_only_notice.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 12px; padding: 6px;"
            f"background: rgba(0,0,0,40); border-radius: 4px;"
        )
        self.level_only_notice.hide()
        right_layout.addWidget(self.level_only_notice)

        # Tab widget
        self.tabs = QTabWidget()
        right_layout.addWidget(self.tabs)

        # Create tabs
        self.stats_tab = EntityPropertyEditor(prop_set="weapon")
        self.stats_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.stats_tab, "Stats")

        self.scope_tab = AttachmentTab(prop_set="scope")
        self.scope_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.scope_tab, "Scope")

        self.ammo_tab = AttachmentTab(prop_set="ammo")
        self.ammo_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.ammo_tab, "Ammo")

        self.barrel_tab = AttachmentTab(prop_set="attachment")
        self.barrel_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.barrel_tab, "Barrel")

        self.suppressor_tab = AttachmentTab(prop_set="attachment")
        self.suppressor_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.suppressor_tab, "Suppressor")

        self.iron_tab = AttachmentTab(prop_set="attachment")
        self.iron_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.iron_tab, "Ironsight")

        self.stock_tab = AttachmentTab(prop_set="attachment")
        self.stock_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.stock_tab, "Stock")

        self.grip_tab = AttachmentTab(prop_set="attachment")
        self.grip_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.grip_tab, "Grip")

        self.muzzle_tab = AttachmentTab(prop_set="attachment")
        self.muzzle_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.muzzle_tab, "Muzzle")

        self.mechanism_tab = AttachmentTab(prop_set="attachment")
        self.mechanism_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.mechanism_tab, "Mechanism")

        self.receiver_tab = AttachmentTab(prop_set="attachment")
        self.receiver_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.receiver_tab, "Receiver")

        self.construction_tab = AttachmentTab(prop_set="attachment")
        self.construction_tab.modified.connect(self.modified.emit)
        self.tabs.addTab(self.construction_tab, "Construction")

        # Map attachment-type names (from weapon_mapping) → tab widgets
        # Shotguns: Muzzle includes chokes (as in-game); Receiver replaces Mechanism.
        self.tab_map = {
            "Scope":         self.scope_tab,
            "Magazine":      self.ammo_tab,  # Magazine = Ammo tab
            "Barrel":        self.barrel_tab,
            "Suppressor":    self.suppressor_tab,
            "Ironsight":     self.iron_tab,
            "Stock":         self.stock_tab,
            "Grip":          self.grip_tab,
            "Muzzle":        self.muzzle_tab,
            "Mechanism":     self.mechanism_tab,
            "Receiver":      self.receiver_tab,
            "Construction":  self.construction_tab,
        }

        self.satellite_host = QWidget()
        self.satellite_layout = QVBoxLayout(self.satellite_host)
        self.satellite_layout.setContentsMargins(0, 8, 0, 0)
        self.satellite_editors: list[EntityPropertyEditor] = []
        self.satellite_host.hide()
        right_layout.addWidget(self.satellite_host)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

    @staticmethod
    def _legend_chip(color: str, text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(
            f"color: {TEXT_MUTED}; font-size: 11px;"
            f"border-left: 8px solid {color}; padding-left: 5px;"
        )
        return label

    def set_asr_file(self, asr_file: AsrFile):
        self.asr_file = asr_file
        self.tree.clear()
        self.current_weapon = ""
        self.current_category = ""
        self.reset_btn.setEnabled(False)
        self.weapon_label.setText("Select a weapon")
        self.weapon_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {TEXT_MUTED};"
            f"padding: 2px 4px 0 4px;"
        )
        self.weapon_meta.setText("")
        self.level_only_notice.hide()
        self._clear_satellites()

        # Set ASR file on all tabs
        self.stats_tab.set_asr_file(asr_file)
        for tab in self.tab_map.values():
            tab.set_asr_file(asr_file)

        if not asr_file:
            return

        available = set(asr_file.entities.keys())

        # Populate tree with categories and weapons
        total = 0
        for cat_name, weapon_list in WEAPON_CATEGORIES:
            weapons = get_all_weapons_in_category(cat_name, available)
            if not weapons:
                continue

            cat_item = QTreeWidgetItem(
                self.tree, [f"{cat_name}  ·  {len(weapons)}"]
            )
            cat_item.setFlags(cat_item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            cat_item.setForeground(0, QBrush(QColor(ACCENT)))
            cat_item.setExpanded(True)
            cat_item.setData(0, Qt.ItemDataRole.UserRole, "category")

            for weapon in weapons:
                display = format_entity_label(weapon)
                w_item = QTreeWidgetItem(cat_item, [display])
                w_item.setData(0, Qt.ItemDataRole.UserRole, weapon)
                w_item.setData(1, Qt.ItemDataRole.UserRole, cat_name)
                self._style_weapon_item(w_item, weapon)
                total += 1

        # Auto-select first weapon
        first_cat = self.tree.topLevelItem(0)
        if first_cat:
            for i in range(first_cat.childCount()):
                child = first_cat.child(i)
                if child.data(0, Qt.ItemDataRole.UserRole) and \
                   child.data(0, Qt.ItemDataRole.UserRole) != "info":
                    self._on_weapon_clicked(child, 0)
                    break

    def _entity_is_stub(self, weapon_name: str) -> bool:
        if not self.asr_file:
            return True
        ent = self.asr_file.entities.get(weapon_name)
        if ent is None:
            return True
        return not any(p.name for p in ent.properties)

    def _style_weapon_item(self, item: QTreeWidgetItem, weapon: str) -> None:
        stub = self._entity_is_stub(weapon)
        if is_level_only_weapon(weapon):
            color = LEVEL_WEAPON
            role = "Level pickup — not in the loadout gunsmith"
        elif is_loadout_weapon(weapon):
            color = PLAYER_WEAPON
            role = "Player loadout / gunsmith"
        else:
            color = TEXT_MUTED
            role = "Weapon"
        if stub:
            item.setForeground(0, QBrush(QColor(TEXT_MUTED)))
            font = QFont(item.font(0))
            font.setItalic(True)
            item.setFont(0, font)
            tip = f"{role} (no stat block)\nInternal: {weapon}"
        else:
            item.setForeground(0, QBrush(QColor(color)))
            tip = f"{role}\nInternal: {weapon}"
        item.setToolTip(0, tip)

    def _on_weapon_clicked(self, item: QTreeWidgetItem, _column: int):
        weapon_name = item.data(0, Qt.ItemDataRole.UserRole)
        if not weapon_name or weapon_name in ("category", "info"):
            return

        category = item.data(1, Qt.ItemDataRole.UserRole)
        if not category:
            return

        self.current_weapon = weapon_name
        self.current_category = category
        self.reset_btn.setEnabled(True)

        display = format_entity_label(weapon_name)
        self.weapon_label.setText(display)
        if is_level_only_weapon(weapon_name):
            title_color = LEVEL_WEAPON
            role = "Level pickup"
        elif is_loadout_weapon(weapon_name):
            title_color = PLAYER_WEAPON
            role = "Loadout"
        else:
            title_color = TEXT_MUTED
            role = "Weapon"
        self.weapon_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {title_color};"
            f"padding: 2px 4px 0 4px;"
        )
        self.weapon_meta.setText(f"{role}  ·  {weapon_name}")
        self.weapon_meta.setStyleSheet(
            f"color: {title_color}; font-size: 11px; padding: 0 4px 4px 4px;"
        )

        # Load weapon stats
        self.stats_tab.load_entity(weapon_name)
        self._rebuild_satellites(weapon_name)

        stub = self._entity_is_stub(weapon_name)
        parent = _VARIANT_STUBS.get(weapon_name)
        if stub:
            parent_label = (
                format_entity_label(parent) if parent else "the parent gun"
            )
            self.level_only_notice.setText(
                f"This name is in the patch but has no stat block of its "
                f"own (and none in common.asr blocks 0–1). It is a variant "
                f"/ unlock stub — edit {parent_label} instead."
            )
            self.level_only_notice.show()
        elif is_level_only_weapon(weapon_name):
            self.level_only_notice.setText(
                "Level pickup — not in the loadout gunsmith, so there are "
                "no attachment tabs.\n"
                "Weapon MagazineCapacity is reserve / max carry, not "
                "rounds in the tube. Panzerfaust = 1 rocket (carry limit "
                "10). PzB 39 is single-load; 10 / 12 are pool sizes."
            )
            self.level_only_notice.show()
        else:
            self.level_only_notice.hide()

        if is_level_only_weapon(weapon_name) or stub:
            for i in range(self.tabs.count()):
                self.tabs.setTabVisible(i, self.tabs.tabText(i) == "Stats")
            self.tabs.setCurrentIndex(0)
            return

        # Load attachments
        available = set(self.asr_file.entities.keys()) if self.asr_file else set()
        attachments = get_attachments_for_weapon(weapon_name, category, available)
        try:
            from gui.attachment_compat import (
                get_aliases_for, _LAST_ALIASES, collapse_slots_by_display_name,
            )
            prop_counts = {
                n: len(self.asr_file.entities[n].properties)
                for n in available
                if self.asr_file and n in self.asr_file.entities
            }
            attachments = collapse_slots_by_display_name(attachments, prop_counts)
            aliases = dict(_LAST_ALIASES)
        except Exception:
            aliases = {}

        # Update each tab
        for tab_name, tab_widget in self.tab_map.items():
            entities = attachments.get(tab_name, [])
            # per-tab alias subset
            tab_aliases = {
                e: aliases.get(e, get_aliases_for(e) if aliases else [e])
                for e in entities
            }
            tab_widget.set_entities(entities, aliases=tab_aliases)

        # Show/hide tabs based on whether they have entities
        for i in range(self.tabs.count()):
            tab_text = self.tabs.tabText(i)
            if tab_text == "Stats":
                self.tabs.setTabVisible(i, True)
            elif tab_text == "Ammo":
                # Ammo tab is visible if there are magazines
                self.tabs.setTabVisible(i, self.ammo_tab.has_entities())
            else:
                tab_widget = self.tab_map.get(tab_text)
                if tab_widget:
                    self.tabs.setTabVisible(i, tab_widget.has_entities())

        # Switch to first visible tab
        for i in range(self.tabs.count()):
            if self.tabs.isTabVisible(i):
                self.tabs.setCurrentIndex(i)
                break

    def _clear_satellites(self):
        while self.satellite_layout.count():
            item = self.satellite_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.satellite_editors = []
        self.satellite_host.hide()

    def _rebuild_satellites(self, weapon_name: str):
        """Stack linked ammo/reserve editors under Stats for level-only guns."""
        self._clear_satellites()
        if not self.asr_file or not is_level_only_weapon(weapon_name):
            return
        sources = LEVEL_ONLY_STAT_SOURCES.get(weapon_name) or []
        available = self.asr_file.entities
        added = 0
        for entity_name, prop_set, heading in sources:
            if entity_name not in available:
                continue
            title = QLabel(heading)
            title.setWordWrap(True)
            title.setStyleSheet(
                f"font-weight: 600; color: {TEXT_MUTED}; padding-top: 4px;"
            )
            editor = EntityPropertyEditor(prop_set=prop_set)
            editor.set_asr_file(self.asr_file)
            editor.load_entity(entity_name)
            editor.modified.connect(self.modified.emit)
            self.satellite_layout.addWidget(title)
            self.satellite_layout.addWidget(editor)
            self.satellite_editors.append(editor)
            added += 1
        if added:
            self.satellite_host.show()

    def _reset_weapon(self):
        """Revert weapon + all listed attachments to vanilla (in memory only)."""
        if not self.current_weapon or not self.asr_file:
            return

        display = format_entity_label(self.current_weapon)
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            f"Revert <b>{display}</b> and every attachment listed on its "
            f"tabs to shipped vanilla values <b>in the editor</b>?<br><br>"
            f"This does <b>not</b> write the game files by itself. After "
            f"Reset you must:<br>"
            f"1. <b>Save</b> (Ctrl+S) to write <code>common.asr.asrpatch</code><br>"
            f"2. <b>Fully restart</b> Sniper Elite 5 "
            f"(weapon data loads at launch)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        from gui.vanilla_defaults import reset_entity_to_defaults

        names: list[str] = [self.current_weapon]
        available = set(self.asr_file.entities.keys())
        attachments = get_attachments_for_weapon(
            self.current_weapon, self.current_category, available
        )
        try:
            from gui.attachment_compat import get_aliases_for, _LAST_ALIASES
            aliases = dict(_LAST_ALIASES)
        except Exception:
            aliases = {}
            get_aliases_for = lambda e: [e]  # noqa: E731

        for ent_list in attachments.values():
            for ent in ent_list:
                group = aliases.get(ent) or get_aliases_for(ent)
                names.extend(group)

        for ent, _pset, _h in LEVEL_ONLY_STAT_SOURCES.get(
            self.current_weapon, []
        ):
            names.append(ent)

        # Unique, preserve order
        seen: set[str] = set()
        ordered: list[str] = []
        for n in names:
            if n not in seen and n in available:
                seen.add(n)
                ordered.append(n)

        total = 0
        for name in ordered:
            total += reset_entity_to_defaults(self.asr_file, name)

        # Refresh open editors so spinboxes match memory
        self.stats_tab.load_entity(self.current_weapon)
        self._rebuild_satellites(self.current_weapon)
        for tab in self.tab_map.values():
            if tab.current_entity:
                tab.editor.load_entity(tab.current_entity)

        if total:
            self.modified.emit()
            QMessageBox.information(
                self, "Reset in editor only",
                f"Reverted <b>{total}</b> properties across "
                f"<b>{len(ordered)}</b> entities in memory.<br><br>"
                f"<b>Save is now enabled</b> — press Ctrl+S, then fully "
                f"restart the game.<br>"
                f"Until you Save, Sniper Elite still uses the old "
                f"<code>common.asr.asrpatch</code> on disk.",
            )
        else:
            QMessageBox.information(
                self, "Nothing to reset",
                "No shipped vanilla values could be written (missing "
                "defaults or only read-only base properties).",
            )

    def get_all_entity_names(self) -> list[str]:
        """Return all entity names managed by this panel (for preset system)."""
        if not self.asr_file:
            return []
        available = set(self.asr_file.entities.keys())
        names = []
        for cat_name, _ in WEAPON_CATEGORIES:
            for weapon in get_all_weapons_in_category(cat_name, available):
                names.append(weapon)
                attachments = get_attachments_for_weapon(weapon, cat_name, available)
                for att_list in attachments.values():
                    names.extend(att_list)
                for ent, _pset, _h in LEVEL_ONLY_STAT_SOURCES.get(weapon, []):
                    if ent in available:
                        names.append(ent)
        return list(set(names))
