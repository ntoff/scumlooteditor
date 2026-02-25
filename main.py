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
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self._drag_pos = None

        self.settings_manager = SettingsManager()

        # Create central widget container with vertical layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        layout = QtWidgets.QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Custom window control toolbar (min/max/close)
        self.window_toolbar = QtWidgets.QToolBar()
        self.window_toolbar.setMovable(False)
        self.window_toolbar.setFloatable(False)
        self.window_toolbar.setIconSize(QtCore.QSize(24, 24))
        self.window_toolbar.setStyleSheet("QToolBar { border: none; }")
        #self.window_toolbar.addSeparator()  # optional spacing
        self.window_toolbar.mousePressEvent = self._toolbar_mouse_press_event
        self.window_toolbar.mouseMoveEvent = self._toolbar_mouse_move_event
        self.window_toolbar.mouseReleaseEvent = self._toolbar_mouse_release_event

        # Theme toggle button (far left)
        self.theme_btn = QtWidgets.QToolButton()
        self.theme_btn.setToolTip("Toggle Light/Dark Mode")
        self.theme_btn.clicked.connect(self.toggle_theme)
        self.window_toolbar.addWidget(self.theme_btn)

        # Add a stretchable spacer to push buttons to the right
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.window_toolbar.addWidget(spacer)
        
        button_size = 32

        # Minimize button
        minimize_btn = QtWidgets.QToolButton()
        minimize_btn.setText("−")
        minimize_btn.setToolTip("Minimize")
        minimize_btn.setFixedSize(button_size, button_size)
        minimize_btn.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        minimize_btn.clicked.connect(self.showMinimized)
        self.window_toolbar.addWidget(minimize_btn)

        # Maximize/Restore button
        self.maximize_btn = QtWidgets.QToolButton()
        self.maximize_btn.setText("□")
        self.maximize_btn.setToolTip("Maximize")
        self.maximize_btn.setFixedSize(button_size, button_size)
        self.maximize_btn.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        self.maximize_btn.clicked.connect(self._toggle_maximize)
        self.window_toolbar.addWidget(self.maximize_btn)

        # Close button
        close_btn = QtWidgets.QToolButton()
        close_btn.setText("X")
        close_btn.setToolTip("Close")
        close_btn.setFixedSize(button_size, button_size)
        close_btn.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Bold))
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("QToolButton { color: #ff4d4d; }")  # red
        self.window_toolbar.addWidget(close_btn)

        layout.addWidget(self.window_toolbar)

        # Now add tab widget below toolbar
        self.tab_widget = QtWidgets.QTabWidget()
        layout.addWidget(self.tab_widget)

        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self._apply_theme()
        self.init_tabs()
        self._load_shared_settings()

    # Mouse event handlers for dragging
    def _toolbar_mouse_press_event(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()

    def _toolbar_mouse_move_event(self, event):
        # Prevent dragging when window is maximized
        if self.windowState() & QtCore.Qt.WindowMaximized:
            return
        if event.buttons() == QtCore.Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def _toolbar_mouse_release_event(self, event):
        self._drag_pos = None

    def _toggle_maximize(self):
        if self.windowState() & QtCore.Qt.WindowMaximized:
            self.showNormal()
            self.maximize_btn.setText("□")  # or "□" → "/pop-out" if desired
        else:
            self.showMaximized()
            self.maximize_btn.setText("❐")  # restore icon

    def _apply_theme(self):
        settings = self.settings_manager.load_settings('main_window')
        theme = settings.get('theme', 'dark')  # default to dark
        if theme == 'light':
            self.set_light_fusion()
        else:
            self.set_dark_fusion()
        self._update_theme_button(theme)

    def set_dark_fusion(self):
        """Apply Qt's Dark Fusion theme."""
        app = QtWidgets.QApplication.instance()
        app.setStyle("Fusion")
        palette = app.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(63, 63, 63))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(36, 36, 36))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(63, 63, 63))
        palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(63, 63, 63))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(66, 139, 202))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(66, 139, 202))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(0, 0, 0))
        app.setPalette(palette)

        # ✅ Force toolbar and buttons to update their palette
        self.window_toolbar.setPalette(palette)
        self.window_toolbar.style().polish(self.window_toolbar)
        # Also polish all child widgets (buttons) in toolbar
        for child in self.window_toolbar.findChildren(QtWidgets.QToolButton):
            child.setPalette(palette)
            child.style().polish(child)

    def set_light_fusion(self):
        """Apply Qt's Light Fusion theme."""
        app = QtWidgets.QApplication.instance()
        app.setStyle("Fusion")
        palette = app.palette()
        palette.setColor(QtGui.QPalette.Window, QtGui.QColor(239, 239, 239))
        palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(0, 0, 0))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(239, 239, 239))
        palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(0, 0, 0))
        palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(0, 0, 0))
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor(0, 0, 0))
        palette.setColor(QtGui.QPalette.Button, QtGui.QColor(239, 239, 239))
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(0, 0, 0))
        palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 255, 255))
        palette.setColor(QtGui.QPalette.Link, QtGui.QColor(0, 0, 255))
        palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(59, 121, 197))
        palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(255, 255, 255))
        app.setPalette(palette)

        # ✅ Force toolbar and buttons to update their palette
        self.window_toolbar.setPalette(palette)
        self.window_toolbar.style().polish(self.window_toolbar)
        for child in self.window_toolbar.findChildren(QtWidgets.QToolButton):
            child.setPalette(palette)
            child.style().polish(child)

    def toggle_theme(self):
        """Toggle between light and dark Fusion themes."""
        app = QtWidgets.QApplication.instance()
        current = self._get_current_theme()
        if current == 'dark':
            self.set_light_fusion()
            self.settings_manager.save_settings('main_window', {'theme': 'light'})
            self._update_theme_button('light')
        else:
            self.set_dark_fusion()
            self.settings_manager.save_settings('main_window', {'theme': 'dark'})
            self._update_theme_button('dark')

    def _get_current_theme(self):
        # Simple heuristic: check window color brightness
        app = QtWidgets.QApplication.instance()
        color = app.palette().color(QtGui.QPalette.Window)
        brightness = (color.red() + color.green() + color.blue()) / 3
        return 'light' if brightness > 128 else 'dark'

    def _update_theme_button(self, theme):
        """Update theme toggle button icon."""
        if theme == 'light':
            # User is in light mode → click to switch to dark
            self.theme_btn.setText("🌙")
            self.theme_btn.setToolTip("Switch to Dark Fusion Mode")
        else:
            # User is in dark mode → click to switch to light
            self.theme_btn.setText("☀️")
            self.theme_btn.setToolTip("Switch to Light Fusion Mode")

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
        was_maximized = settings.get('was_maximized', False)  # ← Save max state
        if geometry:
            self.restoreGeometry(bytes.fromhex(geometry))
            if was_maximized:
                self.showMaximized()
                self.maximize_btn.setText("❐")  # Show restore icon after restore
            else:
                self.maximize_btn.setText("□")  # Show maximize icon

    def closeEvent(self, event):
        try:
            geometry = bytes(self.saveGeometry()).hex()
            was_maximized = bool(self.windowState() & QtCore.Qt.WindowMaximized)
            settings = {
                'geometry': geometry,
                'was_maximized': was_maximized
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

    window = TabbedApplication()
    window.show()
    sys.exit(app.exec_())

