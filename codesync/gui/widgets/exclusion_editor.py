from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QMenu,
)
from PyQt6.QtCore import Qt

# Preset pattern groups
_PRESETS: dict[str, list[str]] = {
    "AI/ML 通用（数据集、模型权重）": [
        "*.h5", "*.hdf5", "*.pkl", "*.pickle",
        "*.pt", "*.pth", "*.ckpt", "*.safetensors",
        "*.bin", "*.onnx", "*.tflite", "*.pb",
        "*.npy", "*.npz", "*.parquet", "*.arrow",
        "data/", "datasets/", "checkpoints/", "weights/",
    ],
    "Python 项目": [
        ".git/", "__pycache__/", "*.pyc", "*.pyo", "*.pyd",
        ".venv/", "venv/", ".env", "*.egg-info/", "dist/", "build/",
        ".pytest_cache/", ".mypy_cache/", ".ruff_cache/",
    ],
    "AscendC 算子开发": [
        "*.o", "*.so", "*.a", "*.d",
        "build/", "output/", "kernel_meta/",
        "*.json.bak", "ascend_work_path/",
        "*.dump", "*.npu_log",
    ],
    "Node.js 项目": [
        "node_modules/", "dist/", ".next/", ".nuxt/",
        "*.log", "npm-debug.log*", "yarn-debug.log*",
    ],
    "常见大文件格式": [
        "*.zip", "*.tar", "*.gz", "*.bz2", "*.xz", "*.7z",
        "*.iso", "*.img", "*.vmdk",
        "*.mp4", "*.avi", "*.mkv", "*.mov",
    ],
}


class ExclusionEditorWidget(QWidget):
    """Multi-line editor for .gitignore-style exclusion patterns with preset shortcuts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QHBoxLayout()
        lbl = QLabel("排除规则（每行一条，支持 .gitignore 语法）")
        lbl.setStyleSheet("font-size: 12px; color: #666;")
        header.addWidget(lbl)
        header.addStretch()

        preset_btn = QPushButton("＋ 预置")
        preset_btn.setFixedWidth(70)
        preset_btn.setToolTip("选择预置规则快速添加")
        preset_btn.clicked.connect(self._show_presets)
        header.addWidget(preset_btn)

        clear_btn = QPushButton("清空")
        clear_btn.setFixedWidth(50)
        clear_btn.clicked.connect(self._editor.clear if hasattr(self, "_editor") else lambda: None)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText(".git/\n__pycache__/\n*.pyc\nnode_modules/")
        self._editor.setMinimumHeight(100)
        layout.addWidget(self._editor)

        # Wire clear button now that _editor exists
        clear_btn.clicked.disconnect()
        clear_btn.clicked.connect(self._editor.clear)

    def _show_presets(self) -> None:
        menu = QMenu(self)
        for name, patterns in _PRESETS.items():
            action = menu.addAction(name)
            action.setData(patterns)
        chosen = menu.exec(self.sender().mapToGlobal(  # type: ignore[arg-type]
            self.sender().rect().bottomLeft()  # type: ignore[union-attr]
        ))
        if chosen and chosen.data():
            self._add_patterns(chosen.data())

    def _add_patterns(self, new_patterns: list[str]) -> None:
        existing = set(self.patterns())
        to_add = [p for p in new_patterns if p not in existing]
        if to_add:
            current = self._editor.toPlainText().rstrip()
            sep = "\n" if current else ""
            self._editor.setPlainText(current + sep + "\n".join(to_add))

    def patterns(self) -> list[str]:
        return [line.strip() for line in self._editor.toPlainText().splitlines() if line.strip()]

    def set_patterns(self, patterns: list[str]) -> None:
        self._editor.setPlainText("\n".join(patterns))
