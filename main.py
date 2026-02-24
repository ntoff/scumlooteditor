# main.py
import sys
from PyQt5 import QtWidgets, QtGui, QtCore  # <-- Add QtCore import

from settings import SettingsManager
from tabs import ParametersEditor, NodeTreeViewer, SpawnerEditor


class TabbedApplication(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SCUM Loot Editor")
        self.setGeometry(100, 100, 1400, 900)
        self.setWindowState(QtCore.Qt.WindowMaximized)  # ✅ Correct way in PyQt5

        self.settings_manager = SettingsManager()

        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.init_tabs()
        self._load_shared_settings()

    def init_tabs(self):
        self.parameters_editor = ParametersEditor(self, self.settings_manager)
        self.tab_widget.addTab(self.parameters_editor, "Items")

        self.node_editor = NodeTreeViewer(self, self.settings_manager)
        self.tab_widget.addTab(self.node_editor, "Nodes")

        self.spawner_editor = SpawnerEditor(self, self.settings_manager)
        self.tab_widget.addTab(self.spawner_editor, "Spawners")

    def _load_shared_settings(self):
        settings = self.settings_manager.load_settings('main_window')
        geometry = settings.get('geometry')
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))

    def closeEvent(self, event):
        try:
            geometry = bytes(self.saveGeometry()).hex()
            settings = {
                'geometry': geometry
            }
            self.settings_manager.save_settings('main_window', settings)
        except Exception as e:
            print(f"Failed to save main window settings: {e}")

        self.parameters_editor.close()
        self.node_editor.close()
        self.spawner_editor.close()

        event.accept()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    palette = app.palette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(255, 255, 255))
    app.setPalette(palette)

    window = TabbedApplication()
    window.show()
    sys.exit(app.exec_())

