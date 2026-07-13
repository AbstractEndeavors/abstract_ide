#!/usr/bin/env python3
"""
agent.py — real-time agentic chat for the Services tab.

The model streams its reasoning token-by-token into a transcript and may
propose shell commands to inspect the host on its own initiative. Every
proposed command is human-gated: it appears in an approval bar with Run / Skip
and nothing touches the box until the operator clicks Run. Approved commands
execute over the tab's existing SSH connection and their output is fed back to
the model, which continues until it produces a prose answer.

Protocol is a plain `RUN: <cmd>` line (see AGENT_SYSTEM in main.py) rather than
OpenAI tool-calling, so it works with any OpenAI-compatible endpoint, including
small local models.

Safety model — deliberately explicit: the scope is a full shell, and the ONLY
backstop is the human approval gate. Every command is shown before it runs and
Skip is the default. As defence-in-depth for shared or less-trusted use, set
SERVICES_TAB_READONLY=1 to hard-block control-verb commands at the UI (the
operator cannot approve them); the default is off, preserving full-shell use
for a trusted operator on their own box.
"""
import html
import os
import threading

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QTextCursor
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QTextEdit,
    QVBoxLayout, QWidget,
)

from .main import AGENT_SYSTEM, llm_stream, think_suffix

# Opt-in defence-in-depth: when set, control-verb commands cannot be approved.
READONLY = os.environ.get("SERVICES_TAB_READONLY", "").lower() in ("1", "true", "yes")

# Verbs that mutate state — highlighted red in the approval bar so a control
# action can't be waved through as if it were a read.
DANGER_TOKENS = (
    "rm ", "rm-", "kill", "pkill", "reboot", "shutdown", "mkfs", "dd ",
    "chmod", "chown", "truncate", "> ", ">>", "tee ", "mv ", "iptables",
    "ufw ", "systemctl stop", "systemctl restart", "systemctl disable",
    "systemctl mask", "systemctl start", "systemctl kill",
)

MAX_STEPS = 8              # commands the model may chain per turn
TOOL_OUTPUT_CAP = 6000     # chars of command output fed back to the model


