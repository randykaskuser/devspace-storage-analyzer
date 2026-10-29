import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QMessageBox, QProgressDialog, QFileDialog,
                               QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from core.duplicate_finder import find_duplicates, trash_duplicates
from core.repo_cleaner import is_broad_scan_root
from core.system_info import format_size


class DuplicateScanThread(QThread):
    finished = Signal(list, list)  # (groups, errors)
    progress = Signal(int)         # files_seen, emitted from the worker thread (queued to UI)

    def __init__(self, roots):
        super().__init__()
        self.roots = roots

    def run(self):
        def _on_progress(files_seen):
            self.progress.emit(files_seen)

        groups, errors = find_duplicates(self.roots, on_progress=_on_progress)
        self.finished.emit(groups, errors)


class DuplicateDeleteThread(QThread):
    finished = Signal(int, int)  # (trashed, failed)

    def __init__(self, paths):
        super().__init__()
        self.paths = paths

    def run(self):
        trashed, failed = trash_duplicates(self.paths)
        self.finished.emit(trashed, failed)


class DuplicatesTab(QWidget):
    """Duplicates tab: pick a folder, find byte-identical files, move the extra
    copies to the OS Recycle Bin/Trash. Never a permanent delete."""

    def __init__(self):
        super().__init__()
        self.root = ""
        self.last_scan_groups = 0
        self.last_scan_errors = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Header
        header_layout = QHBoxLayout()
        lbl_desc = QLabel("Find byte-identical files (size + SHA-256) in a folder you pick.\n"
                          "One copy of each group is kept; the extras go to the Recycle Bin/Trash, never deleted permanently.")
        lbl_desc.setStyleSheet("color: #a9b7c6; padding: 10px 0;")

        self.lbl_root = QLabel("No folder selected")
        self.lbl_root.setStyleSheet("color: #7a8899; padding: 10px 0;")

        btn_folder = QPushButton("Choose Folder...")
        btn_folder.clicked.connect(self.choose_folder)
        self.btn_folder = btn_folder

        btn_scan = QPushButton("Scan for Duplicates")
        btn_scan.clicked.connect(self.start_scan)
        self.btn_scan = btn_scan

        header_layout.addWidget(lbl_desc)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_root)
        header_layout.addWidget(self.btn_folder)
        header_layout.addWidget(self.btn_scan)

        # Selection tools
        selection_layout = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self.select_all)
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.clicked.connect(self.deselect_all)
        btn_auto = QPushButton("Auto-select Duplicates")
        btn_auto.setToolTip("Check every copy except the first one in each group")
        btn_auto.clicked.connect(self.auto_select)

        selection_layout.addStretch()
        selection_layout.addWidget(btn_auto)
        selection_layout.addWidget(btn_select_all)
        selection_layout.addWidget(btn_deselect_all)

        # List widget: one row per duplicate file
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "Path", "Group", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self.update_total)

        # Bottom bar
        bottom_layout = QHBoxLayout()
        self.lbl_total = QLabel("Choose a folder and scan to find duplicate files.")
        self.btn_clean = QPushButton("Move Selected to Trash")
        self.btn_clean.setStyleSheet("background-color: #e53935; color: white;")
        self.btn_clean.clicked.connect(self.clean_selected)
        self.btn_clean.setEnabled(False)

        bottom_layout.addWidget(self.lbl_total)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_clean)

        layout.addLayout(header_layout)
        layout.addLayout(selection_layout)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)

        self.setLayout(layout)

    def choose_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Choose folder to scan for duplicates")
        if not chosen:
            return
        if not os.path.isabs(chosen) or not os.path.isdir(chosen):
            QMessageBox.warning(self, "Invalid Folder", "Please choose an existing folder.")
            return
        if is_broad_scan_root(chosen):
            reply = QMessageBox.question(
                self, "Scan a very broad folder?",
                f"Scanning {chosen} will walk your whole drive or home folder. "
                "That can take a very long time and will hash every file it finds. "
                "Pick a smaller folder instead, or continue anyway?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        self.root = chosen
        self.lbl_root.setText(f"Folder: {self.root}")
        self.lbl_root.setStyleSheet("color: #a9b7c6; padding: 10px 0;")

    def start_scan(self):
        if not self.root:
            QMessageBox.information(self, "No Folder", "Choose a folder first, then scan.")
            return

        self.table.setRowCount(0)
        self.btn_clean.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning... Please wait")
        self.lbl_total.setText("Scanning files...")

        self.scanner = DuplicateScanThread([self.root])
        self.scanner.progress.connect(self.on_scan_progress)
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.start()

    def on_scan_progress(self, files_seen):
        self.lbl_total.setText(f"Scanning files... ({files_seen} seen)")

    def on_scan_finished(self, groups, errors):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Scan for Duplicates")
        self.last_scan_groups = len(groups)
        self.last_scan_errors = len(errors)

        # Block itemChanged while rows are half-populated: setItem() emits it
        # per cell and update_total() assumes every row is complete.
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        for gi, group in enumerate(groups, start=1):
            label = f"Group {gi} · {len(group['paths'])} copies"
            for pi, path in enumerate(group["paths"]):
                row = self.table.rowCount()
                self.table.insertRow(row)

                # Checkbox: auto-check every copy except the first (the kept one)
                item_check = QTableWidgetItem()
                item_check.setFlags((item_check.flags() ^ Qt.ItemIsEditable) | Qt.ItemIsUserCheckable)
                item_check.setCheckState(Qt.Unchecked if pi == 0 else Qt.Checked)

                item_path = QTableWidgetItem(path)
                item_path.setFlags(item_path.flags() ^ Qt.ItemIsEditable)
                if pi == 0:
                    item_path.setForeground(Qt.gray)

                item_group = QTableWidgetItem(label)
                item_group.setFlags(item_group.flags() ^ Qt.ItemIsEditable)

                item_size = QTableWidgetItem(format_size(group["size"]))
                item_size.setFlags(item_size.flags() ^ Qt.ItemIsEditable)
                item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                item_size.setData(Qt.UserRole, {
                    "path": path,
                    "size_bytes": group["size"],
                    "group": gi,
                    "is_first": pi == 0,
                })

                self.table.setItem(row, 0, item_check)
                self.table.setItem(row, 1, item_path)
                self.table.setItem(row, 2, item_group)
                self.table.setItem(row, 3, item_size)

        self.table.blockSignals(False)
        self.update_total()

    def _checked_rows(self):
        rows = []
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.Checked:
                rows.append(i)
        return rows

    def update_total(self, item=None):
        total_selected = 0
        checked = 0
        for i in range(self.table.rowCount()):
            size_item = self.table.item(i, 3)
            data = size_item.data(Qt.UserRole) if size_item is not None else None
            if data is None:
                continue  # row still being populated; skip, don't crash
            if self.table.item(i, 0).checkState() == Qt.Checked:
                total_selected += data["size_bytes"]
                checked += 1
        note = f" · {self.last_scan_errors} path errors" if self.last_scan_errors else ""
        self.lbl_total.setText(
            f"Found {self.last_scan_groups} duplicate groups · "
            f"Selected {checked} files · reclaimable: {format_size(total_selected)}{note}"
        )
        self.btn_clean.setEnabled(checked > 0)

    def select_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Checked)

    def deselect_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Unchecked)

    def auto_select(self):
        """Check every copy except the first one in each group (the kept copy)."""
        for i in range(self.table.rowCount()):
            data = self.table.item(i, 3).data(Qt.UserRole)
            self.table.item(i, 0).setCheckState(Qt.Unchecked if data["is_first"] else Qt.Checked)

    def clean_selected(self):
        paths = []
        kept_selected = 0
        for i in self._checked_rows():
            data = self.table.item(i, 3).data(Qt.UserRole)
            paths.append(data["path"])
            if data["is_first"]:
                kept_selected += 1

        if not paths:
            return

        if kept_selected:
            confirm_text = (
                f"Move {len(paths)} duplicate files to the Recycle Bin/Trash?\n\n"
                f"WARNING: this includes the kept copy of {kept_selected} group(s) — "
                "those groups will have no copies left outside the Trash.\n"
                "Files can still be restored from the Recycle Bin/Trash afterwards."
            )
        else:
            confirm_text = (
                f"Move {len(paths)} duplicate files to the Recycle Bin/Trash?\n\n"
                "One copy of each group is kept. Files can be restored from the Recycle Bin/Trash afterwards."
            )

        reply = QMessageBox.question(
            self, "Confirm Move to Trash", confirm_text,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # No new scan while a delete is in flight: the table would
            # repopulate with rows for paths being trashed.
            self.btn_scan.setEnabled(False)
            self.btn_folder.setEnabled(False)

            self.progress = QProgressDialog("Moving files to Trash...", None, 0, 0, self)
            self.progress.setWindowTitle("Please Wait")
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.show()

            self.cleaner = DuplicateDeleteThread(paths)
            self.cleaner.finished.connect(self.on_clean_finished)
            self.cleaner.start()

    def on_clean_finished(self, trashed, failed):
        self.progress.close()
        self.btn_folder.setEnabled(True)
        if failed:
            QMessageBox.warning(self, "Finished with Errors",
                                f"Moved {trashed} files to the Recycle Bin/Trash. {failed} could not be moved.")
        else:
            QMessageBox.information(self, "Done",
                                    f"Moved {trashed} files to the Recycle Bin/Trash.")
        self.start_scan()
