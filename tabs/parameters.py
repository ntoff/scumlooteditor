# tabs/parameters.py
import json
import os
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import (
    QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QHBoxLayout,
    QFrame, QLabel, QLineEdit, QPushButton, QScrollArea, QHeaderView,
    QStyledItemDelegate, QFileDialog, QMessageBox, QTextEdit,
    QDialog, QDialogButtonBox, QInputDialog, QCompleter, QListView,
    QAbstractItemView
)
from PyQt5.QtCore import Qt, QAbstractItemModel, QModelIndex, QStringListModel, QByteArray

from settings import SettingsManager


class ParametersEditor(QWidget):
    def __init__(self, parent=None, settings_manager=None):
        super().__init__(parent)
        self.data = None
        self.current_file_path = None
        self.last_folder = os.path.expanduser("~")
        self.filtered_items = []
        self.current_filtered_index = -1
        self.settings_manager = settings_manager or SettingsManager()

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

        self.save_button = QPushButton("Save")
        self.save_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.save_button.clicked.connect(self.save_file)

        button_layout.addWidget(self.open_button)
        button_layout.addWidget(self.save_button)

        button_frame.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        button_frame.setFixedHeight(40)

        filter_frame = QFrame(self)
        filter_frame.setFrameShape(QFrame.StyledPanel)
        filter_frame.setFrameShadow(QFrame.Raised)
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setAlignment(Qt.AlignLeft)

        filter_label = QLabel("Find ID:")
        self.filter_input = QLineEdit()
        self.filter_input.setMaxLength(50)
        self.filter_input.setMinimumWidth(200)
        self.filter_input.setMaximumWidth(200)
        self.filter_input.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        self.filter_input.textChanged.connect(self.filter_items)

        prev_button = QPushButton("Previous")
        prev_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        prev_button.clicked.connect(self.previous_match)

        next_button = QPushButton("Next")
        next_button.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        next_button.clicked.connect(self.next_match)

        self.counter_label = QLabel("0/0")
        self.counter_label.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        filter_layout.addWidget(prev_button)
        filter_layout.addWidget(next_button)
        filter_layout.addWidget(self.counter_label)

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
        if self.data and "Parameters" in self.data:
            for item in self.data["Parameters"]:
                tree_item = QTreeWidgetItem()
                tree_item.setText(0, str(item["Id"]))
                tree_item.setText(1, str(item["IsDisabledForSpawning"]).lower())
                tree_item.setText(2, str(item["AllowedLocations"]))
                tree_item.setText(3, str(item["CooldownPerSquadMemberMin"]))
                tree_item.setText(4, str(item["CooldownPerSquadMemberMax"]))
                tree_item.setText(5, str(item["CooldownGroup"]))
                tree_item.setText(6, str(item["Variations"]))
                tree_item.setText(7, str(item["ShouldOverrideInitialAndRandomUsage"]).lower())
                tree_item.setText(8, str(item["InitialUsageOverride"]))
                tree_item.setText(9, str(item["RandomUsageOverrideUsage"]))
                self.tree.addTopLevelItem(tree_item)

    def save_file(self):
        if not self.data:
            return

        items = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
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

        if column in [2, 6]:
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Edit {self.tree.headerItem().text(column)}")
            dialog.setModal(True)

            layout = QtWidgets.QVBoxLayout()

            text_edit = QTextEdit()
            text_edit.setPlainText(value)
            text_edit.setWordWrapMode(QtGui.QTextOption.WrapAnywhere)
            text_edit.setAcceptRichText(False)

            layout.addWidget(text_edit)

            button_layout = QtWidgets.QHBoxLayout()
            ok_button = QPushButton("OK")
            cancel_button = QPushButton("Cancel")

            ok_button.clicked.connect(dialog.accept)
            cancel_button.clicked.connect(dialog.reject)

            button_layout.addWidget(ok_button)
            button_layout.addWidget(cancel_button)

            layout.addLayout(button_layout)

            dialog.setLayout(layout)
            dialog.resize(500, 300)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                item.setText(column, text_edit.toPlainText())
        else:
            new_value, ok = QInputDialog.getText(self, "Edit Value", "Enter new value:", text=value)
            if ok:
                item.setText(column, new_value)

    def filter_items(self, text):
        filter_text = text.lower()

        self.filtered_items = [
            self.tree.topLevelItem(i)
            for i in range(self.tree.topLevelItemCount())
            if filter_text in self.tree.topLevelItem(i).text(0).lower()
        ]

        self.current_filtered_index = -1
        self.update_counter()

        self.tree.clearSelection()

        if self.filtered_items and filter_text:
            self.tree.itemSelectionChanged.disconnect(self.on_tree_select)

            self.tree.setCurrentItem(self.filtered_items[0])
            self.tree.scrollToItem(self.filtered_items[0], QAbstractItemView.PositionAtCenter)
            self.current_filtered_index = 0
            self.update_counter()

            self.tree.itemSelectionChanged.connect(self.on_tree_select)

    def update_counter(self):
        total_items = self.tree.topLevelItemCount()
        if self.filtered_items:
            self.counter_label.setText(f"{self.current_filtered_index + 1}/{len(self.filtered_items)}")
        else:
            self.counter_label.setText(f"0/{total_items}")

    def next_match(self):
        if not self.filtered_items:
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
        if not self.filtered_items:
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
