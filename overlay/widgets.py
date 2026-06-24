from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor


def _label(text: str, font_size: int = 14, bold: bool = False, color: str = "white") -> QLabel:
    lbl = QLabel(text)
    font = QFont("Consolas", font_size)
    font.setBold(bold)
    lbl.setFont(font)
    lbl.setStyleSheet(f"color: {color}; background: transparent;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


class DeltaWidget(QWidget):
    """Shows delta vs personal best: +0.234s (red) or -0.112s (green)."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        self.delta_label = _label("---", font_size=28, bold=True)
        layout.addWidget(self.delta_label)

    def update_delta(self, delta: float | None):
        if delta is None:
            self.delta_label.setText("---")
            self.delta_label.setStyleSheet("color: white; background: transparent;")
            return
        sign = "+" if delta >= 0 else ""
        color = "#ff4444" if delta >= 0 else "#44ff88"
        self.delta_label.setText(f"{sign}{delta:.3f}s")
        self.delta_label.setStyleSheet(f"color: {color}; background: transparent;")


class LapTimeWidget(QWidget):
    """Small current/best lap display in the corner."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(12)
        self.current_label = _label("0:00.000", font_size=11, color="#cccccc")
        self.best_label = _label("PB: --:--.---", font_size=11, color="#aaaaaa")
        layout.addWidget(self.current_label)
        layout.addWidget(self.best_label)

    def update(self, current: float | None, best: float | None):
        self.current_label.setText(_fmt_time(current))
        self.best_label.setText(f"PB: {_fmt_time(best)}")


class BrakeCueWidget(QWidget):
    """Shows BRAKE cue with distance hint when approaching a braking zone."""

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setVisible(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        self.cue_label = _label("BRAKE", font_size=18, bold=True, color="#ff8800")
        layout.addWidget(self.cue_label)

    def show_cue(self, text: str):
        self.cue_label.setText(text)
        self.setVisible(True)

    def hide_cue(self):
        self.setVisible(False)


def _fmt_time(seconds: float | None) -> str:
    if seconds is None or seconds <= 0:
        return "--:--.---"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:06.3f}"
