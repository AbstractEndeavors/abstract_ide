from ..imports import *
from PyQt6.QtWidgets import QFileDialog, QMessageBox
from PyQt6.QtCore import Qt
import re
from collections import defaultdict
# ───────────────── helpers to read tree state ─────────────────

def _iter_tree_rows(self):
    """Yield (path, apply_checked, overwrite_checked, item) for each row."""
    for i in range(self.files_list.topLevelItemCount()):
        it = self.files_list.topLevelItem(i)
        path = it.data(0, Qt.ItemDataRole.UserRole) or it.text(0)
        apply_checked    = (it.checkState(1) == Qt.CheckState.Checked)
        overwrite_checked= (it.checkState(2) == Qt.CheckState.Checked)
        yield path, apply_checked, overwrite_checked, it

def _gather_checked(self):
    """Return list of dicts for rows the user wants to apply to."""
    targets = []
    for path, apply_ck, over_ck, _ in _iter_tree_rows(self):
        if apply_ck and path:
            targets.append({"path": path, "overwrite": over_ck})
    return targets

# ───────────── logging to log pane (if present) ─────────────
def get_files(self) -> list[str]:
    params = make_params(self)
    dirs, files = get_files_and_dirs(**params)
    return files
def append_log(self, text: str):
    if not hasattr(self, "log") or self.log is None:
        return
    c = self.log.textCursor()
    c.movePosition(c.MoveOperation.End)
    self.log.setTextCursor(c)
    self.log.insertPlainText(text)
    self.log.ensureCursorVisible()

# ───────────── small helpers for tests / diagnostics ────────

def get_all_files(self) -> list[str]:
    try:
        files = get_files(self)
    except Exception as e:
        QMessageBox.critical(self, "Error", str(e))
        set_status(self, f"Error: {e}", "error")
        return []
    if hasattr(self, "output"):
        self.output.insertPlainText(f"files = {files}\n")
    return files

def get_hunks(self, diff_text: str) -> list[Hunk]:
    hunks = parse_unified_diff(diff_text)
    if not hunks:
        QMessageBox.warning(self, "Warning", "No valid hunks found in diff.")
        set_status(self, "No valid hunks found.", "warn")
        return []
    if hasattr(self, "output"):
        self.output.insertPlainText(f"hunks = {hunks}\n")
    return hunks

def get_all_subs(self, hunks: list[Hunk]) -> list[str]:
    flat: list[str] = []
    for h in hunks:
        flat.extend(h.subs)
    if hasattr(self, "output"):
        self.output.insertPlainText(f"subs(flat) = {flat}\n")
    return flat

def find_matches_for_hunks(files: list[str], hunks: list[Hunk]) -> tuple[list[str], list[dict]]:
    all_files: set[str] = set()
    all_found: list[dict] = []
    for h in hunks:
        if not h.subs:
            continue
        nu_files, found_paths = getPaths(files, h.subs)
        all_files.update(nu_files)
        for fp in found_paths:
            fp["hunk"] = h
        all_found.extend(found_paths)
    return sorted(all_files), all_found

def get_test_diff(self) -> str:
    diff_text = """\
-def browse_dir(self):
-    d = QFileDialog.getExistingDirectory(self, "Choose directory", self.dir_in.text() or os.getcwd())
-    if d:
-        self.dir_in.setText(d)
+def browse_dir(self):
+    d = QFileDialog.getExistingDirectory(self, "Choose directory", self.dir_in.text() or os.getcwd())
+    if d:
+        self.dir_in.setText(d)
"""
    diff_text = diff_text.strip("\n")
    if hasattr(self, "output"):
        self.output.insertPlainText(f"diff_text = {diff_text}\n")
    return diff_text

def get_nufiles(self, files: list[str], subs: list[str] | str):
    nu_files, found_paths = getPaths(files, subs)
    if hasattr(self, "output"):
        self.output.insertPlainText(f"nu_files = {nu_files}\n")
        self.output.insertPlainText(f"found_paths = {found_paths}\n")
    return nu_files, found_paths

def output_test(self, *_):
    files = get_all_files(self)
    diff_text = get_test_diff(self)
    hunks = get_hunks(self, diff_text)
    subs = get_all_subs(self, hunks)
    get_nufiles(self, files, subs)

# ───────────────────── Core preview/apply ───────────────────

def _ask_user_to_pick_file(self, files: List[str], title: str = "Pick a file to preview") -> str | None:
    if not files:
        return None
    if len(files) == 1:
        return files[0]
    dlg = QFileDialog(self, title, os.path.dirname(files[0]) if files else os.getcwd())
    dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
    dlg.setNameFilter("All files (*)")
    if dlg.exec():
        sel = dlg.selectedFiles()
        return sel[0] if sel else None
    return None

