from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class MarketPanelMixin:
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
