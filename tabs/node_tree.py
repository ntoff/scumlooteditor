# tabs/node_tree.py
import json
import sys
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QTreeView, QVBoxLayout, QHBoxLayout, QFrame, QPushButton,
    QFileDialog, QMessageBox, QFormLayout, QDialog, QDialogButtonBox,
    QLineEdit, QCompleter, QListView, QStyledItemDelegate, QComboBox,
    QMenu, QAction, QAbstractItemView, QSplitter, QLabel
)
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, QByteArray, QSize


class CompleterDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        text = index.data(Qt.DisplayRole)
        font_metrics = option.widget.fontMetrics() if hasattr(option, 'widget') and option.widget else QtGui.QFontMetrics(QtGui.QFont())
        width = font_metrics.boundingRect(text).width()
        return QSize(width, size.height())


class TreeItem:
    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.childItems = []
        self.itemData = data
        self.displayText = f"{data.get('Name', 'Root')} ({data.get('Rarity', '')})" if data.get('Rarity') else data.get('Name', 'Root')
        self.postSpawnAction = "\n".join(data.get("PostSpawnActions", [])) if isinstance(data.get("PostSpawnActions", None), list) else ""
        self.childrenMergeMode = data.get("ChildrenMergeMode", None)

    def appendChild(self, child):
        self.childItems.append(child)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):
        return len(self.childItems)

    def columnCount(self):
        return 3

    def data(self, column):
        if column == 0:
            return self.displayText
        elif column == 1:
            return self.postSpawnAction if self.postSpawnAction else ""
        elif column == 2:
            return self.childrenMergeMode if self.childrenMergeMode else ""
        return None

    def setData(self, column, value):
        if column == 0:
            self.itemData["Name"] = value
            self.displayText = f"{value} ({self.itemData.get('Rarity', '')})" if self.itemData.get('Rarity') else value
        elif column == 1:
            if value == "None":
                self.postSpawnAction = None
                if "PostSpawnActions" in self.itemData:
                    del self.itemData["PostSpawnActions"]
            else:
                self.postSpawnAction = value
                self.itemData["PostSpawnActions"] = [value.replace('\n', '\r\n')] if value else []
        elif column == 2:
            if value == "None":
                self.childrenMergeMode = None
                if "ChildrenMergeMode" in self.itemData:
                    del self.itemData["ChildrenMergeMode"]
            else:
                self.childrenMergeMode = value
                self.itemData["ChildrenMergeMode"] = value
        return True

    def parent(self):
        return self.parentItem

    def row(self):
        return self.parentItem.childItems.index(self) if self.parentItem else 0


