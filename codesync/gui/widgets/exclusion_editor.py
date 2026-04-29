from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit


class ExclusionEditorWidget(QWidget):
    """Multi-line editor for .gitignore-style exclusion patterns."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        lbl = QLabel("排除规则（每行一条，支持 .gitignore 语法）")
        lbl.setStyleSheet("font-size: 12px; color: #666;")
        layout.addWidget(lbl)

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText(".git/\n__pycache__/\n*.pyc\nnode_modules/")
        self._editor.setMinimumHeight(100)
        layout.addWidget(self._editor)

    def patterns(self) -> list[str]:
        return [line.strip() for line in self._editor.toPlainText().splitlines() if line.strip()]

    def set_patterns(self, patterns: list[str]) -> None:
        self._editor.setPlainText("\n".join(patterns))
