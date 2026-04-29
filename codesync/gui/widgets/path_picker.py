from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton, QFileDialog
from PyQt6.QtCore import pyqtSignal


class PathPickerWidget(QWidget):
    """A line edit + browse button for choosing a local directory."""
    path_changed = pyqtSignal(str)

    def __init__(self, placeholder: str = "选择本地目录…", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._edit = QLineEdit()
        self._edit.setPlaceholderText(placeholder)
        self._edit.textChanged.connect(self.path_changed)
        layout.addWidget(self._edit)

        btn = QPushButton("浏览…")
        btn.setFixedWidth(70)
        btn.clicked.connect(self._browse)
        layout.addWidget(btn)

    def _browse(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择本地目录", self._edit.text())
        if path:
            self._edit.setText(path)

    def path(self) -> str:
        return self._edit.text().strip()

    def set_path(self, path: str) -> None:
        self._edit.setText(path)