def _preview_for_path(self, target_file: str):
    """Preview ONLY for the provided path (no re-populate / no re-match)."""
    diff = self.diff_text.toPlainText().strip()
    if not diff or not target_file or not os.path.exists(target_file):
        return
    try:
        with open(target_file, "r", encoding="utf-8") as f:
            original_lines = f.read().splitlines()
        patched = apply_custom_diff(original_lines, diff.splitlines())
        self.preview.setPlainText(patched)
        set_status(self, f"Preview generated for: {target_file}", "ok")
        append_log(self, f"Preview generated for {target_file}\n")
    except ValueError as e:
        QMessageBox.critical(self, "Error", str(e))
        set_status(self, f"Error: {e}", "error")
        append_log(self, f"Error in preview: {e}\n")
    except Exception as e:
        QMessageBox.critical(self, "Unexpected Error", f"An unexpected error occurred: {e}")
        set_status(self, f"Unexpected Error: {e}", "error")
        append_log(self, f"Unexpected error in preview: {e}\n")

def preview_patch(self):
    diff = self.diff_text.toPlainText().strip()
    if not diff:
        QMessageBox.critical(self, "Error", "No diff provided.")
        set_status(self, "Error: No diff provided.", "error")
        return

    try:
        files = get_files(self)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to gather files: {e}")
        set_status(self, f"Error: {e}", "error")
        return

    if not files:
        QMessageBox.warning(self, "No Files", "No files match the current filters.")
        set_status(self, "No files match filters.", "warn")
        return

    hunks = parse_unified_diff(diff)
    if not hunks:
        QMessageBox.warning(self, "Warning", "No valid hunks found in diff.")
        set_status(self, "No valid hunks found.", "warn")
        return

    matched_files, found_paths = find_matches_for_hunks(files, hunks)

    # Fill the tree. We prefer a flat list of file paths here.
    self._fill_files_tree(matched_files, default_apply=True, default_overwrite=True)

    # Choose preview target:
    path = self._pick_preview_target(files, hunks)
    if not path:
        # fallback to first match if present
        if matched_files:
            path = matched_files[0]
        elif found_paths:
            path = found_paths[0]["file_path"]

    if not path:
        set_status(self, "No matches found in any file.", "warn")
        return

    _preview_for_path(self, path)

def _selected_tree_row_flags(self):
    """
    Returns (path, apply_checked, overwrite_checked) for the current tree row,
    or (None, False, False) if nothing selected.
    """
    it = self.files_list.currentItem()
    if not it:
        return None, False, False
    path = it.data(0, Qt.ItemDataRole.UserRole) or it.text(0)
    apply_checked = (it.checkState(1) == Qt.CheckState.Checked)
    overwrite_checked = (it.checkState(2) == Qt.CheckState.Checked)
    return path, apply_checked, overwrite_checked

def _first_overwrite_checked(self):
    """
    Returns first path in the tree with Overwrite checked, else None.
    """
    for i in range(self.files_list.topLevelItemCount()):
        it = self.files_list.topLevelItem(i)
        if it.checkState(2) == Qt.CheckState.Checked:
            return it.data(0, Qt.ItemDataRole.UserRole) or it.text(0)
    return None
