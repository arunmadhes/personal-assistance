import html
import re
import threading

import ai_router
from agent_manager import get_task
from market_data import extract_symbol
from services.agent_service import stream_agent_response
from voice_input import listen
from voice_output import speak
from wake_word import listen_for_wake_word


class ChatTaskMixin:

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
                lines.append(f"- {profile['role']}: {profile['objective']}")
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
            source = "voice" if self.voice_active else "chat_ui"
            metadata = {
                "market_tab": tab_id == self.market_tab_id,
            }

            for token in stream_agent_response(message, source=source, tab_id=tab_id, metadata=metadata):
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
