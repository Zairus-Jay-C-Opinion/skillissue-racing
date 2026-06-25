"""
HUD overlay widgets for Skill Issue Racing.

PillHUD       — horizontal pill: lap time | delta vs PB | coaching cue
SectorStrip   — three colored bars for S1/S2/S3 progress
StatusWindow  — 320×240 mini agent activity log
push_event()  — thread-safe; appends to shared _event_log deque
"""

from collections import deque
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import (
    QFont, QPainter, QColor, QPainterPath, QBrush, QPen,
)

# ── Colors ─────────────────────────────────────────────────────────────────────
C_BG_PILL = QColor(10, 10, 15, 192)   # semi-transparent dark
C_BG_WIN  = QColor(10, 10, 15, 228)   # slightly more opaque for windows
C_BORDER  = QColor(255, 255, 255, 25)
C_TEAL    = QColor(0, 212, 170)        # delta negative / sector done
C_RED     = QColor(239, 68, 68)        # delta positive (slower)
C_ORANGE  = QColor(245, 166, 35)       # ACT coaching cue
C_GRAY    = QColor(136, 136, 153)      # text-secondary
C_DIM_SEC = QColor(67, 74, 90)         # sector pending


def _fmt_time(seconds) -> str:
    if seconds is None or seconds <= 0:
        return "--:--.---"
    mins = int(seconds // 60)
    secs = seconds % 60
    return f"{mins}:{secs:06.3f}"


# ── Shared event log ────────────────────────────────────────────────────────────
_event_log: deque = deque(maxlen=50)


def push_event(message: str):
    """Append a timestamped line to the agent activity log. Thread-safe."""
    ts = datetime.now().strftime("%H:%M")
    _event_log.appendleft(f"{ts}  {message}")


# ── PillHUD ─────────────────────────────────────────────────────────────────────
class PillHUD(QWidget):
    """The main floating pill: [LAP | VS PB delta | ACT coaching]"""

    W, H, R = 420, 80, 24

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)

        row = QHBoxLayout(self)
        row.setContentsMargins(24, 0, 24, 0)
        row.setSpacing(0)

        left,  self._lap_val   = self._col("LAP",   "--:--.---", Qt.AlignmentFlag.AlignLeft,   18)
        mid,   self._delta_val = self._col("VS PB",  "---",      Qt.AlignmentFlag.AlignHCenter, 24, bold=True, c=C_TEAL)
        right, self._act_val   = self._col("ACT",   "---",      Qt.AlignmentFlag.AlignRight,   14, c=C_ORANGE)

        row.addWidget(left, 1)
        row.addWidget(mid, 2)
        row.addWidget(right, 1)

    def _col(self, header, value, align, size, bold=False, c=None):
        w = QWidget()
        w.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        col = QVBoxLayout(w)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(3)
        col.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        hdr = QLabel(header)
        hdr.setFont(QFont("Consolas", 7, QFont.Weight.Medium))
        hdr.setStyleSheet("color: #888899; background: transparent; letter-spacing: 2px;")
        hdr.setAlignment(align)

        val = QLabel(value)
        val.setFont(QFont("Consolas", size, QFont.Weight.Bold if bold else QFont.Weight.Medium))
        hex_c = c.name() if c else "#ffffff"
        val.setStyleSheet(f"color: {hex_c}; background: transparent;")
        val.setAlignment(align)

        col.addWidget(hdr)
        col.addWidget(val)
        return w, val

    def set_unlocked_hint(self, unlocked: bool):
        """Show an orange border when the overlay is in drag-to-reposition mode."""
        self._unlocked = unlocked
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.W, self.H, self.R, self.R)
        p.fillPath(path, QBrush(C_BG_PILL))
        unlocked = getattr(self, "_unlocked", True)
        pen = QPen(QColor(232, 93, 4, 200) if unlocked else C_BORDER)
        pen.setWidthF(1.5 if unlocked else 1.0)
        p.setPen(pen)
        p.drawPath(path)

    def update_lap(self, current):
        self._lap_val.setText(_fmt_time(current))

    def update_delta(self, delta):
        if delta is None:
            self._delta_val.setText("---")
            self._delta_val.setStyleSheet("color: #ffffff; background: transparent;")
            return
        sign = "+" if delta >= 0 else ""
        c = C_RED if delta >= 0 else C_TEAL
        self._delta_val.setText(f"{sign}{delta:.3f}s")
        self._delta_val.setStyleSheet(f"color: {c.name()}; background: transparent;")

    def update_act(self, text: str | None):
        self._act_val.setText(text or "---")


