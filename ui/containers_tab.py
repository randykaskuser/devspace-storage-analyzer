import os
import subprocess
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                               QLabel, QMessageBox, QProgressDialog, QFrame)
from PySide6.QtCore import Qt, QThread, Signal
from core.system_info import format_size, is_admin

class DockerScanThread(QThread):
    finished = Signal(dict)
    
    def run(self):
        stats = {"docker_df": [], "wsl": []}
        try:
            result = subprocess.run(["docker", "system", "df", "--format", "{{json .}}"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip():
                        stats["docker_df"].append(json.loads(line))
        except:
            pass
            
        try:
            local_appdata = os.environ.get("LOCALAPPDATA", "")
            packages_dir = os.path.join(local_appdata, "Packages")
            if os.path.exists(packages_dir):
                for pkg in os.listdir(packages_dir):
                    vhdx_path = os.path.join(packages_dir, pkg, "LocalState", "ext4.vhdx")
                    if os.path.exists(vhdx_path):
                        size = os.path.getsize(vhdx_path)
                        distro_name = pkg.split('_')[0]
                        if "Canonical" in pkg: distro_name = "Ubuntu"
                        elif "Debian" in pkg: distro_name = "Debian"
                        elif "SUSE" in pkg: distro_name = "SUSE"
                        stats["wsl"].append({"name": distro_name, "size": format_size(size)})
        except:
            pass
        self.finished.emit(stats)

class DockerCompactThread(QThread):
    finished = Signal(bool, str)
    
    def run(self):
        vhdx_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Docker", "wsl", "data", "ext4.vhdx")
        if not os.path.exists(vhdx_path):
            self.finished.emit(False, "Docker WSL data file not found.")
            return
            
        try:
            # Shutdown WSL first
            subprocess.run(["wsl", "--shutdown"], creationflags=subprocess.CREATE_NO_WINDOW)
            
            # Create diskpart script
            script_path = os.path.join(os.environ.get("TEMP", ""), "compact_docker.txt")
            with open(script_path, "w") as f:
                f.write(f'select vdisk file="{vhdx_path}"\nattach vdisk readonly\ncompact vdisk\ndetach vdisk\n')
                
            # Run diskpart
            result = subprocess.run(["diskpart", "/s", script_path], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if result.returncode == 0:
                self.finished.emit(True, "Successfully compacted Docker VHDX!")
            else:
                self.finished.emit(False, f"DiskPart failed:\n{result.stderr}")
                
        except Exception as e:
            self.finished.emit(False, str(e))

class ContainersTab(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()
        
        self.scanner = DockerScanThread()
        self.scanner.finished.connect(self.on_scan_finished)
        self.scanner.start()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        lbl_title = QLabel("🐳 Containers & WSL2")
        lbl_title.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        
        self.lbl_loading = QLabel("Scanning Docker Engine and WSL...")
        self.lbl_loading.setStyleSheet("color: #a9b7c6; margin-bottom: 20px;")
        
        # Docker Stats Container
        self.docker_stats = QHBoxLayout()
        self.wsl_stats = QVBoxLayout()
        
        # Action Area
        action_layout = QVBoxLayout()
        action_layout.setContentsMargins(0, 30, 0, 0)
        
        lbl_desc = QLabel(
            "Docker Desktop on Windows uses a dynamic virtual disk (ext4.vhdx) that grows over time but never shrinks automatically.\n"
            "Even if you delete containers and images, the disk space is not returned to Windows."
        )
        lbl_desc.setStyleSheet("color: #a9b7c6;")
        
        # Check Docker VHDX
        vhdx_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Docker", "wsl", "data", "ext4.vhdx")
        size_str = "Not Found"
        if os.path.exists(vhdx_path):
            size = os.path.getsize(vhdx_path)
            size_str = format_size(size)
            
        self.lbl_status = QLabel(f"Host ext4.vhdx size: {size_str}")
        self.lbl_status.setStyleSheet("font-size: 16px; font-weight: bold; color: #4a88c7; margin-top: 10px; margin-bottom: 10px;")
        
        self.btn_compact = QPushButton("Compact Docker Disk (Requires Admin)")
        self.btn_compact.setStyleSheet("background-color: #2b7042; font-size: 14px; padding: 10px;")
        self.btn_compact.clicked.connect(self.compact_disk)
        
        if not is_admin():
            self.btn_compact.setEnabled(False)
            self.btn_compact.setText("Compact Docker Disk (Restart App as Admin to unlock)")
            
        action_layout.addWidget(lbl_desc)
        action_layout.addWidget(self.lbl_status)
        action_layout.addWidget(self.btn_compact)
        
        layout.addWidget(lbl_title)
        layout.addWidget(self.lbl_loading)
        layout.addLayout(self.docker_stats)
        layout.addSpacing(20)
        layout.addLayout(self.wsl_stats)
        layout.addLayout(action_layout)
        layout.addStretch()
        
        self.setLayout(layout)
        
    def create_stat_card(self, title, value):
        card = QFrame()
        card.setStyleSheet("background-color: #313335; border-radius: 8px; border: 1px solid #444444;")
        v = QVBoxLayout()
        v.setContentsMargins(15, 15, 15, 15)
        
        t = QLabel(title)
        t.setStyleSheet("color: #a9b7c6; font-size: 14px; border: none;")
        
        val = QLabel(str(value))
        val.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold; border: none;")
        
        v.addWidget(t)
        v.addWidget(val)
        card.setLayout(v)
        return card

    def on_scan_finished(self, stats):
        self.lbl_loading.hide()
        
        # Populate Docker Stats
        if stats.get("docker_df"):
            for d in stats["docker_df"]:
                ctype = d.get("Type", "")
                size = d.get("Size", "0B")
                count = d.get("TotalCount", "0")
                if "Images" in ctype:
                    self.docker_stats.addWidget(self.create_stat_card("Images", size))
                elif "Containers" in ctype:
                    self.docker_stats.addWidget(self.create_stat_card(f"Containers ({count})", size))
                elif "Local Volumes" in ctype:
                    self.docker_stats.addWidget(self.create_stat_card("Volumes", size))
                elif "Build Cache" in ctype:
                    self.docker_stats.addWidget(self.create_stat_card("Build Cache", size))
        else:
            lbl = QLabel("Docker is not running or not installed.")
            lbl.setStyleSheet("color: #e53935;")
            self.docker_stats.addWidget(lbl)
            
        # Populate WSL Stats
        if stats.get("wsl"):
            wsl_title = QLabel("WSL Distributions")
            wsl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
            self.wsl_stats.addWidget(wsl_title)
            
            for dist in stats["wsl"]:
                lbl = QLabel(f"• {dist['name']}: {dist['size']}")
                lbl.setStyleSheet("color: #a9b7c6; font-size: 14px;")
                self.wsl_stats.addWidget(lbl)
        
    def compact_disk(self):
        reply = QMessageBox.question(
            self, 'Confirm Compaction',
            "This will shut down all running WSL and Docker containers temporarily.\nAre you sure you want to proceed?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.progress = QProgressDialog("Compacting Docker VHDX... This may take several minutes.", None, 0, 0, self)
            self.progress.setWindowTitle("Please Wait")
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setCancelButton(None)
            self.progress.show()
            
            self.compactor = DockerCompactThread()
            self.compactor.finished.connect(self.on_finished)
            self.compactor.start()
            
    def on_finished(self, success, msg):
        self.progress.close()
        if success:
            QMessageBox.information(self, "Success", msg)
        else:
            QMessageBox.warning(self, "Error", msg)