def parse_run(text):
    """Return the command from the first `RUN:` line, or None for a final answer."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("RUN:"):
            return stripped[4:].strip()
    return None


def looks_dangerous(cmd):
    low = " " + cmd.lower()
    return any(tok in low for tok in DANGER_TOKENS)


class AgentThread(QThread):
    """Drive one chat turn: stream, propose commands, run approved ones, repeat."""
    token = pyqtSignal(str)         # streamed assistant text
    propose = pyqtSignal(str)       # a command awaiting Run/Skip
    ran = pyqtSignal(str, str)      # (cmd, output) after an approved run
    skipped = pyqtSignal(str)       # (cmd) the operator declined
    answer = pyqtSignal()           # turn finished with a prose answer
    error = pyqtSignal(str)

    def __init__(self, ssh, llm_api, model, api_key, messages, parent=None):
        super().__init__(parent)
        self._ssh = ssh
        self._llm_api = llm_api
        self._model = model
        self._api_key = api_key
        self._messages = messages          # shared history (mutated in-thread)
        self._decision = None
        self._gate = threading.Event()

    def approve(self, run):
        """Called from the GUI thread to release a pending command."""
        self._decision = bool(run)
        self._gate.set()

    def _stream_turn(self):
        """Stream one assistant reply, emitting display tokens. Stops early at a
        completed RUN: line so the model can't ramble a hallucinated OUTPUT past
        its own command (and we stop paying for those tokens)."""
        text = ""
        emitted = 0
        for piece in llm_stream(self._llm_api, self._messages,
                                api_key=self._api_key, model=self._model):
            text += piece
            cmd = parse_run(text)
            if cmd:
                idx = text.upper().index("RUN:")
                nl = text.find("\n", idx)
                if nl != -1:                       # the RUN: line is complete
                    self.token.emit(text[emitted:nl])
                    return text, cmd
            self.token.emit(text[emitted:])
            emitted = len(text)
        return text, parse_run(text)

    def run(self):
        try:
            for _ in range(MAX_STEPS):
                text, cmd = self._stream_turn()
                self._messages.append({"role": "assistant", "content": text})

                if not cmd:
                    self.answer.emit()
                    return

                self._decision = None
                self._gate.clear()
                self.propose.emit(cmd)
                self._gate.wait()

                if self._decision:
                    output = self._ssh.run_command(cmd) or "(no output)"
                    self.ran.emit(cmd, output)
                    self._messages.append(
                        {"role": "user", "content": "OUTPUT:\n" + output[:TOOL_OUTPUT_CAP]})
                else:
                    self.skipped.emit(cmd)
                    self._messages.append({"role": "user", "content":
                        "The operator DENIED that command. Do not retry it; take a "
                        "different approach or give your best answer with what you have."})
            # Ran out of steps — ask for a wrap-up.
            self._messages.append({"role": "user", "content":
                "Step limit reached. Summarize your findings and recommendations now."})
            for piece in llm_stream(self._llm_api, self._messages,
                                    api_key=self._api_key, model=self._model):
                self.token.emit(piece)
            self.answer.emit()
        except Exception as exc:
            self.error.emit(str(exc))


class AgentChatDialog(QDialog):
    """A modeless chat panel that streams the model and gates its commands."""

    def __init__(self, title, ssh, llm_selection, messages, autostart=False,
                 deep_provider=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AI Chat — %s" % title)
        self.setModal(False)
        self.resize(820, 640)
        self._ssh = ssh
        self._llm_selection = llm_selection    # () -> (api, model, key)
        self._deep_provider = deep_provider    # () -> bool ; None = always deep
        self._messages = messages              # includes the system prompt
        self._thread = None
        self._assistant_open = False

        layout = QVBoxLayout(self)
        self.transcript = QTextEdit()
        self.transcript.setReadOnly(True)
        # Force a fixed, readable colour scheme so the transcript (and the
        # command-output blocks) stay legible under a dark system theme, where
        # the inherited default text colour is white — which was rendering the
        # log output as white-on-near-white.
        self.transcript.setStyleSheet(
            "QTextEdit { background:#ffffff; color:#1a1a1a; }")
        layout.addWidget(self.transcript, 1)

        # Approval bar — hidden until the model proposes a command.
        self.pending = QWidget()
        pend = QHBoxLayout(self.pending)
        pend.setContentsMargins(0, 0, 0, 0)
        pend.addWidget(QLabel("Run command?"))
        self.cmd_label = QLineEdit()
        self.cmd_label.setReadOnly(True)
        self.cmd_label.setStyleSheet("font-family: monospace; background:#ffffff; color:#1a1a1a;")
        pend.addWidget(self.cmd_label, 1)
        self.run_btn = QPushButton("Run")
        self.run_btn.clicked.connect(lambda: self._approve(True))
        self.skip_btn = QPushButton("Skip")
        self.skip_btn.clicked.connect(lambda: self._approve(False))
        pend.addWidget(self.run_btn)
        pend.addWidget(self.skip_btn)
        self.pending.setVisible(False)
        layout.addWidget(self.pending)

        row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask about this service, or tell the AI what to inspect…")
        self.input.returnPressed.connect(self._send)
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._send)
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)
        layout.addLayout(row)

        self.status = QLabel("")
        layout.addWidget(self.status)

        if autostart:
            # The seed already carries the first user message (the analysis
            # request); echo it and run the opening turn immediately.
            for m in self._messages:
                if m["role"] == "user":
                    self._append_html("<b>You:</b> analyze this %s<br>"
                                      % ("process" if "PROCESS" in m["content"] else "service"))
                    break
            self._start_turn(seed=True)

    # -- transcript helpers --
    def _append_html(self, fragment):
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)
        self.transcript.insertHtml(fragment)
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)

    def _append_text(self, text):
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)
        self.transcript.insertPlainText(text)
        self.transcript.moveCursor(QTextCursor.MoveOperation.End)

    # -- turn lifecycle --
    def _send(self):
        if self._thread and self._thread.isRunning():
            return
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._append_html("<br><b>You:</b> %s<br>" % html.escape(text))
        deep = self._deep_provider() if self._deep_provider else True
        self._messages.append({"role": "user", "content": text + think_suffix(deep)})
        self._start_turn()

    def _start_turn(self, seed=False):
        api, model, key = self._llm_selection()
        self._set_busy(True)
        self.status.setText("Thinking… (%s)" % (model or "server default"))
        self._assistant_open = False
        self._thread = AgentThread(self._ssh, api, model, key, self._messages, parent=self)
        self._thread.token.connect(self._on_token)
        self._thread.propose.connect(self._on_propose)
        self._thread.ran.connect(self._on_ran)
        self._thread.skipped.connect(self._on_skipped)
        self._thread.answer.connect(self._on_answer)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_token(self, piece):
        if not self._assistant_open:
            self._append_html("<b>AI:</b> ")
            self._assistant_open = True
        self._append_text(piece)

    def _on_propose(self, cmd):
        self._assistant_open = False
        self._append_html("<br>")
        self.cmd_label.setText(cmd)
        danger = looks_dangerous(cmd)
        blocked = danger and READONLY
        self.cmd_label.setStyleSheet(
            "font-family: monospace; background:#ffffff; color: %s;"
            % ("#b00000" if danger else "#111111"))
        if blocked:
            self.run_btn.setText("Blocked (read-only)")
            self.run_btn.setEnabled(False)
        else:
            self.run_btn.setText("Run (control action)" if danger else "Run")
            self.run_btn.setEnabled(True)
        self.pending.setVisible(True)
        self.skip_btn.setDefault(True)     # default to the safe choice
        self.skip_btn.setFocus()
        self.status.setText("Control action blocked by read-only mode — Skip to continue."
                            if blocked else "Waiting for approval…")

    def _approve(self, ok):
        self.pending.setVisible(False)
        if not ok:
            self._append_html("<i>— command skipped —</i><br>")
        if self._thread:
            self._thread.approve(ok)
        self.status.setText("Thinking…")

    def _on_ran(self, cmd, output):
        # explicit dark text on a light block so command output is always legible
        self._append_html(
            "<pre style='background:#f4f4f4; color:#1a1a1a; padding:4px; "
            "border-left:3px solid #bbbbbb;'>$ %s\n%s</pre>"
            % (html.escape(cmd), html.escape(output[:4000])))

    def _on_skipped(self, cmd):
        pass  # note already written in _approve

    def _on_answer(self):
        self._append_html("<br>")
        self._set_busy(False)
        self.status.setText("Ready.")

    def _on_error(self, msg):
        self._append_html("<br><span style='color:#b00000;'>[error: %s]</span><br>"
                          % html.escape(msg))
        self._set_busy(False)
        self.status.setText("Error.")

    def _set_busy(self, busy):
        self.input.setEnabled(not busy)
        self.send_btn.setEnabled(not busy)
        if not busy:
            self.input.setFocus()

    def closeEvent(self, event):
        # Release a thread blocked on approval so it can exit cleanly.
        if self._thread and self._thread.isRunning():
            self._thread.approve(False)
            self._thread.wait(2000)
        event.accept()
