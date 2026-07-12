#!/usr/bin/env python3
"""
servicesTab — remote systemd service viewer as an ideConsole tab.

PyQt6 port of abstract_parallels.services_mgr.servicesManager (the 2026-07-11
revision): one batched collection per refresh via remote_collector.py shipped
over a single SSH exec, live per-unit CPU%, non-systemd "stray" rows, sudo
password over stdin (never on argv).

Differences from the standalone tool:
  * QWidget tab instead of QMainWindow, so it embeds in ideConsole.
  * Collection runs in a QThread — an SSH round-trip must not freeze the
    whole IDE.
  * paramiko is imported lazily so the IDE still opens without it; the tab
    reports the missing dependency on Connect instead.
"""
import json
import os
import shlex
import urllib.error
import urllib.parse
import urllib.request

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox,
    QPushButton, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget,
)

_HERE = os.path.dirname(os.path.abspath(__file__))
COLLECTOR_PATH = os.path.join(_HERE, "remote_collector.py")

COLUMNS = ["Type", "Service / Process", "State", "PID", "CPU %", "Mem (MB)",
           "Procs", "Host:Port", "Uptime", "Actions", "Logs", "AI"]
COLUMN_WIDTHS = [60, 300, 95, 70, 70, 90, 60, 130, 110, 330, 60, 80]
# Columns whose values must sort numerically rather than lexically.
NUMERIC_COLS = {3, 4, 5, 6, 8}

# ─────────────────────────── LLM configuration ────────────────────────────
# This is a provider-neutral OpenAI-compatible client. It is NOT tied to any
# particular LLM service — point it at whatever /v1 endpoint you run: a local
# llama.cpp / vLLM / Ollama server, a cloud API, or a self-hosted gateway.
# Bring your own model; nothing here assumes a specific backend.
#
# Configuration (all optional, all overridable in the connect dialog):
#   LLM_API_BASE     base URL, ideally ending in /v1   (default: local llama.cpp)
#   LLM_API_KEY      Bearer token, if your endpoint requires one
#   LLM_API_CHOICES  comma-separated extra endpoints to prefill the dropdown
# For backwards compatibility a few legacy env names / key files are also read.
def _first_env(*names):
    for name in names:
        val = os.environ.get(name)
        if val:
            return val
    return ""


def _config_val(filename):
    """Read a single value from ~/.config/services_tab/<filename>, or ''.
    Lets an install pin its own default endpoint/model without env vars or
    touching the (PyPI-published, provider-neutral) source."""
    try:
        with open(os.path.expanduser("~/.config/services_tab/" + filename)) as fh:
            return fh.read().strip()
    except OSError:
        return ""


def _default_api_key():
    """Resolve a Bearer key from env or a key file. Never hardcoded — this
    package publishes to PyPI, so no credential may live in the source."""
    key = _first_env("LLM_API_KEY", "OPENAI_API_KEY", "HUGPY_API_KEY")
    if key:
        return key
    for path in ("~/.config/services_tab/api_key", "~/.config/hugpy/api_key"):
        try:
            with open(os.path.expanduser(path)) as fh:
                found = fh.read().strip()
                if found:
                    return found
        except OSError:
            continue
    return ""


# Common local defaults so the dropdown is useful out of the box on a fresh
# install; the user's own endpoint (from env) is prepended and selected. 8081
# leads because that is where a local llama-server is commonly run here; 8080 is
# llama.cpp's stock port and 11434 is Ollama.
_LOCAL_DEFAULTS = ["http://localhost:8081/v1",    # local llama-server (primary)
                   "http://localhost:8080/v1",    # llama.cpp stock port
                   "http://localhost:11434/v1"]   # Ollama
LLM_API_DEFAULT = (_first_env("LLM_API_BASE", "HUGPY_LLM_API")
                   or _config_val("endpoint") or _LOCAL_DEFAULTS[0])
LLM_API_CHOICES = list(dict.fromkeys(         # dedup, preserve order
    [LLM_API_DEFAULT]
    + [c.strip() for c in _first_env("LLM_API_CHOICES").split(",") if c.strip()]
    + _LOCAL_DEFAULTS))
LLM_API_KEY_DEFAULT = _default_api_key()

# Optional per-install model preferences (env or ~/.config/services_tab/*). The
# source stays provider-neutral: an install pins its own good model here, e.g.
# LLM_MODEL=flux2-klein-9b-uncensored-text-encoder. LLM_MODEL is auto-selected;
# LLM_PREFERRED_MODELS (comma-sep) float to the top of the dropdown.
LLM_MODEL_DEFAULT = _first_env("LLM_MODEL") or _config_val("model")
LLM_PREFERRED = [m.strip() for m in
                 (_first_env("LLM_PREFERRED_MODELS") or _config_val("preferred")
                  or LLM_MODEL_DEFAULT).split(",") if m.strip()]
