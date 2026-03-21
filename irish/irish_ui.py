import html
import re
import sys
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import ai_router
from agent_manager import get_task
from agent import process_command
from live_market_data import fetch_price_series, fetch_quote_snapshot
from market_data import extract_symbol, extract_timeframe
from watchlist import load_watchlist, remove_from_watchlist
from voice_input import listen
from voice_output import speak
from wake_word import listen_for_wake_word


class StreamSignal(QObject):
    new_token = Signal(str, str)
    finished = Signal(str)
    add_chat = Signal(str, str)
    start_response = Signal(str)
    set_voice_active = Signal(bool)
    refresh_mode = Signal()
    update_tab_status = Signal(str, str)
    refresh_task_panel = Signal()
    market_cards_ready = Signal(object)
    market_watchlist_ready = Signal(object)
    market_chart_ready = Signal(object)


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


class IrishUI(QWidget):

    def __init__(self):
        super().__init__()

        self.voice_active = False
        self.tab_counter = 0
        self.chat_tabs = {}
        self.market_tab_id = None
        self.market_signal_cards = {}
        self.market_refresh_token = 0
        self.market_watchlist_token = 0
        self.market_chart_token = 0
        self.market_workspace = None
        self.market_window = None
        self.market_popup_activity = None
        self.market_popup_task_view = None
        self.market_popup_mode = None
        self.market_popup_chart = None
        self.market_popup_chart_summary = None
        self.market_chart_buttons = {}
        self.market_chart_window = None
        self.market_chart_popup = None
        self.market_chart_popup_summary = None
        self.market_chart_popup_clock = None
        self.market_chart_popup_timeframe_buttons = {}
        self.clock_label = None
        self.market_popup_clock = None
        self.market_chart_symbol = ""
        self.market_chart_timeframe = "swing"

        self.setWindowTitle("Irish AI Assistant")
        self.setGeometry(220, 120, 920, 620)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #16181d;
                color: #f4f7fb;
                font-family: "Segoe UI";
                font-size: 14px;
            }
            QTabWidget::pane {
                border: 1px solid #2a3140;
                border-radius: 14px;
                background: #111318;
                top: -1px;
            }
            QTabBar::tab {
                background: #121723;
                color: #b8c4d8;
                border: 1px solid #283143;
                padding: 8px 14px;
                margin-right: 6px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
            QTabBar::tab:selected {
                background: #1e2636;
                color: #eef3fb;
                border-color: #4a83ff;
            }
            QTextEdit {
                background-color: #111318;
                border: 1px solid #2a3140;
                border-radius: 14px;
                padding: 14px;
                selection-background-color: #3a6df0;
            }
            QLineEdit {
                background-color: #0f1217;
                border: 1px solid #2a3140;
                border-radius: 12px;
                padding: 10px 12px;
                color: #f4f7fb;
            }
            QLineEdit:focus {
                border: 1px solid #4a83ff;
            }
            QPushButton {
                background-color: #2c6bed;
                border: none;
                border-radius: 12px;
                padding: 10px 16px;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #3a78f5;
            }
            QPushButton:disabled {
                background-color: #384153;
                color: #aeb8c7;
            }
            QLabel {
                color: #dfe6f0;
            }
            """
        )

        layout = QVBoxLayout()

        mode_bar = QHBoxLayout()
        self.mode_label = QLabel("Mode:")
        self.mode_btn = QPushButton("Switch to Online")
        self.mode_status = QLabel()
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet(
            "color:#ffd782; font-weight:700; background:#23180a; padding:6px 12px; border-radius:12px;"
        )
        self.new_chat_btn = QPushButton("New Chat")
        self.market_tab_btn = QPushButton("Open Market Window")
        self.mode_btn.clicked.connect(self.toggle_mode)
        self.new_chat_btn.clicked.connect(self.create_chat_tab)
        self.market_tab_btn.clicked.connect(self.open_market_window)

        mode_bar.addWidget(self.mode_label)
        mode_bar.addWidget(self.mode_status)
        mode_bar.addStretch()
        mode_bar.addWidget(self.clock_label)
        mode_bar.addWidget(self.market_tab_btn)
        mode_bar.addWidget(self.new_chat_btn)
        mode_bar.addWidget(self.mode_btn)
        layout.addLayout(mode_bar)

        content_row = QHBoxLayout()

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_chat_tab)
        self.tabs.tabBarDoubleClicked.connect(self._handle_tab_double_click)
        content_row.addWidget(self.tabs, 3)

        self.task_panel = QFrame()
        self.task_panel.setStyleSheet(
            "QFrame { background:#10141c; border:1px solid #2a3140; border-radius:14px; }"
        )
        panel_layout = QVBoxLayout(self.task_panel)
        panel_layout.setContentsMargins(14, 14, 14, 14)

        self.task_title = QLabel("Task Context")
        self.task_title.setStyleSheet("color:#9fc3ff; font-size:16px; font-weight:700;")
        self.task_subtitle = QLabel("No active task yet.")
        self.task_subtitle.setStyleSheet("color:#b8c4d8;")

        self.task_view = QTextEdit()
        self.task_view.setReadOnly(True)
        self.task_view.setPlaceholderText("When Irish plans or delegates a task, details will appear here.")

        panel_layout.addWidget(self.task_title)
        panel_layout.addWidget(self.task_subtitle)
        panel_layout.addWidget(self.task_view)

        content_row.addWidget(self.task_panel, 1)
        layout.addLayout(content_row)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask Irish something...")

        btn_bar = QHBoxLayout()
        self.send_btn = QPushButton("Send")
        self.mic_btn = QPushButton("Speak")
        btn_bar.addWidget(self.send_btn)
        btn_bar.addWidget(self.mic_btn)

        layout.addWidget(self.input)
        layout.addLayout(btn_bar)
        self.setLayout(layout)

        self.send_btn.clicked.connect(self.send_message)
        self.input.returnPressed.connect(self.send_message)
        self.mic_btn.clicked.connect(self.voice_message)

        self.stream = StreamSignal()
        self.stream.new_token.connect(self.update_stream)
        self.stream.finished.connect(self.stream_finished)
        self.stream.add_chat.connect(self.add_chat)
        self.stream.start_response.connect(self.start_response)
        self.stream.set_voice_active.connect(self.set_voice_active)
        self.stream.refresh_mode.connect(self.refresh_mode_ui)
        self.stream.update_tab_status.connect(self.set_tab_status)
        self.stream.refresh_task_panel.connect(self.refresh_task_panel)
        self.stream.market_cards_ready.connect(self.update_market_cards)
        self.stream.market_watchlist_ready.connect(self.update_market_watchlist)
        self.stream.market_chart_ready.connect(self.update_market_chart)

        self.create_market_tab(make_current=False)
        self.create_chat_tab(make_current=True)
        self.refresh_mode_ui()
        self.add_chat(self.current_tab_id(), "[System] Irish is ready.")

        self.task_timer = QTimer(self)
        self.task_timer.timeout.connect(self.refresh_task_panel)
        self.task_timer.start(1200)
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.refresh_clock_labels)
        self.clock_timer.start(1000)
        self.refresh_clock_labels()
        self.refresh_task_panel()

    def create_chat_tab(self, make_current=True):
        self.tab_counter += 1
        tab_id = f"chat-{self.tab_counter}"
        index = self._create_tab_shell(
            tab_id,
            f"Chat {self.tab_counter}",
            "Irish is ready.",
        )

        if make_current:
            self.tabs.setCurrentIndex(index)

        return tab_id

    def create_market_tab(self, make_current=True):
        if self.market_tab_id and self.market_tab_id in self.chat_tabs:
            if make_current:
                self._select_tab(self.market_tab_id)
            return self.market_tab_id

        self.market_tab_id = "market-main"
        index = self._create_tab_shell(
            self.market_tab_id,
            "Markets",
            "Use this workspace for Indian stock analysis, watchlists, journal entries, and risk sizing.",
            initial_status="Market Desk",
        )

        container = self.chat_tabs[self.market_tab_id]["container"]
        if self.market_workspace is None:
            self.market_workspace = self._build_market_workspace()
        container.layout().insertWidget(1, self.market_workspace)
        container.layout().setStretch(2, 1)

        if make_current:
            self.tabs.setCurrentIndex(index)

        self.set_tab_status(self.market_tab_id, "Market Desk")
        self.add_chat(self.market_tab_id, "[System] Market desk is ready for Indian stock analysis.")
        self.refresh_market_watchlist()
        return self.market_tab_id

    def _create_tab_shell(self, tab_id, title, placeholder, initial_status="Ready"):
        container = QWidget()
        container.setProperty("tab_id", tab_id)
        tab_layout = QVBoxLayout(container)
        tab_layout.setContentsMargins(6, 6, 6, 6)

        status_label = QLabel(initial_status)
        status_label.setStyleSheet(
            "color:#9ac6ff; background:#132035; padding:4px 10px; border-radius:10px; font-weight:600;"
        )

        chat = QTextEdit()
        chat.setReadOnly(True)
        chat.setPlaceholderText(placeholder)
        chat.setMinimumHeight(170)

        tab_layout.addWidget(status_label)
        tab_layout.addWidget(chat, 1)

        index = self.tabs.addTab(container, title)
        self.chat_tabs[tab_id] = {
            "container": container,
            "chat": chat,
            "status": status_label,
            "response_open": False,
            "active_tasks": 0,
            "task_ids": [],
            "title": title,
            "kind": "market" if tab_id == self.market_tab_id else "chat",
        }
        return index

    def _build_market_workspace(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_market_controls())
        content_layout.addStretch()

        scroll.setWidget(content)
        scroll.setMinimumHeight(420)
        return scroll

    def _build_market_controls(self):
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background:#121924; border:1px solid #2a3140; border-radius:12px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Indian Market Desk")
        title.setStyleSheet("color:#ffd782; font-size:17px; font-weight:700;")

        hint = QLabel(
            "Use separate trade lanes for intraday, swing, and long-term ideas. The desk will keep the chat output below, while these controls help you launch cleaner market workflows."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color:#b8c4d8;")

        top_row = QHBoxLayout()
        self.market_symbol_input = QLineEdit()
        self.market_symbol_input.setPlaceholderText("Symbol or index like RELIANCE, INFY, NIFTY")
        analyze_btn = QPushButton("Quote")
        watch_btn = QPushButton("Add Watchlist")
        risk_btn = QPushButton("Risk Template")

        analyze_btn.clicked.connect(lambda: self._send_market_command("quote {symbol}"))
        watch_btn.clicked.connect(lambda: self._send_market_command("add {symbol} to watchlist"))
        risk_btn.clicked.connect(self._fill_risk_template)

        top_row.addWidget(self.market_symbol_input, 2)
        top_row.addWidget(analyze_btn)
        top_row.addWidget(watch_btn)
        top_row.addWidget(risk_btn)

        shortcut_row = QHBoxLayout()
        for symbol in ("RELIANCE", "TCS", "INFY", "NIFTY", "BANKNIFTY"):
            button = QPushButton(symbol)
            button.clicked.connect(lambda checked=False, value=symbol: self._set_market_symbol(value))
            shortcut_row.addWidget(button)

        strategy_grid = QGridLayout()
        strategy_grid.setHorizontalSpacing(10)
        strategy_grid.setVerticalSpacing(10)

        signal_strip = QHBoxLayout()
        signal_strip.addWidget(self._build_signal_card("Intraday Signal", "intraday", "#5ad1ff"))
        signal_strip.addWidget(self._build_signal_card("Swing Signal", "swing", "#8aff8a"))
        signal_strip.addWidget(self._build_signal_card("Long-Term Signal", "positional", "#ffcf6a"))

        strategy_grid.addWidget(
            self._build_strategy_card(
                "Intraday",
                "Fast setup review for live market momentum, VWAP context, and short-term signal bias.",
                "#5ad1ff",
                (
                    ("Analyze", "intraday analyze {symbol} stock"),
                    ("Signal", "intraday trade for {symbol}"),
                    ("Quote", "quote {symbol}"),
                ),
            ),
            0,
            0,
        )
        strategy_grid.addWidget(
            self._build_strategy_card(
                "Swing",
                "Multi-day setup view for breakout, pullback, support, resistance, and position planning.",
                "#8aff8a",
                (
                    ("Analyze", "swing analyze {symbol} stock"),
                    ("Signal", "swing trade for {symbol}"),
                    ("Risk", "risk for {symbol} entry 0 stop 0 capital 100000 risk 1"),
                ),
            ),
            0,
            1,
        )
        strategy_grid.addWidget(
            self._build_strategy_card(
                "Long Term",
                "Positional and investing-style view with broader trend, structure, and patience bias.",
                "#ffcf6a",
                (
                    ("Analyze", "positional analyze {symbol} stock"),
                    ("View", "long term analysis for {symbol}"),
                    ("Journal", "journal {symbol} long term thesis"),
                ),
            ),
            0,
            2,
        )

        helper_row = QHBoxLayout()
        helper_row.addWidget(
            self._build_market_helper(
                "Desk Flow",
                "1. Pick a symbol\n2. Choose a lane\n3. Review setup in chat\n4. Save or journal if useful",
                "#5ad1ff",
            )
        )
        helper_row.addWidget(
            self._build_market_helper(
                "Quick Tools",
                "Show watchlist, review journal, and compare NIFTY or BANKNIFTY without typing full commands.",
                "#8aff8a",
            )
        )

        watchlist_panel = self._build_market_watchlist_panel()

        bottom_row = QHBoxLayout()
        show_watchlist_btn = QPushButton("Show Watchlist")
        show_journal_btn = QPushButton("Show Journal")
        nifty_btn = QPushButton("Analyze NIFTY")
        banknifty_btn = QPushButton("Analyze BANKNIFTY")

        show_watchlist_btn.clicked.connect(lambda: self._start_task(self.market_tab_id, "show watchlist"))
        show_journal_btn.clicked.connect(lambda: self._start_task(self.market_tab_id, "show trade journal"))
        nifty_btn.clicked.connect(lambda: self._start_task(self.market_tab_id, "analyze NIFTY"))
        banknifty_btn.clicked.connect(lambda: self._start_task(self.market_tab_id, "analyze BANKNIFTY"))

        bottom_row.addWidget(show_watchlist_btn)
        bottom_row.addWidget(show_journal_btn)
        bottom_row.addWidget(nifty_btn)
        bottom_row.addWidget(banknifty_btn)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(top_row)
        layout.addLayout(shortcut_row)
        layout.addLayout(signal_strip)
        layout.addLayout(strategy_grid)
        layout.addLayout(helper_row)
        layout.addWidget(watchlist_panel)
        layout.addLayout(bottom_row)
        return panel

    def _build_strategy_card(self, title, body, accent, actions):
        card = QFrame()
        card.setMinimumHeight(185)
        card.setStyleSheet(
            f"QFrame {{ background:#0f1622; border:1px solid {accent}; border-radius:14px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        heading = QLabel(title)
        heading.setStyleSheet(f"color:{accent}; font-size:15px; font-weight:700;")

        text = QLabel(body)
        text.setWordWrap(True)
        text.setStyleSheet("color:#c7d5e8;")

        buttons = QHBoxLayout()
        for label, template in actions:
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, command=template: self._send_market_command(command))
            buttons.addWidget(button)

        layout.addWidget(heading)
        layout.addWidget(text)
        layout.addLayout(buttons)
        return card

    def _build_market_helper(self, title, body, accent):
        card = QFrame()
        card.setMinimumHeight(95)
        card.setStyleSheet(
            f"QFrame {{ background:#0e141d; border:1px solid #243349; border-radius:12px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        heading = QLabel(title)
        heading.setStyleSheet(f"color:{accent}; font-weight:700;")

        text = QLabel(body)
        text.setWordWrap(True)
        text.setStyleSheet("color:#aebfd5;")

        layout.addWidget(heading)
        layout.addWidget(text)
        return card

    def _build_market_watchlist_panel(self):
        panel = QFrame()
        panel.setMinimumHeight(200)
        panel.setStyleSheet(
            "QFrame { background:#0e141d; border:1px solid #243349; border-radius:14px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Live Watchlist")
        title.setStyleSheet("color:#ffd782; font-size:15px; font-weight:700;")
        subtitle = QLabel("Tap a row to load it into the desk, or remove it directly from here.")
        subtitle.setStyleSheet("color:#9fb2c8;")
        subtitle.setWordWrap(True)

        refresh_btn = QPushButton("Refresh Watchlist")
        refresh_btn.clicked.connect(self.refresh_market_watchlist)

        title_wrap = QVBoxLayout()
        title_wrap.addWidget(title)
        title_wrap.addWidget(subtitle)
        header.addLayout(title_wrap, 1)
        header.addWidget(refresh_btn)

        self.market_watchlist_summary = QLabel("No watchlist data yet.")
        self.market_watchlist_summary.setStyleSheet("color:#aebfd5; font-size:12px;")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")

        content = QWidget()
        self.market_watchlist_layout = QVBoxLayout(content)
        self.market_watchlist_layout.setContentsMargins(0, 0, 0, 0)
        self.market_watchlist_layout.setSpacing(8)
        self.market_watchlist_layout.addWidget(QLabel("Your watchlist rows will appear here."))
        self.market_watchlist_layout.addStretch()
        scroll.setWidget(content)

        layout.addLayout(header)
        layout.addWidget(self.market_watchlist_summary)
        layout.addWidget(scroll)
        return panel

    def _build_signal_card(self, title, timeframe, accent):
        card = QFrame()
        card.setMinimumHeight(140)
        card.setStyleSheet(
            f"QFrame {{ background:#0e141d; border:1px solid {accent}; border-radius:14px; }}"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        heading = QLabel(title)
        heading.setStyleSheet(f"color:{accent}; font-size:14px; font-weight:700;")

        signal = QLabel("WAITING")
        signal.setStyleSheet("color:#b8c4d8; font-size:18px; font-weight:700;")

        price = QLabel("Pick a symbol to load live setup data.")
        price.setWordWrap(True)
        price.setStyleSheet("color:#d9e2ef;")

        context = QLabel("Trend: -- | Score: --")
        context.setWordWrap(True)
        context.setStyleSheet("color:#8ea5c2; font-size:12px;")

        levels = QLabel("S/R: -- / --")
        levels.setWordWrap(True)
        levels.setStyleSheet("color:#8ea5c2; font-size:12px;")

        layout.addWidget(heading)
        layout.addWidget(signal)
        layout.addWidget(price)
        layout.addWidget(context)
        layout.addWidget(levels)

        self.market_signal_cards[timeframe] = {
            "card": card,
            "signal": signal,
            "price": price,
            "context": context,
            "levels": levels,
            "accent": accent,
        }
        return card

    def _set_market_symbol(self, symbol):
        self.market_symbol_input.setText(symbol)
        self.market_symbol_input.setFocus()
        self.refresh_market_cards(symbol)
        self.refresh_market_watchlist()
        self.refresh_market_chart(symbol, timeframe="swing")

    def _fill_risk_template(self):
        symbol = self.market_symbol_input.text().strip().upper() or "RELIANCE"
        self._select_tab(self.market_tab_id)
        self.input.setText(f"risk for {symbol} entry 0 stop 0 capital 100000 risk 1")
        self.input.setFocus()
        self.refresh_market_cards(symbol)
        self.refresh_market_chart(symbol, timeframe="swing")

    def _send_market_command(self, template):
        symbol = self.market_symbol_input.text().strip().upper()
        if "{symbol}" in template and not symbol:
            self.add_chat(self.market_tab_id, "[System] Please enter a symbol first.")
            return

        self._select_tab(self.market_tab_id)
        if symbol:
            self.refresh_market_cards(symbol)
            self.refresh_market_chart(symbol, timeframe=extract_timeframe(template.format(symbol=symbol)))
        self._start_task(self.market_tab_id, template.format(symbol=symbol).strip())

    def refresh_market_cards(self, symbol=None):
        current_symbol = (symbol or self.market_symbol_input.text().strip().upper())
        if not current_symbol:
            return

        self.market_refresh_token += 1
        token = self.market_refresh_token

        def worker():
            payload = {"symbol": current_symbol, "token": token, "cards": {}}
            for timeframe in ("intraday", "swing", "positional"):
                try:
                    payload["cards"][timeframe] = {
                        "ok": True,
                        "snapshot": fetch_quote_snapshot(current_symbol, timeframe=timeframe),
                    }
                except Exception as exc:
                    payload["cards"][timeframe] = {
                        "ok": False,
                        "error": str(exc),
                    }
            self.stream.market_cards_ready.emit(payload)

        threading.Thread(target=worker, daemon=True).start()

    def refresh_market_watchlist(self):
        self.market_watchlist_token += 1
        token = self.market_watchlist_token

        def worker():
            items = load_watchlist()
            payload = {"token": token, "rows": [], "count": len(items)}
            for item in items[:12]:
                symbol = item["symbol"]
                try:
                    snapshot = fetch_quote_snapshot(symbol, timeframe="swing")
                    payload["rows"].append({
                        "symbol": symbol,
                        "ok": True,
                        "snapshot": snapshot,
                    })
                except Exception as exc:
                    payload["rows"].append({
                        "symbol": symbol,
                        "ok": False,
                        "error": str(exc),
                    })
            self.stream.market_watchlist_ready.emit(payload)

        threading.Thread(target=worker, daemon=True).start()

    def refresh_market_chart(self, symbol=None, timeframe="swing"):
        current_symbol = (symbol or self.market_symbol_input.text().strip().upper())
        if not current_symbol:
            return

        self.market_chart_symbol = current_symbol
        self.market_chart_timeframe = timeframe
        self._update_chart_timeframe_buttons()
        self.market_chart_token += 1
        token = self.market_chart_token

        def worker():
            try:
                series = fetch_price_series(current_symbol, timeframe=timeframe)
                payload = {"token": token, "ok": True, "series": series}
            except Exception as exc:
                payload = {
                    "token": token,
                    "ok": False,
                    "symbol": current_symbol,
                    "timeframe": timeframe,
                    "error": str(exc),
                }
            self.stream.market_chart_ready.emit(payload)

        threading.Thread(target=worker, daemon=True).start()

    def update_market_cards(self, payload):
        if payload.get("token") != self.market_refresh_token:
            return

        symbol = payload.get("symbol", "")
        for timeframe, card in self.market_signal_cards.items():
            entry = payload.get("cards", {}).get(timeframe, {})
            if not entry:
                continue

            if entry.get("ok"):
                snapshot = entry["snapshot"]
                signal = snapshot.get("signal", "HOLD")
                color = {
                    "STRONG BUY": "#00ff9d",
                    "BUY": "#7dffb3",
                    "HOLD": "#ffd782",
                    "SELL": "#ff8f8f",
                    "STRONG SELL": "#ff5f7d",
                }.get(signal, "#b8c4d8")
                price = snapshot.get("price")
                change_percent = snapshot.get("change_percent")
                support = snapshot.get("support")
                resistance = snapshot.get("resistance")
                price_text = f"{symbol}: {price:.2f} INR" if isinstance(price, (int, float)) else f"{symbol}: --"
                if isinstance(change_percent, (int, float)):
                    price_text += f" ({change_percent:+.2f}%)"
                card["signal"].setText(signal)
                card["signal"].setStyleSheet(f"color:{color}; font-size:18px; font-weight:700;")
                card["price"].setText(price_text)
                card["context"].setText(
                    f"Trend: {snapshot.get('trend', '--')} | Score: {snapshot.get('setup_score', '--')}/100"
                )
                if isinstance(support, (int, float)) and isinstance(resistance, (int, float)):
                    card["levels"].setText(f"S/R: {support:.2f} / {resistance:.2f}")
                else:
                    card["levels"].setText("S/R: -- / --")
            else:
                card["signal"].setText("UNAVAILABLE")
                card["signal"].setStyleSheet("color:#ff8f8f; font-size:18px; font-weight:700;")
                card["price"].setText(f"{symbol}: live data unavailable")
                card["context"].setText(entry.get("error", "Could not load market data right now."))
                card["levels"].setText("S/R: -- / --")

    def update_market_watchlist(self, payload):
        if payload.get("token") != self.market_watchlist_token:
            return

        while self.market_watchlist_layout.count():
            item = self.market_watchlist_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        count = payload.get("count", 0)
        self.market_watchlist_summary.setText(
            f"{count} symbols tracked. Live rows below use swing-mode signal snapshots."
        )

        rows = payload.get("rows", [])
        if not rows:
            empty = QLabel("Your watchlist is empty right now. Add symbols from the Market Desk controls.")
            empty.setStyleSheet("color:#9fb2c8;")
            empty.setWordWrap(True)
            self.market_watchlist_layout.addWidget(empty)
            self.market_watchlist_layout.addStretch()
            return

        for row in rows:
            self.market_watchlist_layout.addWidget(self._build_market_watchlist_row(row))

        self.market_watchlist_layout.addStretch()

    def update_market_chart(self, payload):
        if payload.get("token") != self.market_chart_token:
            return

        if self.market_popup_chart is None and self.market_chart_popup is None:
            return

        if payload.get("ok"):
            series = payload["series"]
            label = f"{series.get('symbol', self.market_chart_symbol)} • {series.get('timeframe', self.market_chart_timeframe).title()}"
            if self.market_popup_chart is not None:
                self.market_popup_chart.set_chart_data(
                    label,
                    series.get("closes", []),
                    ema9=series.get("ema9", []),
                    ema21=series.get("ema21", []),
                )
            closes = series.get("closes", [])
            if closes and self.market_popup_chart_summary is not None:
                self.market_popup_chart_summary.setText(
                    f"{label} chart loaded with {len(closes)} points. Blue = price, green = EMA9, gold = EMA21."
                )
            elif self.market_popup_chart_summary is not None:
                self.market_popup_chart_summary.setText("Chart loaded, but there were not enough points to draw a trend.")
        else:
            symbol = payload.get("symbol", self.market_chart_symbol)
            timeframe = payload.get("timeframe", self.market_chart_timeframe)
            if self.market_popup_chart is not None:
                self.market_popup_chart.set_chart_data(f"{symbol} • {timeframe.title()}", [])
            if self.market_popup_chart_summary is not None:
                self.market_popup_chart_summary.setText(
                    f"Could not load chart data for {symbol} ({timeframe}): {payload.get('error', 'unknown error')}"
                )
        self._sync_chart_popup(payload)

    def _set_chart_timeframe(self, timeframe):
        self.market_chart_timeframe = timeframe
        self._update_chart_timeframe_buttons()
        current_symbol = self.market_symbol_input.text().strip().upper() or self.market_chart_symbol
        if current_symbol:
            self.refresh_market_chart(current_symbol, timeframe=timeframe)

    def _update_chart_timeframe_buttons(self):
        if not self.market_chart_buttons:
            self._update_chart_popup_timeframe_buttons()
            return

        palette = {
            "intraday": {"accent": "#5ad1ff", "bg": "#06131d"},
            "swing": {"accent": "#8aff8a", "bg": "#0d1b10"},
            "positional": {"accent": "#ffcf6a", "bg": "#1b160a"},
        }

        for timeframe, button in self.market_chart_buttons.items():
            colors = palette.get(timeframe, {"accent": "#7ea6ff", "bg": "#101826"})
            if timeframe == self.market_chart_timeframe:
                button.setStyleSheet(
                    "QPushButton {"
                    f"background:{colors['accent']}; color:#061018; border:none; "
                    "border-radius:10px; padding:8px 12px; font-weight:700;"
                    "}"
                )
            else:
                button.setStyleSheet(
                    "QPushButton {"
                    f"background:{colors['bg']}; color:{colors['accent']}; border:1px solid {colors['accent']}; "
                    "border-radius:10px; padding:8px 12px; font-weight:700;"
                    "}"
                    "QPushButton:hover { background:#1a2433; }"
                )
        self._update_chart_popup_timeframe_buttons()

    def _update_chart_popup_timeframe_buttons(self):
        if not self.market_chart_popup_timeframe_buttons:
            return

        palette = {
            "intraday": {"accent": "#5ad1ff", "bg": "#06131d"},
            "swing": {"accent": "#8aff8a", "bg": "#0d1b10"},
            "positional": {"accent": "#ffcf6a", "bg": "#1b160a"},
        }

        for timeframe, button in self.market_chart_popup_timeframe_buttons.items():
            colors = palette.get(timeframe, {"accent": "#7ea6ff", "bg": "#101826"})
            if timeframe == self.market_chart_timeframe:
                button.setStyleSheet(
                    "QPushButton {"
                    f"background:{colors['accent']}; color:#061018; border:none; "
                    "border-radius:10px; padding:8px 12px; font-weight:700;"
                    "}"
                )
            else:
                button.setStyleSheet(
                    "QPushButton {"
                    f"background:{colors['bg']}; color:{colors['accent']}; border:1px solid {colors['accent']}; "
                    "border-radius:10px; padding:8px 12px; font-weight:700;"
                    "}"
                    "QPushButton:hover { background:#1a2433; }"
                )

    def open_chart_window(self):
        if self.market_chart_window is not None:
            self.market_chart_window.showNormal()
            self.market_chart_window.raise_()
            self.market_chart_window.activateWindow()
            return

        self.market_chart_window = ChartPopupWindow()
        self.market_chart_window.setWindowTitle("Irish Market Chart")
        self.market_chart_window.setGeometry(260, 140, 1080, 720)
        self.market_chart_window.setStyleSheet(self.styleSheet())

        layout = QVBoxLayout(self.market_chart_window)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Live Market Chart")
        title.setStyleSheet("color:#ffd782; font-size:18px; font-weight:700;")
        self.market_chart_popup_clock = QLabel()
        self.market_chart_popup_clock.setStyleSheet(
            "color:#ffd782; font-weight:700; background:#23180a; padding:6px 12px; border-radius:12px;"
        )
        min_btn = QPushButton("Minimize")
        min_btn.clicked.connect(lambda: self.market_chart_window.showMinimized() if self.market_chart_window else None)
        max_btn = QPushButton("Maximize")
        max_btn.clicked.connect(self._toggle_chart_window_maximize)
        close_btn = QPushButton("Close Chart")
        close_btn.clicked.connect(self._close_chart_window)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.market_chart_popup_clock)
        header.addWidget(min_btn)
        header.addWidget(max_btn)
        header.addWidget(close_btn)

        timeframe_row = QHBoxLayout()
        timeframe_row.setSpacing(8)
        self.market_chart_popup_timeframe_buttons = {}
        for label, timeframe in (
            ("Intraday", "intraday"),
            ("Swing", "swing"),
            ("Long Term", "positional"),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, tf=timeframe: self._set_chart_timeframe(tf))
            timeframe_row.addWidget(button)
            self.market_chart_popup_timeframe_buttons[timeframe] = button
        timeframe_row.addStretch()

        self.market_chart_popup = MiniChartWidget()
        self.market_chart_popup.setMinimumHeight(460)
        self.market_chart_popup_summary = QLabel("Pick a symbol to load a live chart.")
        self.market_chart_popup_summary.setWordWrap(True)
        self.market_chart_popup_summary.setStyleSheet("color:#aebfd5;")

        layout.addLayout(header)
        layout.addLayout(timeframe_row)
        layout.addWidget(self.market_chart_popup, 1)
        layout.addWidget(self.market_chart_popup_summary)

        self.market_chart_window.closed.connect(self._on_chart_window_closed)
        self.market_chart_window.show()
        self.refresh_clock_labels()
        self._update_chart_popup_timeframe_buttons()
        current_symbol = self.market_symbol_input.text().strip().upper() or self.market_chart_symbol
        if current_symbol:
            self.refresh_market_chart(current_symbol, timeframe=self.market_chart_timeframe or "swing")

    def _toggle_chart_window_maximize(self):
        if self.market_chart_window is None:
            return
        if self.market_chart_window.isMaximized():
            self.market_chart_window.showNormal()
        else:
            self.market_chart_window.showMaximized()

    def _close_chart_window(self):
        if self.market_chart_window is not None:
            self.market_chart_window.close()

    def _on_chart_window_closed(self):
        if self.market_chart_window is not None:
            self.market_chart_window.deleteLater()
        self.market_chart_window = None
        self.market_chart_popup = None
        self.market_chart_popup_summary = None
        self.market_chart_popup_clock = None
        self.market_chart_popup_timeframe_buttons = {}

    def _sync_chart_popup(self, payload):
        if self.market_chart_popup is None:
            return

        if payload.get("ok"):
            series = payload["series"]
            label = f"{series.get('symbol', self.market_chart_symbol)} • {series.get('timeframe', self.market_chart_timeframe).title()}"
            self.market_chart_popup.set_chart_data(
                label,
                series.get("closes", []),
                ema9=series.get("ema9", []),
                ema21=series.get("ema21", []),
            )
            closes = series.get("closes", [])
            if closes:
                self.market_chart_popup_summary.setText(
                    f"{label} chart loaded with {len(closes)} points. Blue = price, green = EMA9, gold = EMA21."
                )
            else:
                self.market_chart_popup_summary.setText("Chart loaded, but there were not enough points to draw a trend.")
        else:
            symbol = payload.get("symbol", self.market_chart_symbol)
            timeframe = payload.get("timeframe", self.market_chart_timeframe)
            self.market_chart_popup.set_chart_data(f"{symbol} • {timeframe.title()}", [])
            self.market_chart_popup_summary.setText(
                f"Could not load chart data for {symbol} ({timeframe}): {payload.get('error', 'unknown error')}"
            )

    def _build_market_watchlist_row(self, row):
        symbol = row["symbol"]
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background:#121924; border:1px solid #233347; border-radius:12px; }"
        )
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        left = QVBoxLayout()
        title = QLabel(symbol)
        title.setStyleSheet("color:#eef3fb; font-size:14px; font-weight:700;")

        if row.get("ok"):
            snapshot = row["snapshot"]
            price = snapshot.get("price")
            change_percent = snapshot.get("change_percent")
            signal = snapshot.get("signal", "HOLD")
            signal_color = {
                "STRONG BUY": "#00ff9d",
                "BUY": "#7dffb3",
                "HOLD": "#ffd782",
                "SELL": "#ff8f8f",
                "STRONG SELL": "#ff5f7d",
            }.get(signal, "#b8c4d8")
            price_text = f"Price: {price:.2f} INR" if isinstance(price, (int, float)) else "Price: --"
            if isinstance(change_percent, (int, float)):
                price_text += f" ({change_percent:+.2f}%)"
            meta = QLabel(price_text)
            meta.setStyleSheet("color:#c8d5e8;")
            context = QLabel(
                f"Signal: {signal} | Trend: {snapshot.get('trend', '--')} | Score: {snapshot.get('setup_score', '--')}/100"
            )
            context.setStyleSheet(f"color:{signal_color}; font-size:12px; font-weight:700;")
        else:
            meta = QLabel("Live data unavailable right now.")
            meta.setStyleSheet("color:#ff8f8f;")
            context = QLabel(row.get("error", "Could not load data."))
            context.setStyleSheet("color:#8ea5c2; font-size:12px;")

        left.addWidget(title)
        left.addWidget(meta)
        left.addWidget(context)

        actions = QHBoxLayout()
        load_btn = QPushButton("Load")
        load_btn.clicked.connect(lambda checked=False, value=symbol: self._set_market_symbol(value))
        swing_btn = QPushButton("Swing")
        swing_btn.clicked.connect(lambda checked=False, value=symbol: self._send_market_command_with_symbol("swing analyze {symbol} stock", value))
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda checked=False, value=symbol: self._remove_watchlist_symbol(value))
        actions.addWidget(load_btn)
        actions.addWidget(swing_btn)
        actions.addWidget(remove_btn)

        layout.addLayout(left, 1)
        layout.addLayout(actions)
        return panel

    def _send_market_command_with_symbol(self, template, symbol):
        self.market_symbol_input.setText(symbol)
        self._send_market_command(template)

    def _remove_watchlist_symbol(self, symbol):
        message = remove_from_watchlist(symbol)
        self.add_chat(self.market_tab_id, f"[System] {message}")
        self.refresh_market_watchlist()

    def _select_tab(self, tab_id):
        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if widget.property("tab_id") == tab_id:
                self.tabs.setCurrentIndex(index)
                return

    def open_market_tab(self):
        self.create_market_tab(make_current=True)

    def open_market_window(self):
        self.create_market_tab(make_current=False)

        if self.market_window is not None:
            self._sync_market_popup_views()
            self.market_window.showNormal()
            self.market_window.raise_()
            self.market_window.activateWindow()
            return

        self._detach_market_workspace()

        self.market_window = MarketPopupWindow()
        self.market_window.setWindowTitle("Irish Market Desk")
        self.market_window.setGeometry(180, 90, 1540, 920)
        self.market_window.setStyleSheet(self.styleSheet())

        outer = QVBoxLayout(self.market_window)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(10)

        header = QHBoxLayout()
        title = QLabel("Indian Market Workspace")
        title.setStyleSheet("color:#ffd782; font-size:20px; font-weight:700;")
        subtitle = QLabel("Detached market desk for focused analysis, watchlist review, and faster decision support.")
        subtitle.setStyleSheet("color:#9fb2c8;")
        subtitle.setWordWrap(True)
        header_text = QVBoxLayout()
        header_text.addWidget(title)
        header_text.addWidget(subtitle)

        self.market_popup_mode = QLabel()
        self.market_popup_mode.setStyleSheet(
            "color:#82b1ff; font-weight:700; background:#142746; padding:6px 12px; border-radius:12px;"
        )
        self.market_popup_clock = QLabel()
        self.market_popup_clock.setStyleSheet(
            "color:#ffd782; font-weight:700; background:#23180a; padding:6px 12px; border-radius:12px;"
        )

        redock_btn = QPushButton("Dock Back to Main App")
        redock_btn.clicked.connect(self._close_market_window)

        header.addLayout(header_text, 1)
        header.addWidget(self.market_popup_mode)
        header.addWidget(self.market_popup_clock)
        header.addWidget(redock_btn)

        body = QHBoxLayout()
        body.setSpacing(10)
        body.addWidget(self.market_workspace, 3)

        side_panel = QFrame()
        side_panel.setStyleSheet(
            "QFrame { background:#0f141d; border:1px solid #243349; border-radius:14px; }"
        )
        side_layout = QVBoxLayout(side_panel)
        side_layout.setContentsMargins(12, 12, 12, 12)
        side_layout.setSpacing(8)

        chart_title = QLabel("Mini Chart")
        chart_title.setStyleSheet("color:#ffd782; font-size:16px; font-weight:700;")
        chart_controls = QHBoxLayout()
        chart_controls.setSpacing(8)
        self.market_chart_buttons = {}
        for label, timeframe in (
            ("Intraday", "intraday"),
            ("Swing", "swing"),
            ("Long Term", "positional"),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda _checked=False, tf=timeframe: self._set_chart_timeframe(tf))
            chart_controls.addWidget(button)
            self.market_chart_buttons[timeframe] = button
        chart_controls.addStretch()
        chart_popout_btn = QPushButton("Pop Out Chart")
        chart_popout_btn.clicked.connect(self.open_chart_window)
        chart_min_btn = QPushButton("Minimize")
        chart_min_btn.clicked.connect(lambda: self.market_window.showMinimized() if self.market_window else None)
        chart_max_btn = QPushButton("Maximize")
        chart_max_btn.clicked.connect(self._toggle_market_window_maximize)
        chart_controls.addWidget(chart_popout_btn)
        chart_controls.addWidget(chart_min_btn)
        chart_controls.addWidget(chart_max_btn)
        self.market_popup_chart = MiniChartWidget()
        self.market_popup_chart_summary = QLabel("Pick a symbol to load a live chart.")
        self.market_popup_chart_summary.setWordWrap(True)
        self.market_popup_chart_summary.setStyleSheet("color:#aebfd5;")

        activity_title = QLabel("Market Activity")
        activity_title.setStyleSheet("color:#7fd1ff; font-size:16px; font-weight:700;")
        self.market_popup_activity = QTextEdit()
        self.market_popup_activity.setReadOnly(True)
        self.market_popup_activity.setMinimumWidth(360)

        task_title = QLabel("Market Task Snapshot")
        task_title.setStyleSheet("color:#8aff8a; font-size:16px; font-weight:700;")
        self.market_popup_task_view = QTextEdit()
        self.market_popup_task_view.setReadOnly(True)
        self.market_popup_task_view.setMinimumWidth(360)

        side_layout.addWidget(chart_title)
        side_layout.addLayout(chart_controls)
        side_layout.addWidget(self.market_popup_chart)
        side_layout.addWidget(self.market_popup_chart_summary)
        side_layout.addWidget(activity_title)
        side_layout.addWidget(self.market_popup_activity, 1)
        side_layout.addWidget(task_title)
        side_layout.addWidget(self.market_popup_task_view, 1)

        body.addWidget(side_panel, 1)

        outer.addLayout(header)
        outer.addLayout(body, 1)

        self.market_window.closed.connect(self._reattach_market_workspace)
        self.market_window.show()
        self._sync_market_popup_views()
        self._update_chart_timeframe_buttons()
        self.refresh_clock_labels()
        current_symbol = self.market_symbol_input.text().strip().upper()
        if current_symbol:
            self.refresh_market_chart(current_symbol, timeframe=self.market_chart_timeframe or "swing")
        self.market_window.raise_()
        self.market_window.activateWindow()

    def _handle_tab_double_click(self, index):
        if index < 0:
            return
        widget = self.tabs.widget(index)
        if widget and widget.property("tab_id") == self.market_tab_id:
            self.open_market_window()

    def _detach_market_workspace(self):
        if self.market_workspace is None:
            return
        parent = self.market_workspace.parentWidget()
        if parent is None:
            return
        parent_layout = parent.layout()
        if parent_layout is not None:
            parent_layout.removeWidget(self.market_workspace)
        self.market_workspace.setParent(None)

    def _reattach_market_workspace(self):
        self.create_market_tab(make_current=False)
        container = self.chat_tabs[self.market_tab_id]["container"]
        layout = container.layout()
        if layout.indexOf(self.market_workspace) == -1:
            layout.insertWidget(1, self.market_workspace)
            layout.setStretch(2, 1)
        self._close_chart_window()
        if self.market_window is not None:
            self.market_window.deleteLater()
            self.market_window = None
        self.market_popup_activity = None
        self.market_popup_task_view = None
        self.market_popup_mode = None
        self.market_popup_clock = None
        self.market_popup_chart = None
        self.market_popup_chart_summary = None
        self.market_chart_buttons = {}

    def _close_market_window(self):
        if self.market_window is not None:
            self.market_window.close()

    def _sync_market_popup_views(self):
        if self.market_window is None or self.market_popup_activity is None:
            return

        self.market_popup_mode.setText(f"Mode: {ai_router.get_mode().title()}")
        self.refresh_clock_labels()

        market_tab = self.chat_tabs.get(self.market_tab_id)
        if market_tab:
            self.market_popup_activity.setHtml(market_tab["chat"].toHtml())

        market_task = None
        if market_tab:
            for task_id in reversed(market_tab["task_ids"]):
                task = get_task(task_id)
                if task:
                    market_task = task
                    break

        if not market_task:
            self.market_popup_task_view.setPlainText("No active market task yet.")
            return

        lines = [
            f"Task ID: {market_task['id']}",
            f"Goal: {market_task['message']}",
            f"Status: {market_task['status']}",
            "",
            "Latest result:",
            market_task.get("result", "") or "No result yet.",
        ]
        self.market_popup_task_view.setPlainText("\n".join(lines))

    def refresh_clock_labels(self):
        ist_now = datetime.now(ZoneInfo("Asia/Calcutta")).strftime("IST %d %b %Y  %I:%M:%S %p")
        if self.clock_label is not None:
            self.clock_label.setText(ist_now)
        if self.market_popup_clock is not None:
            self.market_popup_clock.setText(ist_now)
        if self.market_chart_popup_clock is not None:
            self.market_chart_popup_clock.setText(ist_now)

    def _toggle_market_window_maximize(self):
        if self.market_window is None:
            return
        if self.market_window.isMaximized():
            self.market_window.showNormal()
        else:
            self.market_window.showMaximized()

    def close_chat_tab(self, index):
        widget = self.tabs.widget(index)
        tab_id = widget.property("tab_id")

        if tab_id == self.market_tab_id or self.tabs.count() == 1:
            return

        self.chat_tabs.pop(tab_id, None)
        self.tabs.removeTab(index)

    def current_tab_id(self):
        widget = self.tabs.currentWidget()
        return widget.property("tab_id")

    def _chat_widget(self, tab_id):
        return self.chat_tabs[tab_id]["chat"]

    def _append_html(self, tab_id, markup):
        chat = self._chat_widget(tab_id)
        cursor = chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(markup)
        cursor.insertBlock()
        chat.setTextCursor(cursor)
        chat.ensureCursorVisible()

    def _message_card(self, title, body, accent, background):
        return (
            f"<div style='margin: 8px 0;'>"
            f"<div style='display:inline-block; max-width: 92%; "
            f"background:{background}; border:1px solid {accent}; border-radius:14px; "
            f"padding:10px 12px;'>"
            f"<div style='color:{accent}; font-weight:700; margin-bottom:4px;'>{html.escape(title)}</div>"
            f"<div style='color:#eef3fb; white-space:pre-wrap;'>{html.escape(body)}</div>"
            f"</div></div>"
        )

    def _format_token_for_display(self, token):
        cleaned = re.sub(r"\[Task [^\]]+\]\s*", "", token).replace("\r", "")

        if not cleaned.strip():
            return ""

        hidden_messages = {
            "Executing device command...",
            "Executing system command...",
            "Thinking...",
            "Searching...",
            "Looking...",
            "Handling file command...",
            "Planning...",
            "Preparing content...",
            "Saving saved output...",
            "Checking memory...",
            "Completed",
        }

        if cleaned.strip() in hidden_messages:
            return ""

        return cleaned

    def _format_token_for_speech(self, token):
        cleaned = self._format_token_for_display(token).strip()

        if not cleaned:
            return ""

        if cleaned.lower().startswith("saved to "):
            return "I saved it."

        return cleaned

    def add_chat(self, tab_id, text):
        if text.startswith("[System]"):
            body = text.replace("[System]", "", 1).strip()
            self._append_html(tab_id, self._message_card("System", body, "#7fd1ff", "#14212c"))
            self._sync_market_popup_views()
            return

        if text.startswith("You (voice):"):
            body = text.split(":", 1)[1].strip()
            self._append_html(tab_id, self._message_card("You (voice)", body, "#ffd36b", "#2a2413"))
            self._sync_market_popup_views()
            return

        if text.startswith("You:"):
            body = text.split(":", 1)[1].strip()
            self._append_html(tab_id, self._message_card("You", body, "#7ce0a3", "#14261d"))
            self._sync_market_popup_views()
            return

        self._append_html(tab_id, self._message_card("Irish", text, "#7da6ff", "#1a2030"))
        self._sync_market_popup_views()

    def start_response(self, tab_id):
        chat = self._chat_widget(tab_id)
        cursor = chat.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertHtml(
            "<div style='margin: 8px 0;'>"
            "<div style='display:inline-block; max-width: 92%; background:#1a2030; "
            "border:1px solid #7da6ff; border-radius:14px; padding:10px 12px;'>"
            "<div style='color:#7da6ff; font-weight:700; margin-bottom:4px;'>Irish</div>"
            "<div style='color:#eef3fb; white-space:pre-wrap;'>"
        )
        chat.setTextCursor(cursor)
        chat.ensureCursorVisible()
        self.chat_tabs[tab_id]["response_open"] = True

    def update_stream(self, tab_id, token):
        chat = self._chat_widget(tab_id)
        cursor = chat.textCursor()
        cursor.insertText(token)
        chat.setTextCursor(cursor)
        chat.ensureCursorVisible()
        self._sync_market_popup_views()

    def stream_finished(self, tab_id):
        tab = self.chat_tabs.get(tab_id)
        if not tab or not tab["response_open"]:
            return

        chat = tab["chat"]
        cursor = chat.textCursor()
        cursor.insertHtml("</div></div></div>")
        cursor.insertBlock()
        chat.setTextCursor(cursor)
        tab["response_open"] = False

        if tab["active_tasks"] > 0:
            tab["active_tasks"] -= 1

        if tab["active_tasks"] == 0:
            idle_status = "Market Desk" if tab_id == self.market_tab_id else "Ready"
            self.set_tab_status(tab_id, idle_status)
            if tab_id == self.market_tab_id:
                self.refresh_market_watchlist()
        self._sync_market_popup_views()

    def set_tab_status(self, tab_id, status):
        tab = self.chat_tabs.get(tab_id)
        if not tab:
            return

        styles = {
            "Ready": "color:#9ac6ff; background:#132035;",
            "Working": "color:#ffd782; background:#2f2410;",
            "Listening": "color:#89d8a8; background:#14261d;",
            "Market Desk": "color:#ffd782; background:#2c2010;",
        }
        tab["status"].setText(status)
        tab["status"].setStyleSheet(
            f"{styles.get(status, styles['Ready'])} padding:4px 10px; border-radius:10px; font-weight:600;"
        )

        for index in range(self.tabs.count()):
            widget = self.tabs.widget(index)
            if widget.property("tab_id") == tab_id:
                base = tab.get("title", self.tabs.tabText(index).split(" • ")[0])
                suffix = "" if status in {"Ready", "Market Desk"} else f" • {status}"
                self.tabs.setTabText(index, base + suffix)
                break

    def set_voice_active(self, active):
        self.voice_active = active
        self.mic_btn.setEnabled(not active)
        if active:
            self.set_tab_status(self.current_tab_id(), "Listening")
        else:
            current = self.current_tab_id()
            if self.chat_tabs[current]["active_tasks"] == 0:
                idle_status = "Market Desk" if current == self.market_tab_id else "Ready"
                self.set_tab_status(current, idle_status)

    def toggle_mode(self):
        if ai_router.get_mode() == "offline":
            ai_router.set_mode("online")
            self.add_chat(self.current_tab_id(), "[System] Switched to Online mode.")
        else:
            ai_router.set_mode("offline")
            self.add_chat(self.current_tab_id(), "[System] Switched to Offline mode.")

        self.refresh_mode_ui()

    def refresh_mode_ui(self):
        mode = ai_router.get_mode()

        if mode == "online":
            self.mode_btn.setText("Switch to Offline")
            self.mode_status.setText("Online")
            self.mode_status.setStyleSheet(
                "color: #82b1ff; font-weight: 700; background:#142746; padding:4px 10px; border-radius:10px;"
            )
        else:
            self.mode_btn.setText("Switch to Online")
            self.mode_status.setText("Offline")
            self.mode_status.setStyleSheet(
                "color: #89d8a8; font-weight: 700; background:#14261d; padding:4px 10px; border-radius:10px;"
            )
        self.refresh_task_panel()
        self._sync_market_popup_views()

    def refresh_task_panel(self):
        task = self._current_tab_task()

        if not task:
            self.task_subtitle.setText("No active task yet.")
            self.task_view.setPlainText(
                "When Irish starts a planned task in this chat, you will see the current role, shared notes, and recent results here."
            )
            return

        self.task_subtitle.setText(
            f"{task['agent'].title()} task • {task['status']} • updated {task['updated_at']}"
        )

        lines = [
            f"Task ID: {task['id']}",
            f"Goal: {task['message']}",
            "",
            "Sub-agents:",
        ]

        sub_agents = task.get("sub_agents", {})
        if sub_agents:
            for profile in sub_agents.values():
                lines.append(
                    f"- {profile['role']}: {profile['objective']}"
                )
                if profile.get("last_output"):
                    lines.append(f"  Last output: {profile['last_output']}")
        else:
            lines.append("- No sub-agents yet")

        lines.append("")
        lines.append("Shared context:")

        shared_context = task.get("shared_context", [])
        if shared_context:
            for entry in shared_context[-8:]:
                lines.append(f"- {entry['agent']} ({entry['kind']}): {entry['content']}")
        else:
            lines.append("- No shared context yet")

        if task.get("result"):
            lines.append("")
            lines.append("Latest result:")
            lines.append(task["result"])

        self.task_view.setPlainText("\n".join(lines))
        self._sync_market_popup_views()

    def _current_tab_task(self):
        tab_id = self.current_tab_id()
        tab = self.chat_tabs.get(tab_id)
        if not tab:
            return None

        latest_task = None
        for task_id in reversed(tab["task_ids"]):
            task = get_task(task_id)
            if task:
                latest_task = task
                break

        return latest_task

    def _target_tab_for_new_task(self):
        current = self.current_tab_id()
        if self.chat_tabs[current]["active_tasks"] > 0:
            return self.create_chat_tab(make_current=True)
        return current

    def _start_task(self, tab_id, message, is_voice=False):
        if tab_id == self.market_tab_id:
            symbol = extract_symbol(message)
            if symbol:
                self.market_symbol_input.setText(symbol)
                self.refresh_market_cards(symbol)

        self.chat_tabs[tab_id]["active_tasks"] += 1
        label = "You (voice)" if is_voice else "You"
        self.stream.add_chat.emit(tab_id, f"{label}: {message}")
        self.stream.start_response.emit(tab_id)
        self.stream.update_tab_status.emit(tab_id, "Working")

        threading.Thread(
            target=self.process_message,
            args=(message, tab_id),
            daemon=True,
        ).start()

    def send_message(self):
        message = self.input.text().strip()
        if not message:
            return

        lowered = message.lower()
        if lowered in {"open market window", "open market desk", "show market window"}:
            self.input.clear()
            self.open_market_window()
            return
        if lowered in {"dock market window", "close market window", "return market window"}:
            self.input.clear()
            self._close_market_window()
            return

        self.input.clear()
        tab_id = self._target_tab_for_new_task()
        self._start_task(tab_id, message, is_voice=False)

    def voice_message(self):
        if self.voice_active:
            return

        self.stream.set_voice_active.emit(True)
        threading.Thread(target=self._capture_voice_message, daemon=True).start()

    def _capture_voice_message(self):
        try:
            text = listen()
            if text:
                tab_id = self._target_tab_for_new_task()
                self._start_task(tab_id, text, is_voice=True)
            else:
                self.stream.add_chat.emit(self.current_tab_id(), "Irish: I couldn't hear you clearly.")
        finally:
            self.stream.set_voice_active.emit(False)

    def wake_listener(self):
        while True:
            try:
                listen_for_wake_word()
                if self.voice_active:
                    continue
                self.stream.set_voice_active.emit(True)
                text = listen()
                if text:
                    tab_id = self._target_tab_for_new_task()
                    self._start_task(tab_id, text, is_voice=True)
            except Exception as exc:
                print("Wake listener error:", exc)
            finally:
                self.stream.set_voice_active.emit(False)

    def process_message(self, message, tab_id):
        try:
            for token in process_command(message):
                task_match = re.search(r"\[Task ([^\]]+)\]", token)
                if task_match:
                    task_id = task_match.group(1)
                    tab = self.chat_tabs.get(tab_id)
                    if tab is not None and task_id not in tab["task_ids"]:
                        tab["task_ids"].append(task_id)

                display_token = self._format_token_for_display(token)
                speech_token = self._format_token_for_speech(token)

                if display_token:
                    self.stream.new_token.emit(tab_id, display_token)

                if speech_token:
                    speak(speech_token)
        finally:
            self.stream.refresh_mode.emit()
            self.stream.finished.emit(tab_id)
            self.stream.refresh_task_panel.emit()


def main():
    app = QApplication(sys.argv)
    window = IrishUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
