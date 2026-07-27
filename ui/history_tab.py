import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QFrame)
from PySide6.QtCore import Qt
from core.db import db
from core.system_info import format_size

class HistoryTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.load_data()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        lbl_title = QLabel("📖 Cleanup History")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        
        lbl_desc = QLabel("Track your storage recovery over time.")
        lbl_desc.setStyleSheet("color: #a9b7c6; margin-bottom: 20px;")
        
        # Summary Stats
        self.stats_layout = QHBoxLayout()
        self.stats_layout.setSpacing(20)
        
        # History Table
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Date & Time", "Item", "Space Recovered"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #2b2b2b;
                border: 1px solid #3c3f41;
                gridline-color: #3c3f41;
                color: #a9b7c6;
            }
            QHeaderView::section {
                background-color: #3c3f41;
                color: #ffffff;
                padding: 5px;
                border: 1px solid #2b2b2b;
            }
        """)
        
        layout.addWidget(lbl_title)
        layout.addWidget(lbl_desc)
        layout.addLayout(self.stats_layout)
        layout.addSpacing(20)
        layout.addWidget(self.table)
        
        self.setLayout(layout)
        
    def create_stat_card(self, title, value, color="#ffffff"):
        card = QFrame()
        card.setStyleSheet("background-color: #313335; border-radius: 8px; border: 1px solid #444444;")
        v = QVBoxLayout()
        v.setContentsMargins(15, 15, 15, 15)
        
        t = QLabel(title)
        t.setStyleSheet("color: #a9b7c6; font-size: 14px; border: none;")
        
        val = QLabel(str(value))
        val.setStyleSheet(f"color: {color}; font-size: 24px; font-weight: bold; border: none;")
        
        v.addWidget(t)
        v.addWidget(val)
        card.setLayout(v)
        return card

    def load_data(self):
        # Clear existing
        while self.stats_layout.count():
            item = self.stats_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.table.setRowCount(0)
        
        stats = db.get_stats()
        history = db.get_history()
        
        # Calculate time-based stats
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        last_week = today - timedelta(days=7)
        
        recovered_today = 0
        recovered_yesterday = 0
        recovered_last_week = 0
        
        for entry in history:
            try:
                date_obj = datetime.fromisoformat(entry["timestamp"]).date()
                if date_obj == today:
                    recovered_today += entry["bytes_freed"]
                if date_obj == yesterday:
                    recovered_yesterday += entry["bytes_freed"]
                if date_obj >= last_week:
                    recovered_last_week += entry["bytes_freed"]
            except:
                pass
                
        # Populate Stats Cards
        self.stats_layout.addWidget(self.create_stat_card("Today", format_size(recovered_today), "#4c9b54"))
        self.stats_layout.addWidget(self.create_stat_card("Yesterday", format_size(recovered_yesterday)))
        self.stats_layout.addWidget(self.create_stat_card("Last 7 Days", format_size(recovered_last_week)))
        self.stats_layout.addWidget(self.create_stat_card("Lifetime Recovered", format_size(stats.get("lifetime_freed_bytes", 0)), "#4a88c7"))
        
        # Populate Table
        for entry in history:
            row = self.table.rowCount()
            self.table.insertRow(row)
            
            try:
                dt = datetime.fromisoformat(entry["timestamp"])
                time_str = dt.strftime("%Y-%m-%d %H:%M")
            except:
                time_str = entry["date"]
                
            item_time = QTableWidgetItem(time_str)
            item_time.setForeground(Qt.gray)
            
            item_name = QTableWidgetItem(entry["item"])
            item_name.setForeground(Qt.white)
            
            item_size = QTableWidgetItem(format_size(entry["bytes_freed"]))
            item_size.setForeground(Qt.green)
            item_size.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            
            self.table.setItem(row, 0, item_time)
            self.table.setItem(row, 1, item_name)
            self.table.setItem(row, 2, item_size)
