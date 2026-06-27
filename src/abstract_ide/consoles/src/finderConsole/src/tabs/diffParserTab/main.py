from .imports import *
class diffParserTab(QWidget):
    def __init__(self, bus: SharedStateBus):
        super().__init__()
        initFuncs(self)
        root = QVBoxLayout(self)
        # Common inputs (dir, filters, etc.)
        grid = QGridLayout()
        install_common_inputs(
            self, grid, bus=bus,
            default_dir_in=os.getcwd(),
            primary_btn=("Preview", self.preview_patch),
            secondary_btn=("Save", self.save_patch),
            trinary_btn=("Save All", (lambda: self.save_all_checked())),
            default_allowed_exts_in=False,
            default_exclude_dirs_in=True
        )

        # Files tree (match results)
        root.addWidget(QLabel("Files found:"))
        self.files_list = QTreeWidget()
        self.files_list.setColumnCount(3)
        self.files_list.setHeaderLabels(["File", "Apply", "Overwrite"])
        self.files_list.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.files_list.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.files_list.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.files_list.setRootIsDecorated(False)
        # handlers
        self.files_list.itemDoubleClicked.connect(self._open_file_from_row)
        self.files_list.currentItemChanged.connect(lambda *_: self._on_tree_selection_changed())
        root.addWidget(self.files_list, stretch=1)

        # Diff / Preview split
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)

        left = QWidget(); lv = QVBoxLayout(left); lv.setContentsMargins(0,0,0,0)
        lv.addWidget(QLabel("Diff:"))
        self.diff_text = QTextEdit()
        self.diff_text.setPlaceholderText("Paste the diff here...")
        lv.addWidget(self.diff_text, stretch=1)

        right = QWidget(); rv = QVBoxLayout(right); rv.setContentsMargins(0,0,0,0)
        rv.addWidget(QLabel("Preview:"))
        self.preview = QTextEdit(); self.preview.setReadOnly(True)
        rv.addWidget(self.preview, stretch=1)

        self.splitter.addWidget(left)
        self.splitter.addWidget(right)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 1)
        root.addWidget(self.splitter, stretch=3)

        # Actions
##        btn_preview = QPushButton("Parse and Preview")
##        btn_preview.clicked.connect(self.preview_patch)
##        root.addWidget(btn_preview)
##
##        btn_save = QPushButton("Approve and Save")
##        btn_save.clicked.connect(self.save_patch)
##        root.addWidget(btn_save)
##        
##        self.saveAllBtn = QPushButton("Approve and Save All")
##        self.saveAllBtn.clicked.connect(lambda: self.save_all_checked()) 
##        root.addWidget(self.saveAllBtn)
        
        # Status line
        self.status_label = QLabel("Ready.")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.status_label.setStyleSheet("color: #4caf50; padding: 4px 0;")
        root.addWidget(self.status_label)

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

    def _open_file_from_row(self, item: QTreeWidgetItem, column: int):
        path = item.data(0, Qt.ItemDataRole.UserRole) or item.text(0)
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
