import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QTreeWidget, QTreeWidgetItem, QMessageBox, 
                               QFileDialog, QProgressDialog, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal
from core.repo_cleaner import scan_repos
from core.trash import hard_delete_directory_contents
from core.system_info import format_size
from core.db import db

class RepoScannerThread(QThread):
    finished = Signal(list)
    
    def __init__(self, dirs):
        super().__init__()
        self.dirs = dirs
        
    def run(self):
        results = scan_repos(self.dirs)
        self.finished.emit(results)

class RepoDeleteThread(QThread):
    finished = Signal(int)
    
    def __init__(self, items):
        super().__init__()
        self.items = items
        
    def run(self):
        freed = 0
        for item in self.items:
            s, f = hard_delete_directory_contents(item["path"])
            if s > 0 or f == 0:
                freed += 1
                db.log_cleanup(f"Project Cache: {item['name']}", item["size"])
        db.increment_session()
        self.finished.emit(freed)

class RepoTab(QWidget):
    def __init__(self):
        super().__init__()
        # Load saved directories if any (simple implementation)
        self.target_dirs = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Header
        header_layout = QHBoxLayout()
        lbl_desc = QLabel("Workspaces Analysis\nAdd root folders to find and analyze development projects and their cache sizes.")
        lbl_desc.setStyleSheet("color: #a9b7c6; padding: 5px 0;")
        
        btn_add = QPushButton("Add Folder")
        btn_add.clicked.connect(self.add_folder)
        
        btn_scan = QPushButton("Scan Workspaces")
        btn_scan.setStyleSheet("background-color: #2b7042;")
        btn_scan.clicked.connect(self.start_scan)
        self.btn_scan = btn_scan
        
        header_layout.addWidget(lbl_desc)
        header_layout.addStretch()
        header_layout.addWidget(btn_add)
        header_layout.addWidget(self.btn_scan)
        
        # Directories display
        self.lbl_dirs = QLabel("Folders to scan: None")
        self.lbl_dirs.setStyleSheet("font-weight: bold; color: #4a88c7; margin-bottom: 10px;")
        
        # Tree Widget for Projects
        self.tree_results = QTreeWidget()
        self.tree_results.setHeaderLabels(["Project", "Framework", "Git Branch", "Last Commit", "Status", "Size"])
        self.tree_results.setColumnCount(6)
        for i in range(5):
            self.tree_results.header().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        self.tree_results.header().setSectionResizeMode(5, QHeaderView.Stretch)
        self.tree_results.itemChanged.connect(self.update_total)
        
        # Bottom bar
        bottom_layout = QHBoxLayout()
        self.lbl_total = QLabel("Total reclaimable space: 0 B")
        self.btn_clean = QPushButton("Permanently Delete Selected Caches")
        self.btn_clean.setStyleSheet("background-color: #e53935; color: white;")
        self.btn_clean.clicked.connect(self.clean_selected)
        self.btn_clean.setEnabled(False)
        
        bottom_layout.addWidget(self.lbl_total)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_clean)
        
        layout.addLayout(header_layout)
        layout.addWidget(self.lbl_dirs)
        layout.addWidget(self.tree_results)
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
    def add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Development Root Folder")
        if folder and folder not in self.target_dirs:
            self.target_dirs.append(folder)
            self.lbl_dirs.setText(f"Folders to scan: {', '.join(self.target_dirs)}")
            
    def start_scan(self):
        if not self.target_dirs:
            QMessageBox.warning(self, "No Folders", "Please add at least one folder to scan.")
            return
            
        self.tree_results.clear()
        self.btn_clean.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning... Please wait")
        self.lbl_total.setText("Deep scanning projects... This may take a moment.")
        
        self.scanner = RepoScannerThread(self.target_dirs)
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.start()
        
    def on_scan_finished(self, projects):
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText("Scan Workspaces")
        
        self.tree_results.blockSignals(True)
        self.tree_results.clear()
        
        for p in projects:
            # Create Project Node
            safety = p["safety"]
            color = "#a9b7c6"
            git_branch = p["git_info"].get("branch", "")
            if not git_branch: git_branch = "None"
            
            project_item = QTreeWidgetItem([
                p["project_name"], 
                p["ecosystem"],
                git_branch,
                p["git_info"]["rel_time"],
                safety,
                format_size(p["total_cache_size"])
            ])
            project_item.setFlags(project_item.flags() | Qt.ItemIsUserCheckable)
            project_item.setCheckState(0, Qt.Unchecked)
            
            # Styling
            project_item.setForeground(0, Qt.white)
            font = project_item.font(0)
            font.setBold(True)
            project_item.setFont(0, font)
            
            # No manual coloring needed, we use emojis for Status.
            
            # Sub-items (Caches)
            for c in p["caches"]:
                cache_item = QTreeWidgetItem([
                    c["name"],
                    c["type"],
                    "",
                    "",
                    "",
                    format_size(c["size"])
                ])
                cache_item.setFlags(cache_item.flags() | Qt.ItemIsUserCheckable)
                cache_item.setCheckState(0, Qt.Unchecked)
                cache_item.setData(0, Qt.UserRole, c["path"])
                cache_item.setData(1, Qt.UserRole, c["size"])
                
                cache_item.setForeground(0, Qt.gray)
                project_item.addChild(cache_item)
                
            self.tree_results.addTopLevelItem(project_item)
            
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
            project_item = self.tree_results.topLevelItem(i)
            for j in range(project_item.childCount()):
                cache_item = project_item.child(j)
                if cache_item.checkState(0) == Qt.Checked:
                    total_selected += cache_item.data(1, Qt.UserRole)
                    has_checked = True
                    
        self.lbl_total.setText(f"Selected space to reclaim: {format_size(total_selected)}")
        self.btn_clean.setEnabled(has_checked)
        
    def clean_selected(self):
        items_to_remove = []
        self.tree_items_to_remove = []
        
        for i in range(self.tree_results.topLevelItemCount()):
            project_item = self.tree_results.topLevelItem(i)
            for j in range(project_item.childCount()):
                cache_item = project_item.child(j)
                if cache_item.checkState(0) == Qt.Checked:
                    items_to_remove.append({
                        "path": cache_item.data(0, Qt.UserRole),
                        "name": cache_item.text(0),
                        "size": cache_item.data(1, Qt.UserRole)
                    })
                    self.tree_items_to_remove.append(cache_item)
                    
        if not items_to_remove:
            return
            
        # Warning if any selected item belongs to an active project
        has_active = False
        for item in self.tree_items_to_remove:
            parent = item.parent()
            if "Active" in parent.text(4):
                has_active = True
                break
                
        warn_text = ""
        if has_active:
            warn_text = "\n\nWARNING: You have selected caches from ACTIVE projects. Deleting them may slow down your current workflow."
            
        reply = QMessageBox.question(
            self, 'Confirm Permanent Deletion',
            f"Are you sure you want to permanently delete {len(items_to_remove)} cache folders?{warn_text}",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.progress = QProgressDialog("Permanently deleting caches...", None, 0, 0, self)
            self.progress.setWindowTitle("Please Wait")
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.show()
            
            self.cleaner = RepoDeleteThread(items_to_remove)
            self.cleaner.finished.connect(self.on_clean_finished)
            self.cleaner.start()
            
    def on_clean_finished(self, freed):
        self.progress.close()
        for item in self.tree_items_to_remove:
            parent = item.parent()
            parent.removeChild(item)
            if parent.childCount() == 0:
                self.tree_results.takeTopLevelItem(self.tree_results.indexOfTopLevelItem(parent))
                
        QMessageBox.information(self, "Success", f"Successfully deleted {freed} cache folders.")
        self.update_total()