def save_patch(self):
    patched = self.preview.toPlainText()
    if not patched:
        QMessageBox.warning(self, "Warning", "No preview to save. Generate a preview first.")
        set_status(self, "No preview to save.", "warn")
        return

    # 1) Prefer the currently-selected tree row (if any)
    target = None
    selected_path, _, sel_overwrite = _selected_tree_row_flags(self)
    if selected_path and os.path.exists(selected_path):
        if sel_overwrite:
            # Overwrite directly, no prompt
            target = selected_path
            try:
                with open(target, "w", encoding="utf-8") as f:
                    f.write(patched if patched.endswith("\n") else patched + "\n")
                QMessageBox.information(self, "Success", f"Saved: {target}")
                set_status(self, f"Saved: {target}", "ok")
                append_log(self, f"Saved patched file: {target}\n")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
                set_status(self, f"Error saving file: {e}", "error")
                append_log(self, f"Error saving file: {e}\n")
            return
        else:
            # Ask to overwrite the selected file
            reply = QMessageBox.question(
                self, "Confirm Save",
                f"Overwrite this file?\n\n{selected_path}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                target = selected_path
                try:
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(patched if patched.endswith("\n") else patched + "\n")
                    QMessageBox.information(self, "Success", f"Saved: {target}")
                    set_status(self, f"Saved: {target}", "ok")
                    append_log(self, f"Saved patched file: {target}\n")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
                    set_status(self, f"Error saving file: {e}", "error")
                    append_log(self, f"Error saving file: {e}\n")
                return
            # If user said No, fall through to chooser

    # 2) If nothing selected, but some row(s) have Overwrite checked, take the first
    ow_first = _first_overwrite_checked(self)
    if ow_first and os.path.exists(ow_first):
        try:
            with open(ow_first, "w", encoding="utf-8") as f:
                f.write(patched if patched.endswith("\n") else patched + "\n")
            QMessageBox.information(self, "Success", f"Saved: {ow_first}")
            set_status(self, f"Saved: {ow_first}", "ok")
            append_log(self, f"Saved patched file: {ow_first}\n")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
            set_status(self, f"Error saving file: {e}", "error")
            append_log(self, f"Error saving file: {e}\n")
        return

    # 3) Fallback: ask user via file dialog (your existing behavior)
    dlg = QFileDialog(self, "Choose target file to overwrite")
    dlg.setFileMode(QFileDialog.FileMode.ExistingFile)
    dlg.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dlg.setNameFilter("All files (*)")
    if not dlg.exec():
        set_status(self, "Save cancelled.", "warn")
        return
    target = dlg.selectedFiles()[0] if dlg.selectedFiles() else None
    if not target:
        set_status(self, "No file chosen.", "error")
        return

    try:
        reply = QMessageBox.question(
            self, "Confirm Save",
            f"Overwrite this file?\n\n{target}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            set_status(self, "Save cancelled.", "warn")
            return

        with open(target, "w", encoding="utf-8") as f:
            f.write(patched if patched.endswith("\n") else patched + "\n")

        QMessageBox.information(self, "Success", f"Saved: {target}")
        set_status(self, f"Saved: {target}", "ok")
        append_log(self, f"Saved patched file: {target}\n")
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to save file: {e}")
        set_status(self, f"Error saving file: {e}", "error")
        append_log(self, f"Error saving file: {e}\n")


def apply_custom_diff(original_lines: List[str], diff_lines: List[str]) -> str:
    """
    Apply simplified unified diff: replace each exact multi-line 'subs' block with 'adds'.
    """
    if diff_lines and "/" in diff_lines[0]:
        diff_lines = diff_lines[1:]
    hunks = parse_unified_diff("\n".join(diff_lines))
    replacements = []
    og_content = "\n".join(original_lines)

    for h in hunks:
        if not h.subs:
            continue
        tot_subs = "\n".join(h.subs)
        for m in re.finditer(re.escape(tot_subs), og_content):
            start_byte = m.start()
            start_line = og_content[:start_byte].count("\n")
            if original_lines[start_line:start_line + len(h.subs)] == h.subs:
                replacements.append({"start": start_line, "end": start_line + len(h.subs), "adds": h.adds[:]})

    replacements.sort(key=lambda r: r["start"])
    for i in range(1, len(replacements)):
        if replacements[i-1]["end"] > replacements[i]["start"]:
            raise ValueError("Overlapping hunks detected.")

    out = original_lines[:]
    for r in reversed(replacements):
        out = out[:r["start"]] + r["adds"] + out[r["end"]:]
    return "\n".join(out)
def save_all_checked(self, make_backup: bool = True, backup_ext: str = ".bak"):
    """
    Save the current diff preview into ALL rows where:
      - Apply is checked, and
      - Overwrite determines whether we replace the file or write *.new
    """
    diff_text = self.diff_text.toPlainText().strip()
    if not diff_text:
        QMessageBox.warning(self, "Warning", "No diff provided.")
        set_status(self, "No diff provided.", "warn")
        return

    try:
        targets = _gather_checked(self)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to read selection: {e}")
        set_status(self, f"Error: {e}", "error")
        return

    if not targets:
        QMessageBox.information(self, "Nothing to do", "No rows are checked for Apply.")
        set_status(self, "No rows checked.", "warn")
        return

    # Pre-parse once for speed
    diff_lines = diff_text.splitlines()

    changed, skipped, failed = 0, 0, 0
    for t in targets:
        path = t["path"]
        ow   = t["overwrite"]

        if not os.path.isfile(path):
            append_log(self, f"Skip (not a file): {path}\n")
            skipped += 1
            continue

        try:
            with open(path, "r", encoding="utf-8") as f:
                original = f.read().splitlines()

            # Recompute patch for THIS file (not using the preview text area)
            patched_text = apply_custom_diff(original, diff_lines)

            # If nothing changed, count as skipped to avoid churn
            original_text = "\n".join(original)
            if patched_text == original_text or patched_text + "\n" == original_text:
                append_log(self, f"No changes needed: {path}\n")
                skipped += 1
                continue

            out_path = path if ow else f"{path}.new"

            # Optional safety backup
            if make_backup and ow and os.path.exists(path):
                try:
                    shutil.copy2(path, path + backup_ext)
                    append_log(self, f"Backup written: {path + backup_ext}\n")
                except Exception as e:
                    append_log(self, f"Backup failed ({path}): {e}\n")

            with open(out_path, "w", encoding="utf-8") as f:
                f.write(patched_text if patched_text.endswith("\n") else patched_text + "\n")

            append_log(self, f"Saved: {out_path}\n")
            changed += 1

        except ValueError as e:
            # apply_custom_diff may raise on overlapping hunks, etc.
            append_log(self, f"Patch error for {path}: {e}\n")
            failed += 1
        except Exception as e:
            append_log(self, f"Unexpected error for {path}: {e}\n")
            failed += 1

    # User feedback
    msg = f"Saved: {changed}, Skipped: {skipped}, Failed: {failed}"
    set_status(self, msg, "ok" if changed and not failed else ("warn" if changed else "error"))
    QMessageBox.information(self, "Apply finished", msg)

def apply_diff_to_directory(self, diff_text: str) -> ApplyReport:
    report = ApplyReport()
    try:
        files = get_files(self)
    except Exception as e:
        QMessageBox.critical(self, "Error", str(e))
        set_status(self, f"Error: {e}", "error")
        return report

    if not diff_text or not diff_text.strip():
        QMessageBox.critical(self, "Error", "No diff provided.")
        set_status(self, "Error: No diff provided.", "error")
        return report

    hunks = parse_unified_diff(diff_text)
    if not hunks:
        QMessageBox.warning(self, "Warning", "No valid hunks found in diff.")
        set_status(self, "No valid hunks found.", "warn")
        return report

    file_to_replacements: dict[str, list] = defaultdict(list)

    for h in hunks:
        if not h.subs:
            report.hunks_skipped += 1
            append_log(self, "Skipping hunk with empty subs\n")
            continue

        nu_files, found_paths = getPaths(files, h.subs)
        h.content = found_paths
        any_applied = False

        for fp in found_paths:
            if not fp.get("lines"):
                continue
            start_line = fp["lines"][0]["line"]
            file_path = fp["file_path"]
            file_to_replacements[file_path].append({
                "start": start_line,
                "end": start_line + len(h.subs),
                "adds": h.adds.copy(),
                "subs": h.subs.copy()
            })
            any_applied = True

        if any_applied:
            report.hunks_applied += 1
            append_log(self, f"Applied hunk to {len(nu_files)} file(s)\n")
        else:
            report.hunks_skipped += 1
            append_log(self, "No matches found for hunk\n")

    for file_path, repls in file_to_replacements.items():
        repls_sorted = sorted(repls, key=lambda r: r["start"])
        overlaps = any(repls_sorted[i-1]["end"] > repls_sorted[i]["start"] for i in range(1, len(repls_sorted)))
        if overlaps:
            append_log(self, f"Error: Overlapping hunks in {file_path}. Skipped.\n")
            report.extend_skipped(file_path)
            continue

        try:
            og = read_any_file(file_path)
            lines = og.split("\n")
            for r in reversed(repls_sorted):
                if r["start"] >= len(lines) or r["end"] > len(lines):
                    append_log(self, f"Warning: Invalid line range in {file_path}, skipping hunk\n")
                    continue
                if lines[r["start"]:r["end"]] != r["subs"]:
                    append_log(self, f"Warning: Mismatch in {file_path}, skipping hunk\n")
                    continue
                lines = lines[:r["start"]] + r["adds"] + lines[r["end"]:]
            new_content = "\n".join(lines)
            if new_content != og and new_content + "\n" != og:
                write_to_file(new_content, f"{file_path}.new")
                report.extend_changed(file_path)
                append_log(self, f"Patched {file_path}.new\n")
            else:
                report.extend_skipped(file_path)
                append_log(self, f"No changes needed for {file_path}\n")
        except Exception as e:
            append_log(self, f"Error applying to {file_path}: {e}\n")
            report.extend_skipped(file_path)

    set_status(self, f"Applied {report.hunks_applied} hunks, skipped {report.hunks_skipped} hunks",
               "ok" if report.hunks_applied else "warn")
    return report
