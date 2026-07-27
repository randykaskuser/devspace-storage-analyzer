import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTreeWidget, QTreeWidgetItem, QMessageBox, 
                               QProgressDialog, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from core.windows_cleaner import scan_windows_storage, empty_recycle_bin
from core.trash import hard_delete_directory_contents
from core.system_info import format_size
from core.db import db

class WindowsStorageScannerThread(QThread):
    finished = Signal(list)
    
    def run(self):
        results = scan_windows_storage()
        self.finished.emit(results)

class WindowsStorageDeleteThread(QThread):
    finished = Signal(int)
    
    def __init__(self, items):
        super().__init__()
        self.items = items
        
    def run(self):
        freed = 0
        for item in self.items:
            if item["type"] == "recycle_bin":
                if empty_recycle_bin():
                    freed += 1
                    db.log_cleanup("Recycle Bin", item["size"])
            else:
                s, f = hard_delete_directory_contents(item["path"])
                if s > 0 or f == 0:
                    freed += 1
                    db.log_cleanup(f"Windows Storage: {item['name']}", item["size"])
                    
        db.increment_session()
        self.finished.emit(freed)

class WindowsStorageTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        lbl_desc = QLabel("Windows Storage Analysis\nDeveloper-relevant Windows caches like Temp, Updates, and Shaders.")
        lbl_desc.setStyleSheet("color: #a9b7c6; padding: 5px 0;")
        
        btn_scan = QPushButton("Scan Windows Storage")
        btn_scan.setStyleSheet("background-color: #2b7042;")
        btn_scan.clicked.connect(self.start_scan)
        self.btn_scan = btn_scan
        
        header_layout.addWidget(lbl_desc)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_scan)
        
        # Tree Widget
        self.tree_results = QTreeWidget()
        self.tree_results.setHeaderLabels(["Category / Item", "Description", "Status", "Size"])
        self.tree_results.setColumnCount(4)
        self.tree_results.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree_results.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree_results.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tree_results.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree_results.itemChanged.connect(self.update_total)
        
        # Bottom bar
        bottom_layout = QHBoxLayout()
        self.lbl_total = QLabel("Selected space to reclaim: 0 B")
        self.btn_clean = QPushButton("Permanently Delete Selected Storage")
        self.btn_clean.setStyleSheet("background-color: #e53935; color: white;")
        self.btn_clean.clicked.connect(self.clean_selected)
        self.btn_clean.setEnabled(False)
        
        bottom_layout.addWidget(self.lbl_total)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_clean)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.tree_results)
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
    def start_scan(self):
        self.tree_results.clear()
        self.btn_clean.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning... Please wait")
        
        self.scanner = WindowsStorageScannerThread()
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.start()
        
    def on_scan_finished(self, results):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Scan Windows Storage")
        
        self.tree_results.blockSignals(True)
        self.tree_results.clear()
        
        # Group by category
        categories = {}
        for r in results:
            cat = r["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)
            
        for cat, items in categories.items():
            cat_item = QTreeWidgetItem([cat, "", "", ""])
            cat_item.setFlags(cat_item.flags() | Qt.ItemIsUserCheckable)
            cat_item.setCheckState(0, Qt.Unchecked)
            
            font = cat_item.font(0)
            font.setBold(True)
            cat_item.setFont(0, font)
            
            cat_size = 0
            
            for i in items:
                child = QTreeWidgetItem([
                    i["name"],
                    i["desc"],
                    i["safety"],
                    format_size(i["size_bytes"])
                ])
                child.setFlags(child.flags() | Qt.ItemIsUserCheckable)
                child.setCheckState(0, Qt.Unchecked)
                child.setData(0, Qt.UserRole, i)
                child.setData(1, Qt.UserRole, i["size_bytes"])
                child.setForeground(0, Qt.gray)
                
                cat_item.addChild(child)
                cat_size += i["size_bytes"]
                
            cat_item.setText(3, format_size(cat_size))
            self.tree_results.addTopLevelItem(cat_item)
            
        self.tree_results.expandAll()
        self.tree_results.blockSignals(False)
        self.update_total()
        
    def update_total(self, item=None, column=0):
        # Auto-check children if parent is checked
        if item and item.childCount() > 0:
            self.tree_results.blockSignals(True)
            state = item.checkState(0)
            for i in range(item.childCount()):
                item.child(i).setCheckState(0, state)
            self.tree_results.blockSignals(False)
            
        total_selected = 0
        has_checked = False
        
        for i in range(self.tree_results.topLevelItemCount()):
            cat_item = self.tree_results.topLevelItem(i)
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    total_selected += child.data(1, Qt.UserRole)
                    has_checked = True
                    
        self.lbl_total.setText(f"Selected space to reclaim: {format_size(total_selected)}")
        self.btn_clean.setEnabled(has_checked)
        
    def clean_selected(self):
        items_to_remove = []
        self.tree_items_to_remove = []
        
        for i in range(self.tree_results.topLevelItemCount()):
            cat_item = self.tree_results.topLevelItem(i)
            for j in range(cat_item.childCount()):
                child = cat_item.child(j)
                if child.checkState(0) == Qt.Checked:
                    data = child.data(0, Qt.UserRole)
                    items_to_remove.append({
                        "name": data["name"],
                        "path": data["path"],
                        "size": data["size_bytes"],
                        "type": data["type"]
                    })
                    self.tree_items_to_remove.append(child)
                    
        if not items_to_remove:
            return
            
        has_moderate = False
        for item in items_to_remove:
            if "Moderate" in item.get("safety", "") or item["name"] == "Windows Update Cache":
                has_moderate = True
                break
                
        warn_text = ""
        if has_moderate:
            warn_text = "\n\nWARNING: You selected some moderate-risk caches (like Windows Update). Ensure you are not currently downloading updates."
            
        reply = QMessageBox.question(
            self, 'Confirm Permanent Deletion',
            f"Are you sure you want to permanently delete {len(items_to_remove)} Windows caches?{warn_text}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.progress = QProgressDialog("Permanently deleting storage...", None, 0, 0, self)
            self.progress.setWindowTitle("Please Wait")
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.show()
            
            self.cleaner = WindowsStorageDeleteThread(items_to_remove)
            self.cleaner.finished.connect(self.on_clean_finished)
            self.cleaner.start()
            
    def on_clean_finished(self, freed):
        self.progress.close()
        for item in self.tree_items_to_remove:
            parent = item.parent()
            parent.removeChild(item)
            if parent.childCount() == 0:
                self.tree_results.takeTopLevelItem(self.tree_results.indexOfTopLevelItem(parent))
                
        QMessageBox.information(self, "Success", f"Successfully deleted {freed} Windows storage items.")
        self.update_total()
