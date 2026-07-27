import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QMessageBox, QProgressDialog, QCheckBox, 
                               QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from core.global_cache_cleaner import scan_global_caches
from core.trash import hard_delete_directory_contents
from core.system_info import format_size
from core.db import db

class GlobalCacheScannerThread(QThread):
    finished = Signal(list)
    
    def run(self):
        caches = scan_global_caches()
        self.finished.emit(caches)

class GlobalCacheDeleteThread(QThread):
    finished = Signal(int)
    
    def __init__(self, items):
        super().__init__()
        self.items = items # List of dicts: {"name": "...", "path": "...", "size": 123}
        
    def run(self):
        freed = 0
        for item in self.items:
            s, f = hard_delete_directory_contents(item["path"])
            if s > 0 or f == 0:
                freed += 1
                db.log_cleanup(f"Global Cache: {item['name']}", item["size"])
        db.increment_session()
        self.finished.emit(freed)

class GlobalCachesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.items_to_remove = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        lbl_desc = QLabel("Global Caches (npm, pip, cargo, etc.) usually take up gigabytes of space over time.\nIt is safe to delete them; package managers will simply redownload what they need later.")
        lbl_desc.setStyleSheet("color: #a9b7c6; padding: 10px 0;")
        
        btn_scan = QPushButton("Scan Global Caches")
        btn_scan.clicked.connect(self.start_scan)
        self.btn_scan = btn_scan
        
        header_layout.addWidget(lbl_desc)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_scan)
        
        # Selection tools
        selection_layout = QHBoxLayout()
        btn_select_all = QPushButton("Select All")
        btn_select_all.clicked.connect(self.select_all)
        btn_deselect_all = QPushButton("Deselect All")
        btn_deselect_all.clicked.connect(self.deselect_all)
        
        selection_layout.addStretch()
        selection_layout.addWidget(btn_select_all)
        selection_layout.addWidget(btn_deselect_all)
        
        # List widget
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Name", "Path", "Recommendation", "Size"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.itemChanged.connect(self.update_total)
        
        # Bottom bar
        bottom_layout = QHBoxLayout()
        self.lbl_total = QLabel("Total reclaimable space: 0 B")
        self.btn_clean = QPushButton("Permanently Delete Selected")
        self.btn_clean.setStyleSheet("background-color: #e53935; color: white;")
        self.btn_clean.clicked.connect(self.clean_selected)
        self.btn_clean.setEnabled(False)
        
        bottom_layout.addWidget(self.lbl_total)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_clean)
        
        # Add to layout
        layout.addLayout(header_layout)
        layout.addLayout(selection_layout)
        layout.addWidget(self.table)
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
    def start_scan(self):
        self.table.setRowCount(0)
        self.btn_clean.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning... Please wait")
        self.lbl_total.setText("Scanning global developer caches...")
        
        self.scanner = GlobalCacheScannerThread()
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.start()
        
    def on_scan_finished(self, results):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Scan Global Caches")
        self.table.setRowCount(0)
        total_size = 0
        
        for c in results:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            # Name
            item_name = QTableWidgetItem(c["name"])
            item_name.setFlags((item_name.flags() ^ Qt.ItemIsEditable) | Qt.ItemIsUserCheckable)
            item_name.setCheckState(Qt.Unchecked)
            
            # Path
            item_path = QTableWidgetItem(c["path"])
            item_path.setFlags(item_path.flags() ^ Qt.ItemIsEditable)
            item_path.setForeground(Qt.gray)
            
            # Recommendation (No manual text coloring needed since we use Emojis now)
            safety = c.get("safety", "")
            item_rec = QTableWidgetItem(safety)
            item_rec.setFlags(item_rec.flags() ^ Qt.ItemIsEditable)
            
            # Size
            item_size = QTableWidgetItem(format_size(c["size_bytes"]))
            item_size.setFlags(item_size.flags() ^ Qt.ItemIsEditable)
            item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            # Data
            item_size.setData(Qt.UserRole, {
                "size_bytes": c["size_bytes"],
                "name": c["name"]
            })
            
            self.table.setItem(row, 0, item_name)
            self.table.setItem(row, 1, item_path)
            self.table.setItem(row, 2, item_rec)
            self.table.setItem(row, 3, item_size)
            total_size += c["size_bytes"]
            
        self.lbl_total.setText(f"Found {len(results)} caches. Total size: {format_size(total_size)}")
        
    def update_total(self, item=None):
        total_selected = 0
        has_checked = False
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.Checked:
                data = self.table.item(i, 3).data(Qt.UserRole)
                total_selected += data["size_bytes"]
                has_checked = True
        self.lbl_total.setText(f"Selected space to reclaim: {format_size(total_selected)}")
        self.btn_clean.setEnabled(has_checked)
        
    def select_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Checked)
            
    def deselect_all(self):
        for i in range(self.table.rowCount()):
            self.table.item(i, 0).setCheckState(Qt.Unchecked)
            
    def clean_selected(self):
        items = []
        has_unsafe = False
        
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.Checked:
                data = self.table.item(row, 3).data(Qt.UserRole)
                items.append({
                    "path": self.table.item(row, 1).text(),
                    "name": data["name"],
                    "size": data["size_bytes"]
                })
                
                # Check safety rating of selected items
                rec = self.table.item(row, 2).text()
                if "Moderate" in rec or "Rebuild" in rec:
                    has_unsafe = True
                
        if not items:
            return
            
        warn_text = ""
        if has_unsafe:
            warn_text = "\n\nWARNING: You selected caches that might require long rebuild times (e.g. Cargo, Gradle). Proceed?"
            
        reply = QMessageBox.question(
            self, 'Confirm Permanent Deletion',
            f"Are you sure you want to permanently delete {len(items)} global caches?{warn_text}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.progress = QProgressDialog("Permanently deleting caches...", None, 0, 0, self)
            self.progress.setWindowTitle("Please Wait")
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.show()
            
            self.cleaner = GlobalCacheDeleteThread(items)
            self.cleaner.finished.connect(self.on_clean_finished)
            self.cleaner.start()
            
    def on_clean_finished(self, freed):
        self.progress.close()
        QMessageBox.information(self, "Success", f"Successfully deleted {freed} cache folders.")
        self.start_scan()
