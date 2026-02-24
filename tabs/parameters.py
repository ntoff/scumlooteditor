# tabs/parameters.py
import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QLineEdit, QPushButton, QScrollArea, QHeaderView,
    QStyledItemDelegate, QFileDialog, QMessageBox, QTextEdit,
    QDialog, QDialogButtonBox, QInputDialog, QCompleter, QListView,
    QAbstractItemView, QButtonGroup, QCheckBox, QFormLayout
)
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, QStringListModel, QByteArray

from settings import SettingsManager

class CooldownsDialog(QDialog):
    def __init__(self, current_min=None, current_max=None, current_initial=None, current_random=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adjust Cooldowns")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        # Inputs
        form_layout = QFormLayout()
        self.min_input = QLineEdit()
        self.max_input = QLineEdit()
        self.initial_input = QLineEdit()
        self.random_input = QLineEdit()
        
        # Add validators for all inputs
        validator = QtGui.QIntValidator(0, 999999)
        self.min_input.setValidator(validator)
        self.max_input.setValidator(validator)
        self.initial_input.setValidator(validator)
        self.random_input.setValidator(validator)

        # Set defaults if provided
        if current_min is not None:
            self.min_input.setText(str(current_min))
        if current_max is not None:
            self.max_input.setText(str(current_max))
        if current_initial is not None:
            self.initial_input.setText(str(current_initial))
        if current_random is not None:
            self.random_input.setText(str(current_random))

        form_layout.addRow("Cooldown Min:", self.min_input)
        form_layout.addRow("Cooldown Max:", self.max_input)
        form_layout.addRow("Initial Usage:", self.initial_input)
        form_layout.addRow("Random Usage:", self.random_input)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            orientation=Qt.Horizontal,
            parent=self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_values(self):
        return (
            int(self.min_input.text()) if self.min_input.text() else 0,
            int(self.max_input.text()) if self.max_input.text() else 0,
            int(self.initial_input.text()) if self.initial_input.text() else 0,
            int(self.random_input.text()) if self.random_input.text() else 0
        )

class ParametersEditor(QWidget):
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.data = None
        self.current_file_path = None
        self.last_folder = os.path.expanduser("~")
        self.filtered_items = []
        self.current_filtered_index = -1
        self.settings_manager = settings_manager or SettingsManager()
        self.all_items = []  # Store all QTreeWidgetItems for filtering

        self.initUI()
        self.load_settings()

    def initUI(self):
        button_frame = QFrame(self)
        button_frame.setFrameShape(QFrame.StyledPanel)
        button_frame.setFrameShadow(QFrame.Raised)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignLeft)

        self.open_button = QPushButton("Open")
        self.open_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.open_button.clicked.connect(self.open_file)

        self.close_button = QPushButton("Close")
        self.close_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.close_button.clicked.connect(self.close_file)
        
        self.save_button = QPushButton("Save")
        self.save_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.save_button.clicked.connect(self.save_file)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.close_button)

        button_frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        button_frame.setFixedHeight(40)

        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.StyledPanel)
        filter_frame.setFrameShadow(QFrame.Raised)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setAlignment(Qt.AlignLeft)

        # ID Filter
        filter_label = QLabel("Find ID:")
        self.filter_input = QLineEdit()
        self.filter_input.setMaxLength(50)
        self.filter_input.setMinimumWidth(200)
        self.filter_input.setMaximumWidth(200)
        self.filter_input.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.filter_input.textChanged.connect(self.filter_items)
        self.filter_input.setClearButtonEnabled(True)

        self.prev_button = QPushButton("Previous")
        self.prev_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.prev_button.clicked.connect(self.previous_match)
        self.prev_button.setEnabled(False)

        self.next_button = QPushButton("Next")
        self.next_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.next_button.clicked.connect(self.next_match)
        self.next_button.setEnabled(False)

        self.counter_label = QLabel("0/0")
        self.counter_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.counter_label.setMinimumWidth(60)
        #self.counter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Status Filter (Enabled / Disabled)
        status_label = QLabel("Show only:")
        self.enabled_checkbox = QCheckBox("Enabled")
        self.disabled_checkbox = QCheckBox("Disabled")

        # Allow unchecking the last button → supports "show all"
        self.enabled_checkbox.toggled.connect(self.on_enabled_toggled)
        self.disabled_checkbox.toggled.connect(self.on_disabled_toggled)

        # Initialize both unchecked (default)
        self.enabled_checkbox.setChecked(False)
        self.disabled_checkbox.setChecked(False)

        # Layout the ID filter part
        id_filter_layout = QHBoxLayout()
        id_filter_layout.addWidget(filter_label)
        id_filter_layout.addWidget(self.filter_input)
        id_filter_layout.addWidget(self.prev_button)
        id_filter_layout.addWidget(self.next_button)
        id_filter_layout.addWidget(self.counter_label)

        # Layout the status filter part (right-aligned)
        status_filter_layout = QHBoxLayout()
        status_filter_layout.addWidget(status_label)
        status_filter_layout.addWidget(self.enabled_checkbox)
        status_filter_layout.addWidget(self.disabled_checkbox)
        status_filter_layout.addStretch()  # Push to right

        # Combine into main filter layout
        filter_layout.addLayout(id_filter_layout)
        filter_layout.addSpacing(8)
        filter_layout.addLayout(status_filter_layout)

        filter_frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        filter_frame.setFixedHeight(50)

        tree_frame = QFrame(self)
        tree_layout = QVBoxLayout(tree_frame)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([
            "Id", "IsDisabledForSpawning", "AllowedLocations",
            "CooldownPerSquadMemberMin", "CooldownPerSquadMemberMax",
            "CooldownGroup", "Variations", "ShouldOverrideInitialAndRandomUsage",
            "InitialUsageOverride", "RandomUsageOverrideUsage"
        ])

        self.tree.setAlternatingRowColors(True)
        self.tree.setItemDelegate(QStyledItemDelegate())

        column_widths = [250, 60, 210, 180, 180, 200, 258, 220, 120, 180]
        for i, width in enumerate(column_widths):
            self.tree.setColumnWidth(i, width)

        header = self.tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.Interactive)

        self.tree.setFrameStyle(QFrame.NoFrame)
        self.tree.setIndentation(0)
        self.tree.setRootIsDecorated(False)
        self.tree.setUniformRowHeights(True)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.tree)

        tree_layout.addWidget(scroll_area)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(button_frame)
        main_layout.addWidget(filter_frame)
        main_layout.addWidget(tree_frame)
        main_layout.setStretch(2, 1)

        self.setLayout(main_layout)

        self.tree.itemSelectionChanged.connect(self.on_tree_select)
        self.tree.itemDoubleClicked.connect(self.on_double_click)
        # Enable context menu on tree widget
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.on_tree_context_menu)
        # Enable multi-selection (Shift/Ctrl + click)
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectRows)

    def load_settings(self):
        settings = self.settings_manager.load_settings('parameters_editor')

        self.last_folder = settings.get('last_folder', os.path.expanduser("~"))

        column_widths = settings.get('column_widths')
        if column_widths:
            self.load_column_widths(column_widths)

    def save_settings(self):
        settings = {
            'last_folder': getattr(self, 'last_folder', os.path.expanduser("~")),
            'column_widths': self.save_column_widths()
        }

        self.settings_manager.save_settings('parameters_editor', settings)

    def save_column_widths(self):
        header = self.tree.header()
        return [header.sectionSize(i) for i in range(header.count())]

    def load_column_widths(self, widths):
        header = self.tree.header()
        for i, width in enumerate(widths):
            if i < header.count():
                header.resizeSection(i, width)

    def load_file(self, file_path):
        try:
            with open(file_path, 'r') as f:
                self.current_file_path = file_path
                self.data = json.load(f)

            # 🔑 Reset status filter to "show all" (both unchecked)
            self.enabled_checkbox.setChecked(False)
            self.disabled_checkbox.setChecked(False)
            self.filter_input.clear()  # Optional: clear search too

            # 🔑 CRITICAL: Clear old item references before repopulating
            self.all_items.clear()
            self.filtered_items.clear()
            self.current_filtered_index = -1

            self.populate_tree()
            self.save_settings()
            self.update_counter()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {e}")

    def open_file(self):
        directory = getattr(self, 'last_folder', os.path.expanduser("~"))
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open JSON File", directory, "JSON files (*.json);;All files (*)"
        )
        if file_path:
            self.load_file(file_path)
            self.last_folder = os.path.dirname(file_path)
            self.save_settings()

    def populate_tree(self):
        self.tree.clear()
        self.all_items = []  # Reset list of all items
        if self.data and "Parameters" in self.data:
            for item in self.data["Parameters"]:
                tree_item = QTreeWidgetItem()
                tree_item.setText(0, str(item.get("Id", "")))
                tree_item.setText(1, str(item.get("IsDisabledForSpawning", False)).lower())
                tree_item.setText(2, str(item.get("AllowedLocations", [])))
                tree_item.setText(3, str(item.get("CooldownPerSquadMemberMin", 0)))
                tree_item.setText(4, str(item.get("CooldownPerSquadMemberMax", 0)))
                tree_item.setText(5, str(item.get("CooldownGroup", "")))
                tree_item.setText(6, str(item.get("Variations", [])))
                tree_item.setText(7, str(item.get("ShouldOverrideInitialAndRandomUsage", False)).lower())
                tree_item.setText(8, str(item.get("InitialUsageOverride", 0)))
                tree_item.setText(9, str(item.get("RandomUsageOverrideUsage", 0)))
                self.tree.addTopLevelItem(tree_item)
                self.all_items.append(tree_item)

    def save_file(self):
        if not self.data:
            return

        items = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.isHidden():
                continue  # Skip hidden items? Or preserve hidden? → Preserve hidden in original
            param = {
                "Id": item.text(0),
                "IsDisabledForSpawning": item.text(1).lower() == "true",
                "AllowedLocations": self.parse_list(item.text(2)),
                "CooldownPerSquadMemberMin": int(item.text(3)) if item.text(3) else 0,
                "CooldownPerSquadMemberMax": int(item.text(4)) if item.text(4) else 0,
                "CooldownGroup": item.text(5),
                "Variations": self.parse_list(item.text(6)),
                "ShouldOverrideInitialAndRandomUsage": item.text(7).lower() == "true",
                "InitialUsageOverride": int(item.text(8)) if item.text(8) else 0,
                "RandomUsageOverrideUsage": int(item.text(9)) if item.text(9) else 0
            }
            items.append(param)

        self.data["Parameters"] = items

        try:
            with open(self.current_file_path, 'w') as f:
                json.dump(self.data, f, indent=4)
            QMessageBox.information(self, "Success", "File saved successfully!")
            self.save_settings()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def close_file(self):
        if not self.current_file_path:
            return

        self.data = None
        self.current_file_path = None
        self.tree.clear()
        self.all_items = []  # Reset item list
        self.filter_input.clear()
        self.enabled_checkbox.setChecked(False)
        self.disabled_checkbox.setChecked(False)  # Ensure both unchecked on close
        self.update_counter()

    def parse_list(self, value):
        if value.startswith('[') and value.endswith(']'):
            items = value[1:-1].split(',')
            return [item.strip().strip("'\"") for item in items if item.strip()]
        return []

    def on_tree_select(self):
        pass

    def on_double_click(self, item, column):
        if column == 0:
            return

        if column in [1, 7]:
            item.setText(column, "false" if item.text(column) == "true" else "true")
            return

        value = item.text(column)

        # Handle AllowedLocations (column 2) with checkboxes
        if column == 2:
            dialog = QDialog(self)
            dialog.setWindowTitle("Edit AllowedLocations")
            dialog.setModal(True)

            layout = QVBoxLayout()
            dialog.setLayout(layout)

            # Static location list
            locations = ['Coastal', 'Continental', 'Mountain']

            # Scrollable container for checkboxes
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            content = QWidget()
            content_layout = QVBoxLayout()
            content_layout.setAlignment(Qt.AlignTop)
            content.setLayout(content_layout)

            # Parse current value and pre-check checkboxes
            current_locs = self.parse_list(value)

            for loc in locations:
                checkbox = QCheckBox(loc)
                checkbox.setChecked(loc in current_locs)
                content_layout.addWidget(checkbox)

            scroll.setWidget(content)

            # OK / Cancel buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                orientation=Qt.Horizontal,
                parent=dialog
            )
            button_box.accepted.connect(dialog.accept)
            button_box.rejected.connect(dialog.reject)

            layout.addWidget(scroll)
            layout.addWidget(button_box)

            dialog.resize(300, 200)

            if dialog.exec_() == QDialog.Accepted:
                # Build updated list of selected locations
                selected_locs = [
                    loc for loc in locations
                    if any(cb.text() == loc and cb.isChecked() for cb in content.findChildren(QCheckBox))
                ]
                item.setText(2, str(selected_locs))

        elif column == 6:
            # Variations: Keep original QTextEdit dialog
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit {self.tree.headerItem().text(column)}")
            dialog.setModal(True)

            layout = QVBoxLayout()
            text_edit = QTextEdit()
            text_edit.setPlainText(value)
            text_edit.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)
            text_edit.setAcceptRichText(False)

            layout.addWidget(text_edit)

            button_layout = QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")

            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)
            layout.addLayout(button_layout)

            dialog.setLayout(layout)
            dialog.resize(500, 300)

            if dialog.exec_() == QDialog.Accepted:
                item.setText(column, text_edit.toPlainText())

        else:
            new_value, ok = QInputDialog.getText(self, "Edit Value", "Enter new value:", text=value)
            if ok:
                item.setText(column, new_value)

    def edit_allowed_locations(self, items=None):
        """
        Edit AllowedLocations for a single item or multiple items.
        If multiple items are provided, shows a dialog that handles 'mixed' states.
        """
        # Default: single item (backward compatibility)
        if items is None:
            # For context menu, this shouldn't happen now, but keep for safety
            items = [self.tree.currentItem()]
        
        # Ensure items list is non-empty
        if not items:
            return

        # Collect all current location sets
        all_loc_sets = []
        for item in items:
            value = item.text(2)
            locs = set(self.parse_list(value))
            all_loc_sets.append(locs)

        # Determine if all are the same
        if len(set(map(frozenset, all_loc_sets))) == 1:
            # All same → use that value as default
            current_locs = all_loc_sets[0]
            is_mixed = False
        else:
            # Mixed state
            current_locs = set()  # or union of all? Better to show empty for clarity
            is_mixed = True

        dialog = QDialog(self)
        dialog.setWindowTitle("Edit AllowedLocations")
        dialog.setModal(True)

        layout = QVBoxLayout()
        dialog.setLayout(layout)

        if is_mixed:
            info = QLabel("⚠️ Selected items have *different* AllowedLocations. Changes apply to all.")
            info.setStyleSheet("color: orange;")
            layout.addWidget(info)

        # Static location list
        locations = ['Coastal', 'Continental', 'Mountain']

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setAlignment(Qt.AlignTop)
        content.setLayout(content_layout)

        # Create checkboxes
        checkboxes = {}
        for loc in locations:
            checkbox = QCheckBox(loc)
            checkbox.setChecked(loc in current_locs)
            checkboxes[loc] = checkbox
            content_layout.addWidget(checkbox)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        # OK / Cancel buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            orientation=Qt.Horizontal,
            parent=dialog
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        dialog.resize(300, 200)

        if dialog.exec_() == QDialog.Accepted:
            # Build final selected locations
            selected_locs = [
                loc for loc in locations
                if checkboxes[loc].isChecked()
            ]
            # Apply to all selected items
            for item in items:
                item.setText(2, str(selected_locs))

    def adjust_cooldowns_batch(self, items):
        """
        Adjusts CooldownPerSquadMemberMin, CooldownPerSquadMemberMax, 
        InitialUsageOverride, and RandomUsageOverrideUsage for multiple items.
        """
        if not items:
            return

        # Collect current values to detect if all items have same values
        current_mins = []
        current_maxs = []
        current_initials = []
        current_randoms = []
        
        for item in items:
            current_mins.append(int(item.text(3)) if item.text(3) else 0)
            current_maxs.append(int(item.text(4)) if item.text(4) else 0)
            current_initials.append(int(item.text(8)) if item.text(8) else 0)
            current_randoms.append(int(item.text(9)) if item.text(9) else 0)

        # Determine defaults for dialog (use first item's values if all are identical)
        mins_set = set(current_mins)
        maxs_set = set(current_maxs)
        initials_set = set(current_initials)
        randoms_set = set(current_randoms)
        
        default_min = list(mins_set)[0] if len(mins_set) == 1 else ""
        default_max = list(maxs_set)[0] if len(maxs_set) == 1 else ""
        default_initial = list(initials_set)[0] if len(initials_set) == 1 else ""
        default_random = list(randoms_set)[0] if len(randoms_set) == 1 else ""

        dialog = CooldownsDialog(default_min, default_max, default_initial, default_random, self)
        if dialog.exec_() == QDialog.Accepted:
            new_min, new_max, new_initial, new_random = dialog.get_values()
            for item in items:
                item.setText(3, str(new_min))
                item.setText(4, str(new_max))
                item.setText(8, str(new_initial))
                item.setText(9, str(new_random))

    def on_tree_context_menu(self, point):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            item = self.tree.itemAt(point)
            if not item:
                return
            selected_items = [item]

        menu = QtWidgets.QMenu(self)
        toggle_spawn_action = menu.addAction("Toggle Spawn")
        toggle_override_action = menu.addAction("Toggle Override")
        edit_locations_action = menu.addAction("Edit locations")
        adjust_cooldown_action = menu.addAction("Adjust cooldowns && Usages")

        action = menu.exec_(self.tree.viewport().mapToGlobal(point))
        if action is None:
            return

        # Apply selected action to ALL selected items in one batch
        if action == toggle_spawn_action:
            self.toggle_field_batch(selected_items, 1)
        elif action == toggle_override_action:
            self.toggle_field_batch(selected_items, 7)
        elif action == edit_locations_action:
            self.edit_allowed_locations(selected_items)
        elif action == adjust_cooldown_action:
            self.adjust_cooldowns_batch(selected_items)

    def toggle_field_batch(self, items, column):
        """
        Toggles a boolean field for multiple items at once.
        Assumes the column contains "true"/"false" strings.
        """
        for item in items:
            current = item.text(column)
            new_val = "false" if current.lower() == "true" else "true"
            item.setText(column, new_val)

    def on_enabled_toggled(self, checked):
        if checked:
            self.disabled_checkbox.setChecked(False)
        self.filter_items()

    def on_disabled_toggled(self, checked):
        if checked:
            self.enabled_checkbox.setChecked(False)
        self.filter_items()

    def filter_items(self):
        filter_text = self.filter_input.text().lower()

        show_enabled = self.enabled_checkbox.isChecked()
        show_disabled = self.disabled_checkbox.isChecked()
        show_all_statuses = not (show_enabled or show_disabled)

        # Hide all items first
        for item in self.all_items:
            id_match = filter_text in item.text(0).lower()
            is_disabled_str = item.text(1)
            is_disabled = is_disabled_str.lower() == "true"
            status_match = show_all_statuses or \
                        (show_enabled and not is_disabled) or \
                        (show_disabled and is_disabled)
            item.setHidden(not (id_match and status_match))

        # Rebuild filtered list (only visible items)
        self.filtered_items = [item for item in self.all_items if not item.isHidden()]

        # 🔑 CRITICAL: Buttons enabled ONLY if:
        #   1. Filter text is non-empty, AND
        #   2. At least one item matches
        has_match = bool(filter_text) and len(self.filtered_items) > 0
        self.prev_button.setEnabled(has_match)
        self.next_button.setEnabled(has_match)

        self.tree.clearSelection()
        self.current_filtered_index = -1

        if has_match:
            self.tree.itemSelectionChanged.disconnect(self.on_tree_select)
            self.tree.setCurrentItem(self.filtered_items[0])
            self.tree.scrollToItem(self.filtered_items[0], QAbstractItemView.PositionAtCenter)
            self.current_filtered_index = 0
            self.tree.itemSelectionChanged.connect(self.on_tree_select)

        self.update_counter()

    def update_counter(self):
        total_items = len(self.all_items)
        if self.filtered_items:
            self.counter_label.setText(f"{self.current_filtered_index + 1}/{len(self.filtered_items)}")
        else:
            self.counter_label.setText(f"0/{total_items}")

    def next_match(self):
        # 🔒 Only proceed if button is enabled AND there are filtered items
        if not self.next_button.isEnabled() or not self.filtered_items:
            return

        self.current_filtered_index = (self.current_filtered_index + 1) % len(self.filtered_items)
        item = self.filtered_items[self.current_filtered_index]

        self.tree.itemSelectionChanged.disconnect(self.on_tree_select)
        self.tree.clearSelection()
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item, QAbstractItemView.PositionAtCenter)
        self.update_counter()
        self.tree.itemSelectionChanged.connect(self.on_tree_select)

    def previous_match(self):
        # 🔒 Only proceed if button is enabled AND there are filtered items
        if not self.prev_button.isEnabled() or not self.filtered_items:
            return

        self.current_filtered_index = (self.current_filtered_index - 1) % len(self.filtered_items)
        item = self.filtered_items[self.current_filtered_index]

        self.tree.itemSelectionChanged.disconnect(self.on_tree_select)
        self.tree.clearSelection()
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item, QAbstractItemView.PositionAtCenter)
        self.update_counter()
        self.tree.itemSelectionChanged.connect(self.on_tree_select)

    def closeEvent(self, event):
        self.save_settings()
        event.accept()