# Token budget per analysis. Generous so a reasoning model can finish its
# answer instead of getting cut off mid-<think>; override via LLM_MAX_TOKENS.
LLM_MAX_TOKENS = int(_first_env("LLM_MAX_TOKENS") or _config_val("max_tokens") or "2200")
# Read timeout (seconds). A fleet that swaps models in/out of GPU on demand can
# spend a minute-plus cold-loading before the first token — by design, not a
# hang. This is a per-read socket timeout that resets on each streamed line /
# keepalive, so it caps only true silence. Generous; override via LLM_TIMEOUT.
LLM_TIMEOUT = int(_first_env("LLM_TIMEOUT") or _config_val("timeout") or "300")

# A model can chat if it lists a text-generation-ish task; entries with no
# task metadata (plain llama-server) are assumed chat-capable.
CHAT_TASKS = {"text-generation", "image-text-to-text", "text2text-generation"}


def think_suffix(deep):
    """Append to a user message to control reasoning. Qwen3-lineage models
    (and the hub) honor a `/no_think` directive to skip the <think> block for a
    fast, direct answer; deep mode leaves full reasoning on."""
    return "" if deep else "\n\n/no_think"

ANALYZE_PROMPT = """You are a senior Linux sysadmin reviewing one item from a systemd service audit.

{context}

Answer concisely under these headings:
PURPOSE: what this {kind} does, in one or two sentences.
HEALTH: is it healthy? Use the state, CPU/memory, uptime and log lines as evidence (crash loops, OOM, errors, restarts).
ANOMALIES: anything unusual or suspicious — unexpected paths (/tmp, /var/tmp, hidden dirs), miner-like CPU patterns, odd network ports, obfuscated names. Say NONE if clean.
ACTIONS: recommended next steps, or NONE if no action needed."""


def gather_service_context(run_sudo, item):
    """Collect unit file + journal tail for a service over SSH; returns prompt text.
    `run_sudo(cmd) -> (out, err)` is the transport."""
    name = item.get("name", "")
    unit, _ = run_sudo("systemctl cat %s" % name)
    journal, _ = run_sudo("journalctl -u %s -n 120 --no-pager" % name)
    facts = ("state=%s enabled=%s pid=%s cpu=%.1f%% mem=%.1fMB procs=%s port=%s uptime=%s"
             % (item.get("active_state", "?"), item.get("enabled"), item.get("pid"),
                float(item.get("cpu", 0)), float(item.get("mem", 0)),
                item.get("nprocs", 1), item.get("port") or "-", item.get("uptime", "?")))
    return ("SERVICE: %s\nRUNTIME: %s\n\nUNIT FILE:\n%s\n\nRECENT JOURNAL (tail):\n%s"
            % (name, facts, unit.strip()[:3000], journal.strip()[-5000:]))


def gather_stray_context(run_sudo, item):
    """Collect process facts for a non-systemd stray; returns prompt text."""
    pid = item.get("pid")
    ps_line, _ = run_sudo("ps -p %s -o pid,user,etime,%%cpu,%%mem,args --no-headers" % pid)
    links, _ = run_sudo("readlink /proc/%s/exe /proc/%s/cwd" % (pid, pid))
    cmdline, _ = run_sudo("tr '\\0' ' ' < /proc/%s/cmdline" % pid)
    facts = ("cgroup=%s cpu=%.1f%% mem=%.1fMB"
             % (item.get("cgroup", "?"), float(item.get("cpu", 0)), float(item.get("mem", 0))))
    return ("NON-SYSTEMD PROCESS (no owning .service): %s (pid %s)\nRUNTIME: %s\n"
            "PS: %s\nEXE / CWD:\n%s\nCMDLINE: %s"
            % (item.get("name"), pid, facts, ps_line.strip(), links.strip(), cmdline.strip()[:1000]))


# ─────────────────────── endpoint route resolution ────────────────────────
# Resolve the chat + models URLs for a configured base. A hugpy host advertises
# a route table at <origin>/endpoints, but it lists routes WITHOUT the /api
# blueprint prefix under which the real JSON API is actually served (the bare
# /v1/... GET is shadowed by the frontend SPA). So we discover the route *shape*
# from /endpoints, then PROBE candidate URLs (with and without /api) and keep the
# one that actually returns a model list. A plain llama.cpp/Ollama/cloud server
# has no /endpoints — its base + the OpenAI /v1 convention is probed directly.
# Provider-neutral, and cached per base so the probe cost is paid once.
_ROUTE_CACHE = {}   # base -> (chat_url, models_url)


def _origin(url):
    p = urllib.parse.urlsplit(url)
    if p.scheme and p.netloc:
        return "%s://%s" % (p.scheme, p.netloc)
    return url.rstrip("/")


def _conv(base):
    """OpenAI /v1 convention (chat_url, models_url) for a base."""
    return (base + ("/chat/completions" if base.endswith("/v1") else "/v1/chat/completions"),
            base + ("/models" if base.endswith("/v1") else "/v1/models"))