class TreeModel(QAbstractItemModel):
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.rootItem = None
        self.headerLabels = ["Item Tree", "Post Spawn Actions", "Children Merge Mode"]
        if data is not None:
            self.setupModelData(data)

    def setupModelData(self, data):
        self.clear()
        self.rootItem = TreeItem({"Name": "Root"})
        self.populateTree(self.rootItem, data)

    def populateTree(self, parent, data):
        if isinstance(data, dict):
            item_data = {
                "Name": data.get("Name", ""),
                "Rarity": data.get("Rarity", ""),
                "PostSpawnActions": data.get("PostSpawnActions", []),
                "ChildrenMergeMode": data.get("ChildrenMergeMode")
            }
            tree_item = TreeItem(item_data, parent)
            parent.appendChild(tree_item)

            if "Children" in data:
                for child in data["Children"]:
                    self.populateTree(tree_item, child)

        elif isinstance(data, list):
            for item_data in data:
                self.populateTree(parent, item_data)

    def clear(self):
        self.beginResetModel()
        self.rootItem = None
        self.endResetModel()

    def index(self, row, column, parent=QModelIndex()):
        if not self.rootItem:
            return QModelIndex()

        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()

        if row < 0 or row >= parentItem.childCount() or column < 0 or column >= parentItem.columnCount():
            return QModelIndex()

        childItem = parentItem.child(row)
        if childItem:
            return self.createIndex(row, column, childItem)
        return QModelIndex()

    def indexFromItem(self, item):
        if not item or item == self.rootItem:
            return QModelIndex()
        parent = item.parent()
        row = parent.childItems.index(item) if parent else 0
        return self.createIndex(row, 0, item)

    def parent(self, index):
        if not index.isValid():
            return QModelIndex()

        parentItem = index.internalPointer().parent()
        if parentItem is None or parentItem == self.rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)

    def rowCount(self, parent=QModelIndex()):
        if not parent.isValid():
            parentItem = self.rootItem
        else:
            parentItem = parent.internalPointer()
        return parentItem.childCount() if parentItem else 0

    def columnCount(self, parent=QModelIndex()):
        return 3

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            if section < len(self.headerLabels):
                return self.headerLabels[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == Qt.DisplayRole:
            if index.column() == 2:
                return item.childrenMergeMode if item.childrenMergeMode else ""
            return item.data(index.column())
        return None

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        item = index.internalPointer()
        if item.setData(index.column(), value):
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            return True
        return False


class NodeTreeViewer(QWidget):
    NAME_COLUMN = 0
    ACTION_COLUMN = 1
    MERGE_MODE_COLUMN = 2
    MERGE_MODE_OPTIONS = ["None", "Replace", "UpdateOrAdd"]
    RARITIES = ["Abundant", "Common", "Uncommon", "Rare", "VeryRare", "ExtremelyRare"]
    DEFAULT_FILE_FILTER = "JSON Files (*.json);;All Files (*)"
    POST_SPAWN_ACTIONS = [
        "None",
        "AbandonedBunkerKeycard", "KillboxKeycard_Cargo", "KillboxKeycard_Sentry",
        "KillboxKeycard_Police", "KillboxKeycard_Radiation", "SetAmmoAmount_BigStash",
        "SetAmmoAmount_SmallStash", "SetCashAmount_BigStash", "SetCashAmount_MediumStash",
        "SetCashAmount_SmallStash", "SetClothesDirtiness_DeadPuppets", "SetClothesDirtiness_DirtyClothes",
        "SetClothesDirtiness_ResidentialClothes", "SetUsage_Max", "SetResourceAmount_CargoDropGasolineCanister"
    ]

    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.current_file = None
        self.last_folder = ""
        self.model = TreeModel()
        self.selected_item = None
        self.settings_manager = settings_manager or SettingsManager()

        self._initialize_ui()
        self._load_settings()

    def _show_error_message(self, title, message):
        print(f"{title}: {message}")
        QMessageBox.critical(self, title, message)

    def _initialize_ui(self):
        button_frame = QFrame(self)
        button_frame.setFrameShape(QFrame.StyledPanel)
        button_frame.setFrameShadow(QFrame.Raised)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setAlignment(Qt.AlignLeft)

        self.open_button = QPushButton("Open")
        self.open_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.open_button.clicked.connect(self._load_json_file)

        self.close_button = QPushButton("Close")
        self.close_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.close_button.clicked.connect(self._close_file)
        
        self.save_button = QPushButton("Save")
        self.save_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.save_button.clicked.connect(self._save_json_file)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.close_button)

        button_frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        button_frame.setFixedHeight(40)

        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setIndentation(15)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.header().setStretchLastSection(True)
        self.tree_view.header().setDefaultAlignment(Qt.AlignLeft)
        self.tree_view.setColumnWidth(0, 200)
        self.tree_view.setColumnWidth(1, 150)
        self.tree_view.setColumnWidth(2, 120)
        self.tree_view.doubleClicked.connect(self._on_item_double_clicked)
        self.tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu)

        layout = QVBoxLayout(self)
        layout.addWidget(button_frame)
        layout.addWidget(self.tree_view)
        layout.setStretch(1, 1)

    def _close_file(self):
        if not self.current_file:
            return

        self.model.clear()
        self.tree_view.expandAll()
        self.current_file = None

    def _load_settings(self):
        settings = self.settings_manager.load_settings('node_editor')
        self.last_folder = settings.get('last_folder', "")
        header = self.tree_view.header()
        column_widths = settings.get('column_widths', [])
        for i, width in enumerate(column_widths):
            if i < header.count():
                header.resizeSection(i, width)

    def _save_settings(self):
        header = self.tree_view.header()
        column_widths = [header.sectionSize(i) for i in range(header.count())]
        settings = {
            'last_folder': self.last_folder,
            'column_widths': column_widths
        }
        self.settings_manager.save_settings('node_editor', settings)

    def _load_json_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open JSON File", self.last_folder, self.DEFAULT_FILE_FILTER
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                self.model.setupModelData(data)
                self.tree_view.expandAll()
                self.current_file = file_path
                self.last_folder = os.path.dirname(file_path)
            except Exception as e:
                self._show_error_message("File Load Error", f"Failed to load JSON file: {e}")

    def _save_json_file(self):
        if not self.current_file:
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save JSON File", self.last_folder, self.DEFAULT_FILE_FILTER
            )
            if not file_path:
                return
        else:
            file_path = self.current_file

        try:
            data = self._collect_tree_data()
            with open(file_path, 'w', newline='') as f:
                json.dump(data, f, indent=4)
            self.current_file = file_path
            self.last_folder = os.path.dirname(file_path)
            #QMessageBox.information(self, "Success", "JSON file saved successfully.")
            self._save_settings()
        except Exception as e:
            self._show_error_message("File Save Error", f"Failed to save JSON file: {e}")

    def _collect_tree_data(self):
        if not self.model.rootItem or not self.model.rootItem.childCount():
            return []
        root_children = []
        for i in range(self.model.rowCount()):
            index = self.model.index(i, 0)
            item = index.internalPointer()
            child_data = self._collect_item_data(item)
            root_children.append(child_data)
        return root_children

    def _collect_item_data(self, item):
        name = item.itemData.get("Name", "")
        rarity = item.itemData.get("Rarity", "")
        actions = item.itemData.get("PostSpawnActions", [])
        merge_mode = item.itemData.get("ChildrenMergeMode")

        child_data = {"Name": name}
        if rarity:
            child_data["Rarity"] = rarity
        if actions:
            child_data["PostSpawnActions"] = actions
        if merge_mode:
            child_data["ChildrenMergeMode"] = merge_mode

        children_data = []
        for i in range(item.childCount()):
            child_index = self.model.index(i, 0, self.model.indexFromItem(item))
            child_item = child_index.internalPointer()
            children_data.append(self._collect_item_data(child_item))

        if children_data:
            child_data["Children"] = children_data

        return child_data

    def _show_context_menu(self, pos):
        index = self.tree_view.indexAt(pos)
        if not index.isValid():
            return

        item = index.internalPointer()
        menu = QMenu()

        add_child_action = QAction("Add Child Item", menu)
        add_child_action.triggered.connect(lambda: self._add_child_item(item))
        menu.addAction(add_child_action)

        menu.addSeparator()

        rarity_menu = menu.addMenu("Rarity")
        for rarity in self.RARITIES:
            action = QAction(rarity, rarity_menu)
            action.triggered.connect(lambda checked, r=rarity: self._change_rarity(item, r))
            rarity_menu.addAction(action)

        menu.addSeparator()

        merge_mode_menu = menu.addMenu("Merge Mode")
        for mode in self.MERGE_MODE_OPTIONS:
            action = QAction(mode, merge_mode_menu)
            action.triggered.connect(lambda checked, m=mode: self._change_merge_mode(item, m))
            merge_mode_menu.addAction(action)

        menu.addSeparator()

        post_spawn_menu = menu.addMenu("Post Spawn Action")
        for action in self.POST_SPAWN_ACTIONS:
            action_item = QAction(action, post_spawn_menu)
            action_item.triggered.connect(lambda checked, a=action: self._change_post_spawn_action(item, a))
            post_spawn_menu.addAction(action_item)

        menu.addSeparator()

        expand_all_action = QAction("Expand All", menu)
        expand_all_action.triggered.connect(self.tree_view.expandAll)
        menu.addAction(expand_all_action)

        collapse_all_action = QAction("Collapse All", menu)
        collapse_all_action.triggered.connect(self.tree_view.collapseAll)
        menu.addAction(collapse_all_action)

        menu.addSeparator()

        delete_action = QAction("Delete", menu)
        delete_action.triggered.connect(lambda: self._delete_item(item))
        menu.addAction(delete_action)

        menu.exec_(self.tree_view.viewport().mapToGlobal(pos))

    def _add_child_item(self, parent_item):
        dialog = QDialog(self)
        dialog.setWindowTitle("Add Child Item")
        layout = QFormLayout(dialog)

        parameters = self._load_parameters()

        name_edit = QLineEdit(dialog)
        name_edit.setPlaceholderText("Enter name...")
        name_completer = QCompleter(parameters)
        name_completer.setCaseSensitivity(Qt.CaseInsensitive)
        name_completer.setCompletionMode(QCompleter.PopupCompletion)
        name_completer.setFilterMode(Qt.MatchContains)
        name_edit.setCompleter(name_completer)

        name_popup = QListView()
        name_popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        name_popup.setWordWrap(False)
        name_popup.setMinimumWidth(300)
        name_completer.setPopup(name_popup)

        delegate = CompleterDelegate()
        name_popup.setItemDelegate(delegate)

        layout.addRow("Name:", name_edit)

        # ✅ Replace rarity QLineEdit with QComboBox
        rarity_combo = QComboBox()
        rarity_combo.addItems(self.RARITIES)
        # Optional: pre-select "Common" for convenience
        rarity_combo.setCurrentIndex(self.RARITIES.index("Common") if "Common" in self.RARITIES else 0)

        layout.addRow("Rarity:", rarity_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec_() == QDialog.Accepted:
            name = name_edit.text().strip()
            rarity = rarity_combo.currentText()  # ← now gets selected value

            if not name:
                QMessageBox.warning(self, "Invalid Input", "Name cannot be empty!")
                return

            child_data = {"Name": name}
            if rarity and rarity in self.RARITIES:  # ensure validity
                child_data["Rarity"] = rarity

            child_item = TreeItem(child_data, parent_item)
            parent_item.appendChild(child_item)

            parent_index = self.model.indexFromItem(parent_item)
            if parent_index.isValid():
                row = parent_item.childCount() - 1
                self.model.beginInsertRows(parent_index, row, row)
                self.model.endInsertRows()

    def _delete_item(self, item):
        parent = item.parent()
        if parent:
            row = item.row()
            self.model.beginRemoveRows(self.model.indexFromItem(parent), row, row)
            parent.childItems.remove(item)
            self.model.endRemoveRows()
        else:
            QMessageBox.information(self, "Cannot Delete", "Top-level items cannot be deleted.")

    def _change_rarity(self, item, rarity):
        item.itemData["Rarity"] = rarity
        if rarity:
            item.displayText = f"{item.itemData['Name']} ({rarity})"
        else:
            item.displayText = item.itemData['Name']

        parent_index = self.model.indexFromItem(item.parent()) if item.parent() else QModelIndex()
        row = item.row()
        index = self.model.createIndex(row, 0, item)
        self.model.dataChanged.emit(index, index)

    def _change_merge_mode(self, item, mode):
        if mode == "None":
            item.childrenMergeMode = None
            if "ChildrenMergeMode" in item.itemData:
                del item.itemData["ChildrenMergeMode"]
        elif mode in self.MERGE_MODE_OPTIONS:
            item.childrenMergeMode = mode
            item.itemData["ChildrenMergeMode"] = mode
        else:
            return

        row = item.row()
        parent_index = self.model.indexFromItem(item)

        top_left = self.model.createIndex(row, self.MERGE_MODE_COLUMN, item)
        bottom_right = self.model.createIndex(row, self.MERGE_MODE_COLUMN, item)
        self.model.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])

    def _change_post_spawn_action(self, item, action):
        if action == "None":
            if "PostSpawnActions" in item.itemData:
                del item.itemData["PostSpawnActions"]
            item.postSpawnAction = None
        else:
            item.itemData["PostSpawnActions"] = [action]
            item.postSpawnAction = action

        row = item.row()
        parent_index = self.model.indexFromItem(item) if item.parent() else QModelIndex()
        top_left = self.model.createIndex(row, self.ACTION_COLUMN, item)
        bottom_right = self.model.createIndex(row, self.ACTION_COLUMN, item)
        self.model.dataChanged.emit(top_left, bottom_right, [Qt.DisplayRole])

    def _on_item_double_clicked(self, index):
        if not index.isValid():
            return

        column = index.column()
        item = index.internalPointer()

        if column == self.MERGE_MODE_COLUMN:
            dialog = QDialog(self)
            dialog.setWindowTitle("Select ChildrenMergeMode")
            layout = QVBoxLayout(dialog)

            combo_box = QComboBox()
            combo_box.addItems(self.MERGE_MODE_OPTIONS)
            current_mode = item.childrenMergeMode
            if current_mode and current_mode in self.MERGE_MODE_OPTIONS:
                combo_box.setCurrentText(current_mode)
            else:
                combo_box.setCurrentText("None")

            layout.addWidget(QLabel("Select merge mode:"))
            layout.addWidget(combo_box)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                Qt.Horizontal, dialog)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec_() == QDialog.Accepted:
                selected_mode = combo_box.currentText()
                self._change_merge_mode(item, selected_mode)
                row = item.row()
                model_index = self.model.createIndex(row, self.MERGE_MODE_COLUMN, item)
                self.model.dataChanged.emit(model_index, model_index, [Qt.DisplayRole])

        elif column == self.ACTION_COLUMN:
            dialog = QDialog(self)
            dialog.setWindowTitle("Select Post Spawn Action")
            layout = QVBoxLayout(dialog)

            combo_box = QComboBox()
            combo_box.addItems(self.POST_SPAWN_ACTIONS)

            current_action = item.itemData.get("PostSpawnActions", [""])[0] if item.itemData.get("PostSpawnActions") else ""
            if current_action in self.POST_SPAWN_ACTIONS:
                combo_box.setCurrentText(current_action)
            else:
                combo_box.setCurrentText("None")

            layout.addWidget(QLabel("Select post spawn action:"))
            layout.addWidget(combo_box)

            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
                Qt.Horizontal, dialog)
            buttons.accepted.connect(dialog.accept)
            buttons.rejected.connect(dialog.reject)
            layout.addWidget(buttons)

            if dialog.exec_() == QDialog.Accepted:
                selected_action = combo_box.currentText()
                self._change_post_spawn_action(item, selected_action)
                row = item.row()
                model_index = self.model.createIndex(row, self.ACTION_COLUMN, item)
                self.model.dataChanged.emit(model_index, model_index, [Qt.DisplayRole])

    def _load_parameters(self):
        parameters = []
        try:
            main_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            params_path = os.path.join(main_dir, "parameters.json")
            with open(params_path, 'r') as f:
                data = json.load(f)
                parameters = [param["Id"] for param in data.get("Parameters", [])]
        except Exception as e:
            self._show_error_message("Parameters Error", f"Error loading parameters: {e}")
        return parameters

    def closeEvent(self, event):
        self._save_settings()
        event.accept()
