from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class MarketPopupWindow(QWidget):
    closed = Signal()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class ChartPopupWindow(QWidget):
    closed = Signal()

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class MiniChartWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.series = []
        self.ema9 = []
        self.ema21 = []
        self.label = "Mini Chart"
        self.setMinimumHeight(220)

    def set_chart_data(self, label, series, ema9=None, ema21=None):
        self.label = label
        self.series = series or []
        self.ema9 = ema9 or []
        self.ema21 = ema21 or []
        self.update()

    def _points_for(self, values, rect):
        clean = [value for value in values if isinstance(value, (int, float))]
        if len(clean) < 2:
            return []
        low = min(clean)
        high = max(clean)
        span = (high - low) or 1.0
        points = []
        for index, value in enumerate(clean):
            x = rect.left() + (rect.width() * index / max(len(clean) - 1, 1))
            y = rect.bottom() - ((value - low) / span) * rect.height()
            points.append((x, y))
        return points

    def _draw_line(self, painter, rect, values, color, width=2):
        points = self._points_for(values, rect)
        if len(points) < 2:
            return
        path = QPainterPath()
        path.moveTo(*points[0])
        for x, y in points[1:]:
            path.lineTo(x, y)
        pen = QPen(QColor(color), width)
        painter.setPen(pen)
        painter.drawPath(path)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#0d131c"))

        painter.setPen(QPen(QColor("#243349"), 1))
        painter.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 12, 12)

        title_rect = self.rect().adjusted(14, 10, -14, -10)
        painter.setPen(QColor("#ffd782"))
        painter.drawText(title_rect, Qt.AlignTop | Qt.AlignLeft, self.label)

        chart_rect = self.rect().adjusted(14, 42, -14, -20)
        painter.setPen(QPen(QColor("#1d2838"), 1))
        for step in range(1, 4):
            y = chart_rect.top() + chart_rect.height() * step / 4
            painter.drawLine(chart_rect.left(), int(y), chart_rect.right(), int(y))

        self._draw_line(painter, chart_rect, self.series, "#5ad1ff", 2.5)
        self._draw_line(painter, chart_rect, self.ema21, "#ffcf6a", 1.5)
        self._draw_line(painter, chart_rect, self.ema9, "#8aff8a", 1.5)
