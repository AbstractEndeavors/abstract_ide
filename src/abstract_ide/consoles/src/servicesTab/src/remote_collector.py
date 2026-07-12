#!/usr/bin/env python3
"""
remote_collector.py — one-shot host snapshot for the service viewer.

Emits a single JSON document on stdout describing every systemd *.service
(active or enabled) plus every notable non-systemd process ("stray"), with
LIVE per-unit CPU% and memory aggregated across all of a unit's processes.

Design goals (these are the fixes over the old per-service SSH storm):
  * ONE process, ONE snapshot — meant to be shipped over a single SSH exec
    (``ssh host python3 - < remote_collector.py``) or run locally.
  * READ-ONLY and NO sudo: everything here comes from /proc and
    ``systemctl show`` (both readable by a normal user). Only the *control*
    actions (start/stop/…) in the GUI need privilege — collection never does.
  * Correct CPU: sampled from /proc jiffies over a short interval (top-style,
    100% == one full core), summed over each unit's cgroup, not a lifetime
    average of just the MainPID.
  * Sees non-systemd processes, so a bare ``nohup ./miner`` shows up as a
    flagged stray instead of being invisible.

Stdlib only; works on Python 3.6+.
"""
import json
import os
import subprocess
import sys
import time

CLK_TCK = os.sysconf("SC_CLK_TCK")
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")
NCPU = os.cpu_count() or 1

# Unit properties fetched in a single batched `systemctl show` call.
UNIT_PROPS = [
    "Id", "MainPID", "ActiveState", "SubState", "UnitFileState",
    "ExecStart", "WorkingDirectory", "ActiveEnterTimestamp", "ControlGroup",
]


def _read(path):
    try:
        with open(path, "r", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def _run(cmd):
    try:
        return subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=15, text=True,
        ).stdout
    except (subprocess.SubprocessError, OSError):
        return ""


# ─────────────────────────── /proc sampling ───────────────────────────────
def _proc_table():
    """pid -> {jiffies, ppid, comm} for every live process."""
    table = {}
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        raw = _read("/proc/%s/stat" % entry)
        if not raw:
            continue
        try:
            # comm (field 2) is parenthesised and may contain spaces/parens.
            rparen = raw.rindex(")")
            comm = raw[raw.index("(") + 1:rparen]
            rest = raw[rparen + 2:].split()
            # rest[0]=state, rest[1]=ppid, rest[11]=utime, rest[12]=stime
            table[int(entry)] = {
                "jiffies": int(rest[11]) + int(rest[12]),
                "ppid": int(rest[1]),
                "comm": comm,
            }
        except (ValueError, IndexError):
            continue
    return table


def _total_jiffies():
    line = _read("/proc/stat").split("\n", 1)[0]
    return sum(int(x) for x in line.split()[1:]) or 1


def _cpu_percent(interval=0.3):
    """pid -> live CPU% (top-style: one saturated core == 100)."""
    first, c1 = _proc_table(), _total_jiffies()
    time.sleep(interval)
    second, c2 = _proc_table(), _total_jiffies()
    span = (c2 - c1) or 1
    pct = {}
    for pid, cur in second.items():
        prev = first.get(pid)
        if prev is None:
            continue
        delta = cur["jiffies"] - prev["jiffies"]
        pct[pid] = (delta / span) * NCPU * 100.0
    return pct, second


def _rss_mb(pid):
    field = _read("/proc/%d/statm" % pid).split()
    if len(field) < 2:
        return 0.0
    return int(field[1]) * PAGE_SIZE / (1024.0 * 1024.0)


def _cgroup_unit(pid):
    """The systemd unit a pid belongs to, parsed from /proc/pid/cgroup.

    Returns the *.service / *.scope / *.slice leaf, or "" if unknown.
    """
    for line in _read("/proc/%d/cgroup" % pid).splitlines():
        # cgroup v2: "0::/system.slice/foo.service"
        # cgroup v1: "N:controller:/system.slice/foo.service"
        path = line.rsplit(":", 1)[-1]
        for part in reversed(path.split("/")):
            if part.endswith((".service", ".scope", ".slice")):
                return part
    return ""


def _cmdline(pid):
    raw = _read("/proc/%d/cmdline" % pid)
    return raw.replace("\x00", " ").strip()


# ─────────────────────────── systemd units ────────────────────────────────
def _unit_names():
    """Active-or-enabled service units, enumerated precisely.

    We ask systemd for the two state-filtered sets directly rather than
    dumping every installed unit file: the full list is mostly aliases and
    system noise, and — critically — passing hundreds of names to a single
    ``systemctl show`` makes it silently return only a fraction of them.
    """
    names = set()
    # Currently-active services (includes system + app units actually running).
    for line in _run(["systemctl", "list-units", "--type=service",
                      "--state=active", "--no-legend", "--no-pager"]).splitlines():
        tok = line.replace("●", " ").split()
        if tok and tok[0].endswith(".service"):
            names.add(tok[0])
    # Enabled-on-boot services (covers enabled-but-inactive units).
    for line in _run(["systemctl", "list-unit-files", "--type=service",
                      "--state=enabled", "--no-legend", "--no-pager"]).splitlines():
        tok = line.split()
        if tok and tok[0].endswith(".service"):
            names.add(tok[0])
    return sorted(names)