def _endpoints_paths(base, api_key="", timeout=4):
    """Route paths (models_path, chat_path) from a /endpoints table, or None."""
    origin = _origin(base)
    headers = {}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    for ep in (origin + "/endpoints", origin + "/api/endpoints"):
        try:
            with urllib.request.urlopen(urllib.request.Request(ep, headers=headers),
                                        timeout=timeout) as resp:
                data = json.loads(resp.read().decode(errors="replace"))
        except Exception:
            continue
        if not isinstance(data, list):
            continue
        chat = models = None
        for e in data:
            u = (e.get("url") or "").rstrip("/")
            methods = e.get("methods") or []
            if "<" in u:                               # skip templated routes
                continue
            if u.endswith("/chat/completions") and "POST" in methods:
                if chat is None or "/v1/" in u:
                    chat = u
            elif u.endswith("/models") and "GET" in methods and "/llm/" not in u:
                if models is None or "/v1/" in u:
                    models = u
        if chat and models:
            return models, chat
    return None


def _models_url_ok(url, api_key="", timeout=4):
    """True if url returns an OpenAI-style model list (dict with data/models)."""
    headers = {}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers),
                                    timeout=timeout) as resp:
            data = json.loads(resp.read().decode(errors="replace"))
        return isinstance(data, dict) and bool(data.get("data") or data.get("models"))
    except Exception:
        return False


def resolve_routes(base, api_key="", timeout=4):
    """(chat_url, models_url) for a base. Discovers the route shape from
    /endpoints when present, probes /api-prefixed and bare candidates plus the
    plain /v1 convention, and keeps the models URL that actually responds.
    Cached per base."""
    base = base.rstrip("/")
    if base in _ROUTE_CACHE:
        return _ROUTE_CACHE[base]
    origin = _origin(base)
    conv_chat, conv_models = _conv(base)
    # (models_url, chat_url) candidates, most-likely first.
    candidates = []
    disc = _endpoints_paths(base, api_key, timeout)
    if disc:
        mp, cp = disc                                  # e.g. /v1/models, /v1/chat/completions
        candidates.append((origin + "/api" + mp, origin + "/api" + cp))  # hugpy real mount
        candidates.append((origin + mp, origin + cp))                    # bare
    candidates.append((conv_models, conv_chat))        # OpenAI convention on the base
    seen = set()
    for models_url, chat_url in candidates:
        if models_url in seen:
            continue
        seen.add(models_url)
        if _models_url_ok(models_url, api_key, timeout):
            _ROUTE_CACHE[base] = (chat_url, models_url)
            return _ROUTE_CACHE[base]
    _ROUTE_CACHE[base] = (conv_chat, conv_models)      # nothing responded — use convention
    return _ROUTE_CACHE[base]


def llm_list_models(llm_api, api_key="", timeout=10):
    """List chat-capable model ids from a server's models route (see resolve_routes)."""
    _, url = resolve_routes(llm_api, api_key)
    headers = {}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode(errors="replace"))
    entries = data.get("data") or data.get("models") or []
    pinned_present, default_flagged, rest = [], [], []
    for e in entries:
        name = (e.get("id") or e.get("name") or "").strip()
        if not name:
            continue
        # A pinned model (LLM_PREFERRED) is always shown, even if its task tag
        # would exclude it — labels are unreliable by provenance, so an explicit
        # user preference overrides the tag filter (see flux2: a capable chat
        # model mislabeled by its upstream repo).
        if name in LLM_PREFERRED:
            pinned_present.append(name)
            continue
        tasks = set(e.get("tasks") or ([e["task"]] if e.get("task") else []))
        if tasks and not (tasks & CHAT_TASKS):
            continue
        # Some gateways mislabel media models as text-generation, so the filter
        # can't be airtight — float any server-flagged defaults after the pins.
        (default_flagged if e.get("media_default") else rest).append(name)
    # Preserve LLM_PREFERRED's own order at the very top.
    pinned = [m for m in LLM_PREFERRED if m in pinned_present]
    return pinned + default_flagged + rest


