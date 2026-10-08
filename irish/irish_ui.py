import sys
import threading
from datetime import datetime
from zoneinfo import ZoneInfo

from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import ai_router
from agent_manager import get_task
from market_data import extract_timeframe
from services.market_service import (
    build_market_cards_payload,
    build_market_chart_payload,
    build_market_watchlist_payload,
)
from ui.chat_panel import ChatTaskMixin
from ui.market_panel import MarketPanelMixin
from ui.market_widgets import ChartPopupWindow, MarketPopupWindow, MiniChartWidget
from watchlist import remove_from_watchlist


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


class IrishUI(ChatTaskMixin, MarketPanelMixin, QWidget):

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
            payload = build_market_cards_payload(current_symbol, token)
            self.stream.market_cards_ready.emit(payload)

        threading.Thread(target=worker, daemon=True).start()

    def refresh_market_watchlist(self):
        self.market_watchlist_token += 1
        token = self.market_watchlist_token

        def worker():
            payload = build_market_watchlist_payload(token, limit=12, timeframe="swing")
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
            payload = build_market_chart_payload(current_symbol, timeframe, token)
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

def main():
    app = QApplication(sys.argv)
    window = IrishUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