def _show_units(names, chunk=50):
    """Batched `systemctl show` -> {unit_id: {prop: value}}.

    Chunked because ``systemctl show`` truncates its output when handed too
    many unit arguments at once; 50 per call is safe and still turns ~130
    units into ~3 calls instead of one-per-unit.
    """
    units = {}
    for start in range(0, len(names), chunk):
        batch = names[start:start + chunk]
        if not batch:
            continue
        out = _run(["systemctl", "show", "--no-pager",
                    "--property=" + ",".join(UNIT_PROPS)] + batch)
        cur = {}
        for line in out.split("\n"):
            if not line.strip():
                if cur.get("Id"):
                    units[cur["Id"]] = cur
                cur = {}
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                cur[key] = val
        if cur.get("Id"):
            units[cur["Id"]] = cur
    return units


def _parse_exec(exec_start):
    """Pull gunicorn/ip/port/workers hints out of an ExecStart string."""
    info = {"gunicorn": False, "ip_add": None, "port": None, "workers": 1}
    if not exec_start:
        return info
    # systemctl renders ExecStart as { path ; argv[]=... ; ... }; grab argv.
    text = exec_start
    if "argv[]=" in text:
        text = text.split("argv[]=", 1)[1].split(";", 1)[0]
    parts = text.split()
    for i, part in enumerate(parts):
        if part.endswith("gunicorn"):
            info["gunicorn"] = True
        elif part.startswith("--bind") and i + 1 < len(parts) and ":" in parts[i + 1]:
            ip, _, port = parts[i + 1].rpartition(":")
            info["ip_add"], info["port"] = ip, port
        elif part == "-p" and i + 1 < len(parts) and parts[i + 1].isdigit():
            info["port"] = parts[i + 1]
        elif part.startswith("--workers") and i + 1 < len(parts):
            try:
                info["workers"] = int(parts[i + 1])
            except ValueError:
                pass
    return info


# ─────────────────────────────── snapshot ─────────────────────────────────
def collect(interval=0.3, stray_cpu=5.0, stray_mem_mb=150.0):
    cpu, table = _cpu_percent(interval)

    # Group every live pid by its systemd unit (via cgroup) once.
    unit_pids, pid_meta = {}, {}
    for pid in table:
        unit = _cgroup_unit(pid)
        meta = {
            "pid": pid,
            "cpu": round(cpu.get(pid, 0.0), 1),
            "mem": round(_rss_mb(pid), 1),
            "comm": table[pid]["comm"],
            "unit": unit,
        }
        pid_meta[pid] = meta
        unit_pids.setdefault(unit, []).append(pid)

    names = _unit_names()
    shown = _show_units(names)

    services = []
    accounted = set()
    for unit_id in names:
        props = shown.get(unit_id, {})
        active = props.get("ActiveState") == "active"
        enabled = props.get("UnitFileState") == "enabled"
        if not (active or enabled):
            continue  # match the original: only active-or-enabled in the view
        pids = unit_pids.get(unit_id, [])
        accounted.update(pids)
        exec_info = _parse_exec(props.get("ExecStart", ""))
        try:
            main_pid = int(props.get("MainPID", "0"))
        except ValueError:
            main_pid = 0
        services.append({
            "name": unit_id,
            "active": active,
            "active_state": props.get("ActiveState", ""),
            "sub_state": props.get("SubState", ""),
            "enabled": enabled,
            "pid": main_pid or None,
            "cpu": round(sum(pid_meta[p]["cpu"] for p in pids), 1),
            "mem": round(sum(pid_meta[p]["mem"] for p in pids), 1),
            "nprocs": len(pids),
            "workers": exec_info["workers"],
            "ip_add": exec_info["ip_add"],
            "port": exec_info["port"],
            "directory": props.get("WorkingDirectory") or None,
            "exec_start": props.get("ExecStart") or None,
            "uptime": _format_uptime(props.get("ActiveEnterTimestamp", "")),
            "type": "service",
        })

    # Strays: notable processes not owned by any *.service cgroup.
    strays = []
    for pid, meta in pid_meta.items():
        if pid in accounted:
            continue
        if meta["unit"].endswith(".service"):
            continue
        if meta["cpu"] < stray_cpu and meta["mem"] < stray_mem_mb:
            continue
        strays.append({
            "name": meta["comm"],
            "pid": pid,
            "cpu": meta["cpu"],
            "mem": meta["mem"],
            "cgroup": meta["unit"] or "-",
            "cmdline": _cmdline(pid)[:240],
            "type": "stray",
        })
    strays.sort(key=lambda s: (s["cpu"], s["mem"]), reverse=True)

    services.sort(key=lambda s: (s["cpu"], s["mem"]), reverse=True)
    return {
        "ok": True,
        "ncpu": NCPU,
        "services": services,
        "strays": strays,
        "totals": {
            "service_mem_mb": round(sum(s["mem"] for s in services), 1),
            "service_cpu": round(sum(s["cpu"] for s in services), 1),
            "n_services": len(services),
            "n_strays": len(strays),
        },
    }


def _format_uptime(ts):
    if not ts:
        return "N/A"
    try:
        from datetime import datetime
        start = datetime.strptime(ts, "%a %Y-%m-%d %H:%M:%S %Z")
        secs = int((datetime.now(start.tzinfo) - start).total_seconds())
        h, rem = divmod(max(secs, 0), 3600)
        m, s = divmod(rem, 60)
        return "%dh %dm %ds" % (h, m, s)
    except (ValueError, TypeError):
        return "N/A"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    interval = 0.3
    if argv:
        try:
            interval = float(argv[0])
        except ValueError:
            pass
    try:
        snap = collect(interval=interval)
    except Exception as exc:  # never crash the transport; report structured error
        snap = {"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}
    json.dump(snap, sys.stdout)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