def llm_analyze(llm_api, context, kind, api_key="", model="", timeout=None,
                stream=True, on_chunk=None, deep=True):
    """POST the analysis prompt to an OpenAI-compatible /v1/chat/completions.

    Streams by default (most OpenAI-compatible servers support it) and returns
    the full accumulated text; pass on_chunk to observe deltas as they arrive. Falls
    back transparently if the server answers with a plain JSON completion.
    deep=False appends /no_think for a fast, direct answer."""
    if timeout is None:
        timeout = LLM_TIMEOUT
    url, _ = resolve_routes(llm_api, api_key)
    payload = {
        "model": model or "default",
        "messages": [{"role": "user",
                      "content": ANALYZE_PROMPT.format(context=context, kind=kind)
                      + think_suffix(deep)}],
        "temperature": 0.2,
        "max_tokens": LLM_MAX_TOKENS,
        "stream": bool(stream),
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        # Skip blank lines and SSE comments (the hub emits ": keepalive")
        # before deciding whether this is a stream or a plain JSON body.
        first = resp.readline().decode(errors="replace")
        while first and (not first.strip() or first.lstrip().startswith(":")):
            first = resp.readline().decode(errors="replace")
        if not first.lstrip().startswith("data:"):
            # non-streaming server: plain JSON body
            data = json.loads(first + resp.read().decode(errors="replace"))
            return data["choices"][0]["message"]["content"].strip()
        parts = []
        line = first
        while line:
            line = line.strip()
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    delta = json.loads(chunk)["choices"][0]["delta"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    delta = {}
                piece = delta.get("content") or ""
                if piece:
                    parts.append(piece)
                    if on_chunk:
                        on_chunk(piece)
            line = resp.readline().decode(errors="replace")
        return "".join(parts).strip()


def llm_stream(llm_api, messages, api_key="", model="", timeout=None,
               temperature=0.2, max_tokens=None):
    """Yield content deltas for a full chat `messages` array (SSE streaming).

    The agent chat uses this directly so it can carry multi-turn history and
    tool-result messages; keepalive comments and a plain-JSON fallback are
    handled like llm_analyze."""
    if timeout is None:
        timeout = LLM_TIMEOUT
    if max_tokens is None:
        max_tokens = LLM_MAX_TOKENS
    url, _ = resolve_routes(llm_api, api_key)
    payload = {
        "model": model or "default",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer %s" % api_key
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        for raw in resp:
            line = raw.decode(errors="replace").strip()
            if not line or line.startswith(":"):
                continue
            if not line.startswith("data:"):
                try:                                    # non-streaming fallback
                    data = json.loads(line)
                    yield data["choices"][0]["message"]["content"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass
                continue
            chunk = line[5:].strip()
            if chunk == "[DONE]":
                break
            try:
                delta = json.loads(chunk)["choices"][0]["delta"]
            except (json.JSONDecodeError, KeyError, IndexError):
                delta = {}
            piece = delta.get("content") or ""
            if piece:
                yield piece


# System prompt for the agent chat: the model can request shell commands, but
# every one is human-gated (see AgentChatDialog). Kept model-agnostic — a plain
# RUN: line, no OpenAI tool-calling, so even a small local model can drive it.
AGENT_SYSTEM = """You are a Linux systems-administration assistant embedded in a \
service monitor and connected to a remote host over SSH. You investigate systemd \
services and processes.

You may run shell commands on the host, but EVERY command you request is shown to \
a human operator who must approve it before it runs. To request a command, output \
a line in EXACTLY this form and then STOP immediately, emitting nothing after it:
RUN: <the shell command>

Never invent or assume a command's output — wait for it. After the operator runs \
it, the result comes back to you prefixed with OUTPUT:. You may then request \
another command or give your answer. If the operator denies a command, adapt.

Prefer read-only inspection (systemctl status/cat, journalctl, ps, ss, cat \
/proc/<pid>/*, ls, readlink, du). Only request state-changing commands (restart, \
stop, kill, edits) when the operator explicitly asks for them. Chain your own \
investigation across several commands when needed. When you have enough \
information, reply in prose with findings and concrete recommendations — no RUN: \
line in a final answer."""


class NumericTableWidgetItem(QTableWidgetItem):
    """A cell that displays formatted text but sorts by an underlying number.

    Without this, "9.0" sorts above "80.0" (string order) and the CPU/Mem
    columns are useless to sort by.
    """

    def __init__(self, text, value):
        super().__init__(text)
        self._value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            try:
                return self._value < other._value
            except TypeError:
                pass
        return super().__lt__(other)


def _uptime_seconds(text):
    """Turn '2h 32m 17s' into a sortable integer; '' / 'N/A' sort lowest."""
    if not text or text == "N/A":
        return -1
    secs = 0
    for part in text.split():
        try:
            if part.endswith("h"):
                secs += int(part[:-1]) * 3600
            elif part.endswith("m"):
                secs += int(part[:-1]) * 60
            elif part.endswith("s"):
                secs += int(part[:-1])
        except ValueError:
            continue
    return secs


# ─────────────────────────────── SSH layer ────────────────────────────────
class SSHClient:
    """Thin paramiko wrapper. Read collection needs no sudo; control actions
    pass the sudo password over stdin rather than echoing it on argv."""

    def __init__(self, hostname, username, password=None, key_path=None,
                 sudo_password=None, port=22):
        import paramiko  # deferred so the IDE loads without it
        self._paramiko = paramiko
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_path = key_path or None
        self.sudo_password = sudo_password
        self.port = int(port or 22)
        self.connect()

    def connect(self):
        try:
            kwargs = {"username": self.username, "port": self.port, "timeout": 15}
            if self.key_path:
                kwargs["key_filename"] = os.path.expanduser(self.key_path)
            if self.password:
                kwargs["password"] = self.password
            self.client.connect(self.hostname, **kwargs)
        except Exception as exc:
            raise ConnectionError("SSH connection failed: %s" % exc)

    def run(self, command, timeout=30):
        """Run a plain (unprivileged) command; return (stdout, stderr)."""
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        return stdout.read().decode(errors="replace"), stderr.read().decode(errors="replace")

    def run_sudo(self, command, timeout=30):
        """Run a command under sudo, feeding the password via stdin (-S)."""
        if not self.sudo_password:
            # No password supplied → assume NOPASSWD sudo or key-privileged.
            return self.run("sudo -n %s" % command, timeout=timeout)
        chan = self.client.get_transport().open_session()
        chan.settimeout(timeout)
        chan.exec_command("sudo -S -p '' %s" % command)
        chan.sendall((self.sudo_password + "\n").encode())
        out, err = b"", b""
        while True:
            if chan.recv_ready():
                out += chan.recv(65536)
            if chan.recv_stderr_ready():
                err += chan.recv_stderr(65536)
            if chan.exit_status_ready() and not chan.recv_ready() and not chan.recv_stderr_ready():
                break
        return out.decode(errors="replace"), err.decode(errors="replace")

    def collect_snapshot(self, interval=0.3):
        """Ship the collector to the remote python3 and parse its JSON."""
        with open(COLLECTOR_PATH, "r") as fh:
            script = fh.read()
        sftp = None
        remote = "/tmp/.services_mgr_collector.py"
        try:
            sftp = self.client.open_sftp()
            with sftp.file(remote, "w") as rf:
                rf.write(script)
            out, err = self.run("python3 %s %s" % (remote, interval), timeout=40)
        finally:
            if sftp is not None:
                try:
                    sftp.remove(remote)
                except Exception:
                    pass
                sftp.close()
        out = out.strip()
        if not out:
            raise RuntimeError("collector returned no output; stderr: %s" % err.strip())
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            raise RuntimeError("collector output was not JSON: %s" % out[:400])
        if not data.get("ok", False):
            raise RuntimeError("collector error: %s" % data.get("error", "unknown"))
        return data

    def systemctl(self, action, unit):
        out, err = self.run_sudo("systemctl %s %s" % (action, unit))
        if err.strip() and "incorrect password" in err.lower():
            raise PermissionError("Sudo password incorrect")
        return out, err

    def kill_pid(self, pid, signal="TERM"):
        return self.run_sudo("kill -%s %d" % (signal, int(pid)))

    def journal(self, unit, lines=200):
        out, _ = self.run_sudo("journalctl -u %s -n %d --no-pager" % (unit, lines))
        return out

    def run_command(self, cmd, timeout=60):
        """Run an arbitrary operator-approved command and return combined output.

        Used by the agent chat: a `sudo `-prefixed command goes through the
        stdin sudo channel, anything else through a login shell. stderr is
        folded in so the model sees failures."""
        cmd = cmd.strip()
        if cmd.startswith("sudo "):
            out, err = self.run_sudo(cmd[5:], timeout=timeout)
        else:
            out, err = self.run("bash -lc %s" % shlex.quote(cmd), timeout=timeout)
        if err.strip():
            out = (out + ("\n" if out and not out.endswith("\n") else "")
                   + "[stderr] " + err.strip())
        return out

    def close(self):
        try:
            self.client.close()
        except Exception:
            pass


class CollectorThread(QThread):
    """One snapshot collection off the GUI thread."""
    snapshot = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ssh, parent=None):
        super().__init__(parent)
        self._ssh = ssh

    def run(self):
        try:
            self.snapshot.emit(self._ssh.collect_snapshot())
        except Exception as exc:
            self.error.emit(str(exc))


class ContextThread(QThread):
    """Gather one row's inspection context over SSH, off the GUI thread.

    The result seeds the agent chat's opening turn; further inspection is
    driven by the model's own approved commands."""
    ready = pyqtSignal(str, str)    # (context, kind)
    error = pyqtSignal(str)

    def __init__(self, ssh, item, parent=None):
        super().__init__(parent)
        self._ssh = ssh
        self._item = item

    def run(self):
        try:
            if self._item.get("type") == "stray":
                self.ready.emit(gather_stray_context(self._ssh.run_sudo, self._item),
                                "process")
            else:
                self.ready.emit(gather_service_context(self._ssh.run_sudo, self._item),
                                "service")
        except Exception as exc:
            self.error.emit(str(exc))


class ModelsThread(QThread):
    """Discover the models an endpoint serves, off the GUI thread."""
    models = pyqtSignal(str, list)  # (endpoint, ids)
    error = pyqtSignal(str, str)    # (endpoint, message)

    def __init__(self, llm_api, api_key="", parent=None):
        super().__init__(parent)
        self._llm_api = llm_api
        self._api_key = api_key

    def run(self):
        try:
            self.models.emit(self._llm_api,
                             llm_list_models(self._llm_api, api_key=self._api_key))
        except Exception as exc:
            self.error.emit(self._llm_api, str(exc))


# ──────────────────────────────── dialogs ─────────────────────────────────
class ConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Server")
        self.setFixedSize(460, 330)
        layout = QFormLayout()
        self.hostname = QLineEdit("192.168.1.100")
        self.port = QLineEdit("22")
        self.username = QLineEdit("solcatcher")
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_path = QLineEdit("~/.ssh/id_ed25519")
        self.sudo_password = QLineEdit()
        self.sudo_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key = QLineEdit(LLM_API_KEY_DEFAULT)
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Hostname:", self.hostname)
        layout.addRow("SSH Port:", self.port)
        layout.addRow("Username:", self.username)
        layout.addRow("Password (if no key):", self.password)
        layout.addRow("SSH Key Path (optional):", self.key_path)
        layout.addRow("Sudo Password (for control):", self.sudo_password)
        layout.addRow("LLM API Key (Bearer, optional):", self.api_key)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def details(self):
        return {
            "hostname": self.hostname.text().strip(),
            "port": self.port.text().strip() or "22",
            "username": self.username.text().strip(),
            "password": self.password.text() or None,
            "key_path": self.key_path.text().strip() or None,
            "sudo_password": self.sudo_password.text() or None,
        }

    def llm_api_key(self):
        return self.api_key.text().strip() or LLM_API_KEY_DEFAULT


class LogViewerDialog(QDialog):
    def __init__(self, title, logs, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Logs — %s" % title)
        self.setGeometry(200, 200, 900, 640)
        layout = QVBoxLayout()
        text = QTextEdit()
        text.setReadOnly(True)
        text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        text.setText(logs)
        layout.addWidget(text)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        self.setLayout(layout)


# ──────────────────────────────── the tab ─────────────────────────────────
class servicesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ssh = None
        self._collector = None
        self._snapshot = None
        self._ctx_thread = None
        self._models_fetcher = None
        self._chats = []            # keep modeless chat dialogs alive

        layout = QVBoxLayout(self)

        bar = QHBoxLayout()
        self.connect_btn = QPushButton("Connect to Server")
        self.connect_btn.clicked.connect(self.connect_to_server)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self.load_services)
        self.refresh_btn.setEnabled(False)
        self.show_strays = QCheckBox("Show non-systemd strays")
        self.show_strays.setChecked(True)
        self.show_strays.stateChanged.connect(self._rerender)
        bar.addWidget(self.connect_btn)
        bar.addWidget(self.refresh_btn)
        bar.addWidget(self.show_strays)
        bar.addSpacing(16)
        bar.addWidget(QLabel("LLM:"))
        self.llm_api_combo = QComboBox()
        self.llm_api_combo.setEditable(True)
        for choice in dict.fromkeys(LLM_API_CHOICES):   # dedup, keep order
            self.llm_api_combo.addItem(choice)
        self.llm_api_combo.setMinimumWidth(220)
        self.llm_api_combo.activated.connect(lambda _: self.discover_models())
        bar.addWidget(self.llm_api_combo)
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)              # type a name if discovery fails
        self.model_combo.setMinimumWidth(200)
        self.model_combo.lineEdit().setPlaceholderText("model (auto-discovered)")
        if LLM_MODEL_DEFAULT:                            # pinned per-install default
            self.model_combo.setEditText(LLM_MODEL_DEFAULT)
        bar.addWidget(self.model_combo)
        # Live API-key field: optional, editable any time (not just at connect)
        # so a key can be supplied on the fly if the endpoint needs one.
        self.key_edit = QLineEdit(LLM_API_KEY_DEFAULT)
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("API key (optional)")
        self.key_edit.setMaximumWidth(150)
        self.key_edit.setToolTip("Bearer key for the LLM endpoint; leave blank if open. "
                                 "Re-query models after changing it.")
        self.key_edit.editingFinished.connect(self.discover_models)
        bar.addWidget(self.key_edit)
        self.models_btn = QPushButton("⟳ Models")
        self.models_btn.setToolTip("Query /v1/models on the selected endpoint")
        self.models_btn.clicked.connect(self.discover_models)
        bar.addWidget(self.models_btn)
        self.deep_check = QCheckBox("Deep")
        self.deep_check.setChecked(True)
        self.deep_check.setToolTip("Deep reasoning (thorough, a few seconds slower). "
                                   "Uncheck for a fast /no_think answer.")
        bar.addWidget(self.deep_check)
        self.chat_btn = QPushButton("AI Chat")
        self.chat_btn.setToolTip("Open a free-form agent chat that can inspect the host")
        self.chat_btn.clicked.connect(self.open_chat)
        self.chat_btn.setEnabled(False)
        bar.addWidget(self.chat_btn)
        bar.addStretch(1)
        self.summary = QLabel("Not connected.")
        bar.addWidget(self.summary)
        layout.addLayout(bar)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)  # drag edges to resize
        header.setStretchLastSection(True)
        header.setSectionsMovable(True)                                  # drag headers to reorder
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(True)
        self.table.setSortingEnabled(True)                               # click a header to sort
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        for col, width in enumerate(COLUMN_WIDTHS):
            self.table.setColumnWidth(col, width)
        layout.addWidget(self.table)

    # -- connection / collection --
    def connect_to_server(self):
        dialog = ConnectionDialog(self)
        if not dialog.exec():
            return
        # Seed the live toolbar key field from the dialog (it can be changed
        # afterwards without reconnecting).
        self.key_edit.setText(dialog.llm_api_key())
        try:
            self.ssh = SSHClient(**dialog.details())
        except ImportError:
            QMessageBox.critical(self, "Missing dependency",
                                 "paramiko is not installed (pip install paramiko).")
            return
        except Exception as exc:
            QMessageBox.critical(self, "Connection Error", str(exc))
            return
        self.refresh_btn.setEnabled(True)
        self.chat_btn.setEnabled(True)
        self.discover_models()
        self.load_services()

    # -- LLM endpoint / model selection --
    def _llm_selection(self):
        """Current (endpoint, model, key) tuple for the agent chat."""
        return self.current_llm_api(), self.current_model(), self.current_key()

    def current_llm_api(self):
        return self.llm_api_combo.currentText().strip() or LLM_API_DEFAULT

    def current_model(self):
        return self.model_combo.currentText().strip()

    def current_key(self):
        """Live Bearer key from the toolbar (empty = send no auth header)."""
        return self.key_edit.text().strip()

    def current_deep(self):
        """Whether 'Deep' reasoning is on (else /no_think is appended)."""
        return self.deep_check.isChecked()

    def discover_models(self):
        if self._models_fetcher and self._models_fetcher.isRunning():
            return
        endpoint = self.current_llm_api()
        # Re-probe /endpoints for this base (a manual refresh drops the cache).
        _ROUTE_CACHE.pop(endpoint.rstrip("/"), None)
        self._models_fetcher = ModelsThread(endpoint, api_key=self.current_key(),
                                            parent=self)
        self._models_fetcher.models.connect(self._on_models)
        self._models_fetcher.error.connect(self._on_models_error)
        self._models_fetcher.start()

    def _on_models(self, endpoint, ids):
        if endpoint != self.current_llm_api():
            return  # user switched endpoints while we were fetching
        typed = self.current_model()
        self.model_combo.clear()
        self.model_combo.addItems(ids)
        # Selection priority: hand-typed value > pinned per-install default >
        # the first entry (already floated to the top by llm_list_models).
        if typed and typed in ids:
            self.model_combo.setCurrentText(typed)
        elif typed and typed not in ids:
            self.model_combo.setEditText(typed)   # keep a hand-typed override
        elif LLM_MODEL_DEFAULT:
            if LLM_MODEL_DEFAULT in ids:
                self.model_combo.setCurrentText(LLM_MODEL_DEFAULT)
            else:
                self.model_combo.setEditText(LLM_MODEL_DEFAULT)

    def _on_models_error(self, endpoint, msg):
        if endpoint != self.current_llm_api():
            return
        # Discovery failing is not fatal — the model box stays editable.
        self.summary.setText("Model discovery failed on %s: %s" % (endpoint, msg))

    def load_services(self):
        if not self.ssh:
            QMessageBox.critical(self, "Error", "Not connected. Connect first.")
            return
        if self._collector and self._collector.isRunning():
            return
        self.summary.setText("Collecting…")
        self.refresh_btn.setEnabled(False)
        self._collector = CollectorThread(self.ssh, self)
        self._collector.snapshot.connect(self._on_snapshot)
        self._collector.error.connect(self._on_collect_error)
        self._collector.start()

    def _on_snapshot(self, snap):
        self._snapshot = snap
        self.refresh_btn.setEnabled(True)
        self._rerender()

    def _on_collect_error(self, msg):
        self.refresh_btn.setEnabled(True)
        self.summary.setText("Collection failed.")
        QMessageBox.critical(self, "Collection Error", msg)

    def _rerender(self):
        snap = self._snapshot
        if not snap:
            return
        rows = list(snap.get("services", []))
        if self.show_strays.isChecked():
            rows += list(snap.get("strays", []))
        # Remember the user's current sort so a refresh doesn't reset it.
        header = self.table.horizontalHeader()
        sort_col = header.sortIndicatorSection()
        sort_order = header.sortIndicatorOrder()
        # Populate with sorting OFF so inserts don't reshuffle rows mid-build
        # (which would desync the per-row colour/widget assignments below).
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for item in rows:
            self._add_row(item)
        self.table.setSortingEnabled(True)
        # Re-apply the chosen sort; before the user has clicked anything the
        # collector's CPU-descending order is preserved.
        if sort_col >= 0:
            self.table.sortItems(sort_col, sort_order)
        self._restore_summary()

    # -- rendering --
    def _add_row(self, item):
        is_stray = item.get("type") == "stray"
        row = self.table.rowCount()
        self.table.insertRow(row)

        state = ("STRAY" if is_stray
                 else item.get("active_state") or ("active" if item.get("active") else "inactive"))
        host_port = ("%s:%s" % (item.get("ip_add"), item.get("port"))
                     if item.get("ip_add") and item.get("port")
                     else (":%s" % item["port"] if item.get("port") else "—"))
        pid = item.get("pid") or 0
        cpu = float(item.get("cpu", 0.0))
        mem = float(item.get("mem", 0.0))
        procs = 1 if is_stray else int(item.get("nprocs", 1))
        uptime = "" if is_stray else item.get("uptime", "N/A")
        # (display_text, numeric_sort_value | None) per column, in order.
        cells = [
            ("stray" if is_stray else "service", None),
            (item.get("name", ""), None),
            (state, None),
            (str(pid) if pid else "", pid),
            ("%.1f" % cpu, cpu),
            ("%.1f" % mem, mem),
            (str(procs), procs),
            (item.get("cgroup", "—") if is_stray else host_port, None),
            (uptime, _uptime_seconds(uptime)),
        ]
        for col, (text, value) in enumerate(cells):
            if col in NUMERIC_COLS:
                cell = NumericTableWidgetItem(text, value)
            else:
                cell = QTableWidgetItem(text)
            cell.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.table.setItem(row, col, cell)

        # Colour cues: strays amber, active green-ish, busy CPU red.
        if is_stray:
            self.table.item(row, 0).setBackground(QColor(255, 214, 153))
        elif item.get("active"):
            self.table.item(row, 2).setForeground(QColor(0, 140, 0))
        if item.get("cpu", 0) >= 80:
            self.table.item(row, 4).setForeground(QColor(200, 0, 0))

        self.table.setCellWidget(row, 9, self._actions_widget(item, is_stray))
        logs_btn = QPushButton("Logs")
        if is_stray:
            logs_btn.setEnabled(False)
        else:
            logs_btn.clicked.connect(lambda _, n=item["name"]: self.show_logs(n))
        self.table.setCellWidget(row, 10, logs_btn)
        ai_btn = QPushButton("Analyze")
        ai_btn.clicked.connect(lambda _, it=item: self._analyze(it))
        self.table.setCellWidget(row, 11, ai_btn)

    def _actions_widget(self, item, is_stray):
        widget = QWidget()
        lay = QHBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)
        if is_stray:
            pid = item.get("pid")
            term = QPushButton("Kill")
            term.clicked.connect(lambda _, p=pid, n=item.get("name"): self._kill(p, n))
            lay.addWidget(term)
            return widget
        name = item["name"]
        for label, action in [("Start", "start"), ("Restart", "restart"),
                              ("Stop", "stop"), ("Reload", "reload")]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, a=action, n=name: self._control(a, n))
            lay.addWidget(btn)
        toggle = "disable" if item.get("enabled") else "enable"
        en = QPushButton("Disable" if item.get("enabled") else "Enable")
        en.clicked.connect(lambda _, a=toggle, n=name: self._control(a, n))
        lay.addWidget(en)
        return widget

    # -- actions --
    def _control(self, action, unit):
        try:
            _, err = self.ssh.systemctl(action, unit)
            if err.strip() and "warning" not in err.lower():
                raise RuntimeError(err.strip())
            QMessageBox.information(self, "OK", "%s %s: done." % (action, unit))
        except Exception as exc:
            QMessageBox.critical(self, "Error", "%s %s failed: %s" % (action, unit, exc))
        self.load_services()

    def _kill(self, pid, name):
        if not pid:
            return
        confirm = QMessageBox.question(
            self, "Kill stray process",
            "Send SIGTERM to PID %s (%s)?\nThis is a non-systemd process." % (pid, name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self.ssh.kill_pid(pid, "TERM")
            QMessageBox.information(self, "OK", "SIGTERM sent to %s." % pid)
        except Exception as exc:
            QMessageBox.critical(self, "Error", "kill %s failed: %s" % (pid, exc))
        self.load_services()

    def show_logs(self, unit):
        try:
            logs = self.ssh.journal(unit)
            LogViewerDialog(unit, logs, self).exec()
        except Exception as exc:
            QMessageBox.critical(self, "Error", "Logs for %s failed: %s" % (unit, exc))

    # -- LLM analysis / agent chat --
    def _analyze(self, item):
        """Gather the row's context, then open an agent chat seeded with it."""
        if not self.ssh:
            QMessageBox.critical(self, "Error", "Not connected. Connect first.")
            return
        if self._ctx_thread and self._ctx_thread.isRunning():
            return
        self.summary.setText("Gathering context for %s …" % item.get("name"))
        self._ctx_thread = ContextThread(self.ssh, item, parent=self)
        self._ctx_thread.ready.connect(
            lambda ctx, kind, it=item: self._open_analysis_chat(it, ctx, kind))
        self._ctx_thread.error.connect(self._on_context_error)
        self._ctx_thread.start()

    def _open_analysis_chat(self, item, context, kind):
        self._restore_summary()
        seed = [
            {"role": "system", "content": AGENT_SYSTEM},
            {"role": "user",
             "content": ANALYZE_PROMPT.format(context=context, kind=kind)
             + think_suffix(self.current_deep())},
        ]
        self._spawn_chat(str(item.get("name", "?")), seed, autostart=True)

    def open_chat(self):
        """Free-form agent chat with no seeded row — inspect the host at will."""
        if not self.ssh:
            QMessageBox.critical(self, "Error", "Not connected. Connect first.")
            return
        seed = [{"role": "system", "content": AGENT_SYSTEM}]
        self._spawn_chat(self.current_llm_api(), seed, autostart=False)

    def _spawn_chat(self, title, seed, autostart):
        from .agent import AgentChatDialog   # lazy: avoids import cycle
        dlg = AgentChatDialog(title, self.ssh, self._llm_selection, seed,
                              autostart=autostart, deep_provider=self.current_deep,
                              parent=self)
        dlg.finished.connect(lambda _=0, d=dlg: self._chats.remove(d)
                             if d in self._chats else None)
        self._chats.append(dlg)
        dlg.show()

    def _on_context_error(self, msg):
        self._restore_summary()
        QMessageBox.critical(self, "Context Error",
                             "Could not gather context: %s" % msg)

    def _restore_summary(self):
        snap = self._snapshot
        if snap:
            t = snap.get("totals", {})
            self.summary.setText(
                "%d services · %d strays · %.0f MB service RAM · %d cores"
                % (t.get("n_services", 0), t.get("n_strays", 0),
                   t.get("service_mem_mb", 0), snap.get("ncpu", 0)))
        else:
            self.summary.setText("")
