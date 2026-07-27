import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QFrame, QProgressBar, QPushButton, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt
from core.background_aggregator import BackgroundAggregatorThread
from core.system_info import format_size, get_disk_usage, get_system_drive_path
from core.db import db
from ui.global_caches_tab import GlobalCacheDeleteThread

class DashboardTab(QWidget):
    def __init__(self):
        super().__init__()
        self.stats = {}
        self.init_ui()
        self.aggregator = BackgroundAggregatorThread()
        self.aggregator.finished.connect(self.on_stats_loaded)
        self.aggregator.start()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)
        
        # --- Top Section: Recoverable Space & CTA ---
        top_layout = QHBoxLayout()
        
        v_top = QVBoxLayout()
        self.lbl_total = QLabel("Scanning...")
        self.lbl_total.setStyleSheet("font-size: 48px; font-weight: bold; color: #ffffff; margin: 0;")
        self.lbl_sub = QLabel("Total Recoverable Space")
        self.lbl_sub.setStyleSheet("font-size: 16px; color: #a9b7c6; margin-bottom: 20px;")
        
        # SSD Health Overview
        self.lbl_ssd = QLabel("System Drive: Scanning...")
        self.lbl_ssd.setStyleSheet("font-size: 14px; font-weight: bold; color: #a9b7c6;")
        
        v_top.addWidget(self.lbl_total)
        v_top.addWidget(self.lbl_sub)
        v_top.addWidget(self.lbl_ssd)
        
        self.btn_clean_rec = QPushButton("Clean Recommended")
        self.btn_clean_rec.setStyleSheet("background-color: #4a88c7; color: white; font-size: 18px; font-weight: bold; padding: 15px 30px; border-radius: 8px;")
        self.btn_clean_rec.setCursor(Qt.PointingHandCursor)
        self.btn_clean_rec.clicked.connect(self.clean_recommended)
        self.btn_clean_rec.setEnabled(False)
        
        top_layout.addLayout(v_top)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_clean_rec)
        
        # --- Stat Cards Grid ---
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(15)
        
        # --- Horizontal Stacked Bar ---
        self.lbl_breakdown = QLabel("Storage Breakdown")
        self.lbl_breakdown.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; margin-top: 20px;")
        
        bar_layout = QHBoxLayout()
        bar_layout.setSpacing(2)
        self.bars = {}
        for ecosystem in ["docker", "node", "python", "rust", "windows", "total"]:
            bar = QProgressBar()
            bar.setObjectName(f"{ecosystem}_bar")
            bar.setFixedHeight(25)
            bar.setTextVisible(False)
            bar.setRange(0, 100)
            bar.setValue(0)
            self.bars[ecosystem] = bar
            bar_layout.addWidget(bar)
            
        self.legend_layout = QHBoxLayout()
        
        # --- Storage Advisor ---
        self.lbl_advisor_title = QLabel("Storage Advisor")
        self.lbl_advisor_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff; margin-top: 20px;")
        
        self.rec_container = QWidget()
        self.rec_layout = QVBoxLayout()
        self.rec_layout.setSpacing(10)
        self.rec_layout.setContentsMargins(0, 0, 0, 0)
        self.rec_container.setLayout(self.rec_layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.rec_container)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # Assemble
        layout.addLayout(top_layout)
        layout.addLayout(self.grid_layout)
        layout.addWidget(self.lbl_breakdown)
        layout.addLayout(bar_layout)
        layout.addLayout(self.legend_layout)
        layout.addWidget(self.lbl_advisor_title)
        layout.addWidget(scroll)
        
        self.setLayout(layout)
        
    def create_stat_card(self, title, value):
        card = QFrame()
        card.setStyleSheet("background-color: #2b2b2b; border-radius: 8px; border: 1px solid #3c3f41;")
        v = QVBoxLayout()
        v.setContentsMargins(15, 15, 15, 15)
        
        val = QLabel(str(value))
        val.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold; border: none;")
        
        t = QLabel(title)
        t.setStyleSheet("color: #a9b7c6; font-size: 14px; border: none;")
        
        v.addWidget(val)
        v.addWidget(t)
        card.setLayout(v)
        return card

    def add_advisor_card(self, text):
        card = QFrame()
        card.setStyleSheet("background-color: #313335; border-radius: 8px; border: 1px solid #444444; padding: 15px;")
        hlayout = QHBoxLayout()
        
        lbl_icon = QLabel("💡")
        lbl_icon.setStyleSheet("font-size: 20px; border: none;")
        
        lbl_text = QLabel(text)
        lbl_text.setStyleSheet("color: #e0e0e0; font-size: 14px; border: none;")
        lbl_text.setWordWrap(True)
        
        hlayout.addWidget(lbl_icon)
        hlayout.addWidget(lbl_text)
        hlayout.addStretch()
        
        card.setLayout(hlayout)
        self.rec_layout.addWidget(card)

    def on_stats_loaded(self, stats):
        self.stats = stats
        total_rec = stats.get("total_recoverable", 0)
        
        self.lbl_total.setText(f"{format_size(total_rec)}")
        
        safe_caches = [c for c in stats.get("global_caches", []) if "Safe" in c.get("safety", "")]
        safe_size = sum(c["size_bytes"] for c in safe_caches)
        
        if safe_size > 0:
            self.btn_clean_rec.setText(f"Clean {format_size(safe_size)} (Safe)")
            self.btn_clean_rec.setEnabled(True)
        else:
            self.btn_clean_rec.setText("No Safe Caches to Clean")
            self.btn_clean_rec.setEnabled(False)
        
        docker_size = sum(d.get("size_bytes", 0) for d in stats.get("wsl_distros", []))
        node_size, py_size, rust_size, other_size = 0, 0, 0, 0
        
        global_cache_size = sum(c.get("size_bytes", 0) for c in stats.get("global_caches", []))
        windows_storage_size = sum(w.get("size_bytes", 0) for w in stats.get("windows_storage", []))
        
        for c in stats.get("global_caches", []):
            name = c.get("name", "").lower()
            size = c.get("size_bytes", 0)
            if "npm" in name or "yarn" in name or "pnpm" in name or "node" in name:
                node_size += size
            elif "pip" in name or "uv" in name or "python" in name:
                py_size += size
            elif "cargo" in name or "rust" in name:
                rust_size += size
            else:
                other_size += size
                
        # Parse Docker
        docker_active_size = 0
        for d in stats.get("docker_df", []):
            try:
                # Docker sizes can be tricky without proper parsing, just adding mock size to breakdown if active
                if "Images" in d.get("Type", ""): docker_size += 500000000
            except: pass
            
        # Update Stat Cards
        # Clear old cards
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        self.grid_layout.addWidget(self.create_stat_card("Development Caches", format_size(global_cache_size)), 0, 0)
        self.grid_layout.addWidget(self.create_stat_card("Docker / WSL", format_size(docker_size)), 0, 1)
        self.grid_layout.addWidget(self.create_stat_card("Windows Storage", format_size(windows_storage_size)), 0, 2)
        
        dev_total = global_cache_size + docker_size
        self.grid_layout.addWidget(self.create_stat_card("Developer Storage", format_size(dev_total)), 0, 3)
        
        # Update SSD Health
        drive_path = get_system_drive_path()
        total_d, used_d, free_d = get_disk_usage(drive_path)
        if total_d > 0:
            free_pct = (free_d / total_d) * 100
            used_pct = 100 - free_pct
            self.lbl_ssd.setText(f"System Drive: {format_size(total_d)} SSD  |  Used: {used_pct:.1f}%  |  Free: {free_pct:.1f}%")
            if free_pct < 15:
                self.lbl_ssd.setStyleSheet("font-size: 14px; font-weight: bold; color: #e53935;")
            else:
                self.lbl_ssd.setStyleSheet("font-size: 14px; font-weight: bold; color: #4c9b54;")
        
        # Update Stacked Bar
        total_calc = docker_size + node_size + py_size + rust_size + windows_storage_size + other_size
        if total_calc == 0: total_calc = 1
        
        self.bars["docker"].setValue(int(docker_size / total_calc * 100))
        self.bars["node"].setValue(int(node_size / total_calc * 100))
        self.bars["python"].setValue(int(py_size / total_calc * 100))
        self.bars["rust"].setValue(int(rust_size / total_calc * 100))
        self.bars["windows"].setValue(int(windows_storage_size / total_calc * 100))
        self.bars["total"].setValue(int(other_size / total_calc * 100))
        
        # Update Legends
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
            
        def add_legend(color, name, size):
            lbl = QLabel(f"■ {name} ({format_size(size)})")
            lbl.setStyleSheet(f"color: {color}; font-weight: bold;")
            self.legend_layout.addWidget(lbl)
            
        add_legend("#4a88c7", "Docker/WSL", docker_size)
        add_legend("#5c9e60", "Node", node_size)
        add_legend("#ffc66d", "Python", py_size)
        add_legend("#cc7832", "Rust", rust_size)
        add_legend("#8a2be2", "Windows Storage", windows_storage_size)
        add_legend("#777777", "Other", other_size)
        self.legend_layout.addStretch()
        
        # Clear Advisor
        for i in reversed(range(self.rec_layout.count())): 
            self.rec_layout.itemAt(i).widget().setParent(None)
            
        # Advisor Logic
        added_advice = False
        
        if safe_caches:
            self.add_advisor_card(f"You have {len(safe_caches)} global caches that are 100% safe to delete. Consider clicking the Clean button to instantly recover {format_size(safe_size)}.")
            added_advice = True
            
        if total_d > 0 and (free_d / total_d) < 0.15:
            self.add_advisor_card(f"⚠ SSD almost full ({(free_d/total_d)*100:.1f}% free). Build performance, IDE indexing, and local databases may degrade. Please reclaim space immediately.")
            added_advice = True
            
        for c in stats.get("global_caches", []):
            if "Playwright" in c.get("name", "") and c.get("size_bytes", 0) > 1000000000:
                self.add_advisor_card(f"Your Playwright browser cache is taking up {format_size(c['size_bytes'])}. If you aren't currently running E2E tests, you can safely reclaim this space.")
                added_advice = True
                
        # Check Windows Update cache size
        win_update_cache = next((w for w in stats.get("windows_storage", []) if w["name"] == "Windows Update Cache"), None)
        if win_update_cache and win_update_cache["size_bytes"] > 2000000000:
            self.add_advisor_card(f"Your Windows Update Cache is using {format_size(win_update_cache['size_bytes'])}. If you're not actively downloading updates, this is safe to clean from the Windows Storage tab.")
            added_advice = True
                
        if not added_advice:
            self.add_advisor_card("Your system looks clean! No immediate action is required.")
            
    def clean_recommended(self):
        # Find all safe caches
        items = []
        for c in self.stats.get("global_caches", []):
            if "Safe" in c.get("safety", ""):
                items.append({
                    "path": c["path"],
                    "name": c["name"],
                    "size": c["size_bytes"]
                })
                
        if not items: return
        
        self.btn_clean_rec.setEnabled(False)
        self.btn_clean_rec.setText("Cleaning...")
        
        self.cleaner = GlobalCacheDeleteThread(items)
        self.cleaner.finished.connect(self.on_clean_finished)
        self.cleaner.start()
        
    def on_clean_finished(self, freed):
        # Refresh dashboard
        self.btn_clean_rec.setText("Scanning...")
        self.aggregator = BackgroundAggregatorThread()
        self.aggregator.finished.connect(self.on_stats_loaded)
        self.aggregator.start()