# ── SectorStrip ─────────────────────────────────────────────────────────────────
class SectorStrip(QWidget):
    """Three colored bars showing S1 / S2 / S3 completion."""

    W, H = 380, 8
    DONE, ACTIVE, PENDING = 0, 1, 2

    def __init__(self):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)
        self._states = [self.PENDING] * 3
        self._blink = False
        t = QTimer(self)
        t.timeout.connect(self._tick)
        t.start(750)

    def _tick(self):
        self._blink = not self._blink
        if self.ACTIVE in self._states:
            self.update()

    def set_progress(self, dist_pct: float):
        if dist_pct < 0.333:
            s = [self.ACTIVE, self.PENDING, self.PENDING]
        elif dist_pct < 0.667:
            s = [self.DONE, self.ACTIVE, self.PENDING]
        else:
            s = [self.DONE, self.DONE, self.ACTIVE]
        if s != self._states:
            self._states = s
            self.update()

    def reset(self):
        self._states = [self.PENDING] * 3
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        gap = 4.0
        r = self.H / 2.0
        seg = (self.W - gap * 2) / 3.0

        for i, state in enumerate(self._states):
            x = i * (seg + gap)
            path = QPainterPath()
            path.addRoundedRect(x, 0, seg, self.H, r, r)
            if state == self.DONE:
                p.fillPath(path, QBrush(C_TEAL))
            elif state == self.ACTIVE:
                alpha = 255 if not self._blink else 150
                p.fillPath(path, QBrush(QColor(0, 212, 170, alpha)))
            else:
                p.fillPath(path, QBrush(C_DIM_SEC))


# ── StatusWindow ────────────────────────────────────────────────────────────────
class StatusWindow(QWidget):
    """320×240 frameless mini window — agent activity log."""

    W, H, R = 320, 240, 12
    HEADER_H = 36
    FOOTER_H = 32

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.W, self.H)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        header.setFixedHeight(self.HEADER_H)
        h_row = QHBoxLayout(header)
        h_row.setContentsMargins(14, 0, 12, 0)

        title = QLabel("SkillIssue Racing")
        title.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        title.setStyleSheet("color: #e85d04; background: transparent; letter-spacing: 1px;")

        close_btn = QLabel("✕")
        close_btn.setFont(QFont("Segoe UI", 10))
        close_btn.setStyleSheet("color: #888899; background: transparent;")
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.mousePressEvent = lambda _: self.hide()

        h_row.addWidget(title)
        h_row.addStretch()
        h_row.addWidget(close_btn)

        # ── Activity feed ──
        self._feed = QListWidget()
        self._feed.setFont(QFont("Segoe UI", 9))
        self._feed.setStyleSheet("""
            QListWidget { background: transparent; border: none; color: #e0e0e0; }
            QListWidget::item { padding: 1px 14px; border: none; }
        """)
        self._feed.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._feed.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # ── Footer ──
        footer = QWidget()
        footer.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        footer.setFixedHeight(self.FOOTER_H)
        f_row = QHBoxLayout(footer)
        f_row.setContentsMargins(14, 0, 14, 0)

        self._dot = QLabel()
        self._dot.setFixedSize(8, 8)
        self._dot.setStyleSheet("background: #41eec2; border-radius: 4px;")

        watch_lbl = QLabel("Watching for new sessions...")
        watch_lbl.setFont(QFont("Segoe UI", 9))
        watch_lbl.setStyleSheet("color: #888899; background: transparent;")

        f_row.addWidget(self._dot)
        f_row.addSpacing(6)
        f_row.addWidget(watch_lbl)
        f_row.addStretch()

        outer.addWidget(header)
        outer.addWidget(self._feed, 1)
        outer.addWidget(footer)

        self._last_log_count = -1
        self._pulse_on = True

        refresh_t = QTimer(self)
        refresh_t.timeout.connect(self._refresh_feed)
        refresh_t.start(500)

        pulse_t = QTimer(self)
        pulse_t.timeout.connect(self._pulse_tick)
        pulse_t.start(1000)

    def _pulse_tick(self):
        self._pulse_on = not self._pulse_on
        alpha = 255 if self._pulse_on else 140
        self._dot.setStyleSheet(f"background: rgba(65,238,194,{alpha}); border-radius: 4px;")

    def _refresh_feed(self):
        n = len(_event_log)
        if n == self._last_log_count:
            return
        self._last_log_count = n
        self._feed.clear()
        for entry in _event_log:
            item = QListWidgetItem(entry)
            item.setForeground(QBrush(QColor(224, 224, 224)))
            self._feed.addItem(item)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Background
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.W, self.H, self.R, self.R)
        p.fillPath(path, QBrush(C_BG_WIN))
        # Border
        pen = QPen(C_BORDER)
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.drawPath(path)
        # Section dividers
        p.drawLine(0, self.HEADER_H, self.W, self.HEADER_H)
        p.drawLine(0, self.H - self.FOOTER_H, self.W, self.H - self.FOOTER_H)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.MouseButton.LeftButton and hasattr(self, "_drag"):
            self.move(e.globalPosition().toPoint() - self._drag)
