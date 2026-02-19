# tabs/spawner.py
import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QFrame, QPushButton, QFileDialog,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem, QComboBox,
    QGroupBox, QFormLayout, QSpinBox, QCheckBox, QScrollArea, QDialog,
    QDialogButtonBox, QLineEdit, QCompleter, QMenu, QAction, QHBoxLayout,
    QLabel
)
from PyQt5.QtCore import Qt, QStringListModel

from settings import SettingsManager


class SpawnerEditor(QWidget):
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.settings_manager = settings_manager or SettingsManager()

        self.current_data = None
        self.current_file_path = None
        self._loading_data = False
        self._last_used_folder = ""
        self._parameters_data = []

        self.init_ui()
        self.load_settings()

    def load_settings(self):
        settings = self.settings_manager.load_settings('spawner_editor')
        last_folder = settings.get("last_folder", "")
        if last_folder:
            self._last_used_folder = last_folder

        splitter_sizes = settings.get("splitter_sizes", [])
        if splitter_sizes and len(splitter_sizes) == 2:
            self.main_splitter.setSizes(splitter_sizes)

        top_splitter_sizes = settings.get("top_splitter_sizes", [])
        if top_splitter_sizes and len(top_splitter_sizes) == 2:
            self.top_splitter.setSizes(top_splitter_sizes)
        else:
            self.top_splitter.setSizes([300, 700])

    def save_settings(self):
        settings = {
            "last_folder": getattr(self, '_last_used_folder', ""),
            "splitter_sizes": self.main_splitter.sizes(),
            "top_splitter_sizes": self.top_splitter.sizes()
        }
        self.settings_manager.save_settings('spawner_editor', settings)

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        button_frame = QFrame(self)
        button_frame.setFrameShape(QFrame.StyledPanel)
        button_frame.setFrameShadow(QFrame.Raised)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignLeft)

        self.open_button = QPushButton("Open")
        self.open_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.open_button.clicked.connect(self.open_file)

        self.save_button = QPushButton("Save")
        self.save_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.save_button.clicked.connect(self.save_file)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.save_button)

        button_frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        button_frame.setFixedHeight(40)

        main_layout.addWidget(button_frame)

        self.main_splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(self.main_splitter)

        self.top_section = QWidget()
        self.top_layout = QVBoxLayout(self.top_section)
        self.init_top_section()
        self.main_splitter.addWidget(self.top_section)

        self.bottom_section = QWidget()
        self.bottom_layout = QVBoxLayout(self.bottom_section)
        self.init_bottom_section()
        self.main_splitter.addWidget(self.bottom_section)

        if self.main_splitter.sizes()[0] == 0 and self.main_splitter.sizes()[1] == 0:
            self.main_splitter.setSizes([400, 400])

    def init_top_section(self):
        nodes_main_layout = QVBoxLayout()
        self.top_layout.addLayout(nodes_main_layout)

        self.top_splitter = QSplitter(Qt.Horizontal)

        self.nodes_tree = QTreeWidget()
        self.nodes_tree.setHeaderLabels(["Rarity"])
        self.nodes_tree.header().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.nodes_tree.itemSelectionChanged.connect(self.on_node_selection_changed)
        self.nodes_tree.setMinimumWidth(200)
        self.nodes_tree.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Expanding)

        self.nodes_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.nodes_tree.customContextMenuRequested.connect(self.show_tree_context_menu)

        self.top_splitter.addWidget(self.nodes_tree)

        details_splitter = QSplitter(Qt.Horizontal)
        details_splitter.setSizes([500, 500])

        ids_container = QWidget()
        ids_layout = QVBoxLayout(ids_container)

        self.ids_label = QLabel("IDs:")
        self.ids_list_widget = QListWidget()
        ids_layout.addWidget(self.ids_label)
        ids_layout.addWidget(self.ids_list_widget)

        self.ids_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ids_list_widget.customContextMenuRequested.connect(self.show_ids_context_menu)

        self.rarity_combo = QComboBox()
        self.rarity_combo.addItems(self.get_rarity_list())
        self.rarity_combo.currentIndexChanged.connect(self.on_rarity_changed)
        self.rarity_label = QLabel("Rarity:")
        ids_layout.addWidget(self.rarity_label)
        ids_layout.addWidget(self.rarity_combo)

        details_splitter.addWidget(ids_container)

        post_spawn_container = QWidget()
        post_spawn_layout = QVBoxLayout(post_spawn_container)

        self.post_spawn_label = QLabel("Post Spawn Actions:")
        self.post_spawn_list = QListWidget()
        self.post_spawn_list.setSelectionMode(QListWidget.MultiSelection)
        self.post_spawn_list.itemChanged.connect(self.on_post_spawn_item_changed)
        post_spawn_layout.addWidget(self.post_spawn_label)
        post_spawn_layout.addWidget(self.post_spawn_list)

        self.post_spawn_actions_list = [
            "AbandonedBunkerKeycard",
            "KillboxKeycard_Cargo", "KillboxKeycard_Sentry",
            "KillboxKeycard_Police", "KillboxKeycard_Radiation",
            "SetAmmoAmount_BigStash", "SetAmmoAmount_SmallStash",
            "SetCashAmount_BigStash", "SetCashAmount_MediumStash",
            "SetCashAmount_SmallStash", "SetClothesDirtiness_DeadPuppets",
            "SetClothesDirtiness_DirtyClothes",
            "SetClothesDirtiness_ResidentialClothes",
            "SetResourceAmount_CargoDropGasolineCanister",
            "SetUsage_Max"
        ]
        for action in self.post_spawn_actions_list:
            item = QListWidgetItem(action)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.post_spawn_list.addItem(item)

        details_splitter.addWidget(post_spawn_container)

        self.top_splitter.addWidget(details_splitter)

        nodes_main_layout.addWidget(self.top_splitter)

    def show_ids_context_menu(self, pos):
        menu = QMenu(self)

        add_action = menu.addAction("Add ID...")
        delete_action = menu.addAction("Delete Selected")
        clear_action = menu.addAction("Clear All")

        action = menu.exec_(self.ids_list_widget.mapToGlobal(pos))

        if action == add_action:
            self.add_id_dialog()
        elif action == delete_action:
            current_items = self.ids_list_widget.selectedItems()
            for item in current_items:
                self.ids_list_widget.takeItem(self.ids_list_widget.row(item))
            self.on_ids_changed()
        elif action == clear_action:
            self.ids_list_widget.clear()
            self.on_ids_changed()

    def add_id_dialog(self):
        selected_items = self.nodes_tree.selectedItems()
        if not selected_items:
            return

        tree_item = selected_items[0]
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return

        node_type, index = data

        node_list = []
        if node_type == "Item":
            node_list = self.current_data.get("Items", [])
        elif node_type == "Node":
            node_list = self.current_data.get("Nodes", [])

        if index >= len(node_list):
            return

        node = node_list[index]

        if node_type == "Item":
            current_id = node.get("Id", "")
            if current_id:
                msg = "Items only support one ID. Adding another ID will replace the existing one."
                reply = QtWidgets.QMessageBox.warning(
                    self, "Multiple IDs Not Supported for Item", msg,
                    QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel, QtWidgets.QMessageBox.Ok
                )
                if reply == QtWidgets.QMessageBox.Cancel:
                    return

        dialog = QDialog(self)
        dialog.setWindowTitle("Add ID")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Enter ID:"))

        id_input = QLineEdit()
        if self._parameters_data:
            model = QStringListModel(self._parameters_data)
            completer = QCompleter(model, id_input)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            id_input.setCompleter(completer)

        layout.addWidget(id_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            new_id = id_input.text().strip()
            if new_id:
                existing_ids = [self.ids_list_widget.item(i).text() for i in range(self.ids_list_widget.count())]

                if node_type == "Item":
                    self.ids_list_widget.clear()
                    self.ids_list_widget.addItem(new_id)
                elif node_type == "Node":
                    if new_id not in existing_ids:
                        self.ids_list_widget.addItem(new_id)
                else:
                    return

                self.on_ids_changed()

    def init_bottom_section(self):
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setAlignment(Qt.AlignTop)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(6)

        self.general_group = QGroupBox("General")
        self.general_layout = QFormLayout()
        self.general_group.setLayout(self.general_layout)
        self.general_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self.general_layout.setContentsMargins(4, 4, 4, 4)
        self.general_layout.setSpacing(6)

        self.file_path_label = QLabel("None")
        
        self.probability_spin = QSpinBox()
        self.probability_spin.setRange(-1, 100)
        self.probability_spin.setSpecialValueText("Not Set (-1)")
        self.probability_spin.valueChanged.connect(self.on_property_changed)
        self.probability_spin.setFixedWidth(120)
        
        self.quantity_min_spin = QSpinBox()
        self.quantity_min_spin.setRange(0, 1000)
        self.quantity_min_spin.valueChanged.connect(self.on_property_changed)
        self.quantity_min_spin.setFixedWidth(60)
        
        self.quantity_max_spin = QSpinBox()
        self.quantity_max_spin.setRange(0, 1000)
        self.quantity_max_spin.valueChanged.connect(self.on_property_changed)
        self.quantity_max_spin.setFixedWidth(60)
        
        self.allow_duplicates_check = QCheckBox()
        self.allow_duplicates_check.stateChanged.connect(self.on_property_changed)
        self.allow_duplicates_check.setText("Allow Duplicates")
        
        self.filter_by_zone_check = QCheckBox()
        self.filter_by_zone_check.stateChanged.connect(self.on_property_changed)
        self.filter_by_zone_check.setText("Should Filter Items By Zone")
        
        self.apply_prob_mod_check = QCheckBox()
        self.apply_prob_mod_check.stateChanged.connect(self.on_property_changed)
        self.apply_prob_mod_check.setText("Should Apply Location Specific Probability Modifier")
        
        self.apply_dmg_mod_check = QCheckBox()
        self.apply_dmg_mod_check.stateChanged.connect(self.on_property_changed)
        self.apply_dmg_mod_check.setText("Should Apply Location Specific Damage Modifier")
        
        self.initial_damage_spin = QSpinBox()
        self.initial_damage_spin.setRange(0, 100)
        self.initial_damage_spin.valueChanged.connect(self.on_property_changed)
        self.initial_damage_spin.setFixedWidth(60)
        
        self.random_damage_spin = QSpinBox()
        self.random_damage_spin.setRange(0, 100)
        self.random_damage_spin.valueChanged.connect(self.on_property_changed)
        self.random_damage_spin.setFixedWidth(60)
        
        self.initial_usage_spin = QSpinBox()
        self.initial_usage_spin.setRange(0, 100)
        self.initial_usage_spin.valueChanged.connect(self.on_property_changed)
        self.initial_usage_spin.setFixedWidth(60)
        
        self.random_usage_spin = QSpinBox()
        self.random_usage_spin.setRange(0, 100)
        self.random_usage_spin.valueChanged.connect(self.on_property_changed)
        self.random_usage_spin.setFixedWidth(60)
        
        self.general_layout.addRow("File:", self.file_path_label)
        self.general_layout.addRow("Probability:", self.probability_spin)
        self.general_layout.addRow("Qty Min:", self.quantity_min_spin)
        self.general_layout.addRow("Qty Max:", self.quantity_max_spin)
        self.general_layout.addRow("Initial Damage:", self.initial_damage_spin)
        self.general_layout.addRow("Random Damage:", self.random_damage_spin)
        self.general_layout.addRow("Initial Usage:", self.initial_usage_spin)
        self.general_layout.addRow("Random Usage:", self.random_usage_spin)
        self.general_layout.addRow(self.allow_duplicates_check)
        self.general_layout.addRow(self.filter_by_zone_check)
        self.general_layout.addRow(self.apply_prob_mod_check)
        self.general_layout.addRow(self.apply_dmg_mod_check)
        scroll_layout.addWidget(self.general_group)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(scroll_content)
        self.bottom_layout.addWidget(self.scroll_area)

    def get_rarity_list(self):
        return [
            "Abundant", "Common", "Uncommon", "Rare",
            "VeryRare", "ExtremelyRare"
        ]

    def open_file(self):
        start_path = getattr(self, '_last_used_folder', os.getcwd())
        if not start_path or not os.path.isdir(start_path):
            start_path = os.getcwd()

        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", start_path, "JSON Files (*.json);;All Files (*)"
        )
        if file_path:
            self._last_used_folder = os.path.dirname(file_path)
            self.current_file_path = file_path
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.current_data = json.load(f)

                self.file_path_label.setText(os.path.basename(file_path))

                self.update_properties_ui()
                self.update_nodes_ui()
                self.update_post_spawn_actions_ui()

                root = self.nodes_tree.invisibleRootItem()
                items_child = root.child(0) if root.childCount() > 0 else None
                if items_child and items_child.childCount() > 0:
                    items_child.child(0).setSelected(True)
                    self.on_node_selection_changed()
                else:
                    nodes_child = root.child(1) if root.childCount() > 1 else None
                    if nodes_child and nodes_child.childCount() > 0:
                        nodes_child.child(0).setSelected(True)
                        self.on_node_selection_changed()

            except Exception as e:
                print(f"Error loading file: {e}")

    def save_file(self):
        if not self.current_file_path:
            start_path = getattr(self, '_last_used_folder', "")
            if not start_path or not os.path.isdir(start_path):
                start_path = QFileDialog.directory().absolutePath if hasattr(QFileDialog, 'directory') else ""

            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save JSON File", start_path, "JSON Files (*.json);;All Files (*)"
            )
            if file_path:
                self.current_file_path = file_path
                self._last_used_folder = os.path.dirname(file_path)
            else:
                return

        try:
            with open(self.current_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.current_data, f, indent=4)
            print(f"File saved: {self.current_file_path}")
            self.save_settings()
        except Exception as e:
            print(f"Error saving file: {e}")

    def update_properties_ui(self):
        if not self.current_data:
            return

        self._loading_data = True
        try:
            prob_val = self.current_data.get("Probability")
            self.probability_spin.setValue(-1 if prob_val is None else prob_val)
            self.quantity_min_spin.setValue(self.current_data.get("QuantityMin", 0))
            self.quantity_max_spin.setValue(self.current_data.get("QuantityMax", 0))
            self.allow_duplicates_check.setChecked(self.current_data.get("AllowDuplicates", False))
            self.filter_by_zone_check.setChecked(self.current_data.get("ShouldFilterItemsByZone", False))
            self.apply_prob_mod_check.setChecked(self.current_data.get("ShouldApplyLocationSpecificProbabilityModifier", False))
            self.apply_dmg_mod_check.setChecked(self.current_data.get("ShouldApplyLocationSpecificDamageModifier", False))
            self.initial_damage_spin.setValue(self.current_data.get("InitialDamage", 0))
            self.random_damage_spin.setValue(self.current_data.get("RandomDamage", 0))
            self.initial_usage_spin.setValue(self.current_data.get("InitialUsage", 0))
            self.random_usage_spin.setValue(self.current_data.get("RandomUsage", 0))
        finally:
            self._loading_data = False

    def update_nodes_ui(self):
        self.nodes_tree.clear()

        items_list = self.current_data.get("Items", [])
        nodes_list = self.current_data.get("Nodes", [])

        items_parent = QTreeWidgetItem(self.nodes_tree, ["Items"])
        nodes_parent = QTreeWidgetItem(self.nodes_tree, ["Nodes"])

        for item in items_list:
            rarity = item.get("Rarity", "Common")
            tree_item = QTreeWidgetItem([rarity])
            tree_item.setData(0, Qt.UserRole, ("Item", items_list.index(item)))
            items_parent.addChild(tree_item)

        for node in nodes_list:
            rarity = node.get("Rarity", "Common")
            tree_item = QTreeWidgetItem([rarity])
            tree_item.setData(0, Qt.UserRole, ("Node", nodes_list.index(node)))
            nodes_parent.addChild(tree_item)

        items_parent.setExpanded(True)
        nodes_parent.setExpanded(True)

    def show_tree_context_menu(self, pos):
        menu = QMenu(self)

        item = self.nodes_tree.itemAt(pos)
        if item is None:
            menu.addAction("Add New Item", self.add_item_dialog)
            menu.addAction("Add New Node", self.add_node_dialog)
        else:
            data = item.data(0, Qt.UserRole)
            if not data:
                return

            node_type, index = data

            menu.addAction("Remove", lambda: self.remove_selected_node(item))
            menu.addAction("Duplicate", lambda: self.duplicate_selected_node(item))

        action = menu.exec_(self.nodes_tree.mapToGlobal(pos))

    def add_item_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Item")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Rarity:"))
        rarity_combo = QComboBox()
        rarity_combo.addItems(self.get_rarity_list())
        layout.addWidget(rarity_combo)

        layout.addWidget(QLabel("ID:"))
        id_input = QLineEdit()
        if self._parameters_data:
            model = QStringListModel(self._parameters_data)
            completer = QCompleter(model, id_input)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            id_input.setCompleter(completer)
        layout.addWidget(id_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            rarity = rarity_combo.currentText()
            new_id = id_input.text().strip()
            if new_id:
                if "Items" not in self.current_data:
                    self.current_data["Items"] = []
                self.current_data["Items"].append({
                    "Rarity": rarity,
                    "Id": new_id
                })
                self.update_nodes_ui()
                self.reselect_tree_item("Item", len(self.current_data["Items"]) - 1)

    def add_node_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add New Node")
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("Rarity:"))
        rarity_combo = QComboBox()
        rarity_combo.addItems(self.get_rarity_list())
        layout.addWidget(rarity_combo)

        layout.addWidget(QLabel("IDs (comma-separated):"))
        ids_input = QLineEdit()
        if self._parameters_data:
            model = QStringListModel(self._parameters_data)
            completer = QCompleter(model, ids_input)
            completer.setFilterMode(Qt.MatchContains)
            completer.setCaseSensitivity(Qt.CaseInsensitive)
            ids_input.setCompleter(completer)
        layout.addWidget(ids_input)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec_() == QDialog.Accepted:
            rarity = rarity_combo.currentText()
            ids_text = ids_input.text().strip()
            new_ids = [x.strip() for x in ids_text.split(",") if x.strip()]

            if new_ids:
                if "Nodes" not in self.current_data:
                    self.current_data["Nodes"] = []
                self.current_data["Nodes"].append({
                    "Rarity": rarity,
                    "Ids": new_ids
                })
                self.update_nodes_ui()
                self.reselect_tree_item("Node", len(self.current_data["Nodes"]) - 1)

    def remove_selected_node(self, tree_item):
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return

        node_type, index = data

        if node_type == "Item":
            items = self.current_data.get("Items", [])
            if 0 <= index < len(items):
                items.pop(index)
        elif node_type == "Node":
            nodes = self.current_data.get("Nodes", [])
            if 0 <= index < len(nodes):
                nodes.pop(index)

        self.update_nodes_ui()
        self.ids_list_widget.clear()
        self.rarity_combo.clear()
        self.rarity_combo.addItems(self.get_rarity_list())

    def duplicate_selected_node(self, tree_item):
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return

        node_type, index = data

        if node_type == "Item":
            items = self.current_data.get("Items", [])
            if 0 <= index < len(items):
                item_copy = items[index].copy()
                items.append(item_copy)
        elif node_type == "Node":
            nodes = self.current_data.get("Nodes", [])
            if 0 <= index < len(nodes):
                node_copy = {
                    "Rarity": nodes[index].get("Rarity", "Common"),
                    "Ids": list(nodes[index].get("Ids", []))
                }
                nodes.append(node_copy)

        self.update_nodes_ui()
        self.reselect_tree_item(node_type, index + 1)

    def reselect_tree_item(self, node_type, index):
        self._loading_data = True
        try:
            root = self.nodes_tree.invisibleRootItem()
            for i in range(root.childCount()):
                parent = root.child(i)
                for j in range(parent.childCount()):
                    item = parent.child(j)
                    data = item.data(0, Qt.UserRole)
                    if data and data[0] == node_type and data[1] == index:
                        item.setSelected(True)
                        self.nodes_tree.scrollToItem(item)
                        self.on_node_selection_changed()
                        return
        finally:
            self._loading_data = False

    def on_node_selection_changed(self):
        selected_items = self.nodes_tree.selectedItems()
        if not selected_items:
            self.ids_list_widget.clear()
            self.rarity_combo.clear()
            self.rarity_combo.addItems(self.get_rarity_list())
            return

        tree_item = selected_items[0]
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return

        node_type, index = data

        node_list = []
        if node_type == "Item":
            node_list = self.current_data.get("Items", [])
        elif node_type == "Node":
            node_list = self.current_data.get("Nodes", [])

        if index >= len(node_list):
            return

        node = node_list[index]

        self.ids_list_widget.clear()
        if node_type == "Item":
            id_single = node.get("Id", "")
            if id_single:
                self.ids_list_widget.addItem(id_single)
        elif node_type == "Node":
            ids = node.get("Ids", [])
            for id_str in ids:
                self.ids_list_widget.addItem(id_str)

        rarity = node.get("Rarity", "Common")
        self.rarity_combo.clear()
        self.rarity_combo.addItems(self.get_rarity_list())
        index_ = self.rarity_combo.findText(rarity)
        if index_ >= 0:
            self.rarity_combo.setCurrentIndex(index_)
        else:
            self.rarity_combo.setCurrentText(rarity)

        self.update_post_spawn_actions_ui()

    def update_post_spawn_actions_ui(self):
        root_post_spawn_actions = self.current_data.get("PostSpawnActions", [])
        if root_post_spawn_actions is None:
            root_post_spawn_actions = []

        self.post_spawn_list.blockSignals(True)
        try:
            for i in range(self.post_spawn_list.count()):
                item = self.post_spawn_list.item(i)
                action_name = item.text()
                item.setCheckState(Qt.Checked if action_name in root_post_spawn_actions else Qt.Unchecked)
        finally:
            self.post_spawn_list.blockSignals(False)

    def on_ids_changed(self):
        selected_items = self.nodes_tree.selectedItems()
        if not selected_items or not self.current_data:
            return

        tree_item = selected_items[0]
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return

        node_type, index = data
        node_list = []
        if node_type == "Item":
            node_list = self.current_data.get("Items", [])
        elif node_type == "Node":
            node_list = self.current_data.get("Nodes", [])

        if index < len(node_list):
            node = node_list[index]
            new_ids = [self.ids_list_widget.item(i).text() for i in range(self.ids_list_widget.count())]

            if node_type == "Item" and len(new_ids) > 0:
                node["Id"] = new_ids[0]
            elif node_type == "Node":
                node["Ids"] = new_ids

    def on_property_changed(self, value=None):
        if not self.current_data or getattr(self, '_loading_data', False):
            return

        prob_val = self.probability_spin.value()
        if prob_val == -1:
            self.current_data.pop("Probability", None)
        else:
            self.current_data["Probability"] = prob_val

        self.current_data["QuantityMin"] = self.quantity_min_spin.value()
        self.current_data["QuantityMax"] = self.quantity_max_spin.value()
        self.current_data["AllowDuplicates"] = self.allow_duplicates_check.isChecked()
        self.current_data["ShouldFilterItemsByZone"] = self.filter_by_zone_check.isChecked()
        self.current_data["ShouldApplyLocationSpecificProbabilityModifier"] = self.apply_prob_mod_check.isChecked()
        self.current_data["ShouldApplyLocationSpecificDamageModifier"] = self.apply_dmg_mod_check.isChecked()
        self.current_data["InitialDamage"] = self.initial_damage_spin.value()
        self.current_data["RandomDamage"] = self.random_damage_spin.value()
        self.current_data["InitialUsage"] = self.initial_usage_spin.value()
        self.current_data["RandomUsage"] = self.random_usage_spin.value()

    def on_post_spawn_item_changed(self, item):
        if not self.current_data or self._loading_data:
            return

        action_name = item.text()
        is_checked = item.checkState() == Qt.Checked

        root_post_spawn_actions = self.current_data.get("PostSpawnActions", [])
        if root_post_spawn_actions is None:
            root_post_spawn_actions = []

        if is_checked:
            if action_name not in root_post_spawn_actions:
                root_post_spawn_actions.append(action_name)
        else:
            if action_name in root_post_spawn_actions:
                root_post_spawn_actions = [a for a in root_post_spawn_actions if a != action_name]

        self.current_data["PostSpawnActions"] = root_post_spawn_actions

    def on_rarity_changed(self, index):
        selected_items = self.nodes_tree.selectedItems()
        if not selected_items:
            return

        tree_item = selected_items[0]
        data = tree_item.data(0, Qt.UserRole)
        if not data:
            return

        node_type, idx = data
        node_list = []
        if node_type == "Item":
            node_list = self.current_data.get("Items", [])
        elif node_type == "Node":
            node_list = self.current_data.get("Nodes", [])

        if idx < len(node_list):
            new_rarity = self.rarity_combo.currentText()
            node_list[idx]["Rarity"] = new_rarity
            tree_item.setText(0, new_rarity)

    def closeEvent(self, event):
        self.save_settings()
        event.accept()
