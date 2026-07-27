from PySide6.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, 
                               QWidget, QStackedWidget, QListWidget, QListWidgetItem, QLabel)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from core.system_info import resource_path
from ui.theme import DARK_THEME_QSS
from ui.dashboard_tab import DashboardTab
from ui.repo_tab import RepoTab
from ui.global_caches_tab import GlobalCachesTab
from ui.containers_tab import ContainersTab
from ui.windows_storage_tab import WindowsStorageTab
from ui.history_tab import HistoryTab
from core.system_info import is_mac

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DevSpace")
        self.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
        self.resize(1100, 750)
        self.setStyleSheet(DARK_THEME_QSS)
        
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar Navigation
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(240)
        self.sidebar.setObjectName("Sidebar")
        self.sidebar.setFocusPolicy(Qt.NoFocus)
        
        self.page_mapping = {} # maps row_index to stack_index
        
        # 0
        self._add_sidebar_item("📊 Dashboard", 0)
        
        # 1
        self._add_sidebar_header("DEVELOPMENT")
        self._add_sidebar_item(" 🟦 Workspaces", 1) # 2
        self._add_sidebar_item(" 🟧 Development Caches", 2) # 3
        
        if not is_mac():
            self._add_sidebar_item(" 🟪 Containers & WSL", 3) # 4
        
        # 5
        self._add_sidebar_header("SYSTEM")
        
        if not is_mac():
            self._add_sidebar_item(" 🪟 Windows Storage", 4) # 6
            
        self._add_sidebar_item(" 📖 Cleanup History", 5) # 7
        
        self.sidebar.currentRowChanged.connect(self.change_page)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        self.dashboard_tab = DashboardTab()
        self.dashboard_tab.request_navigate.connect(self.navigate_to_stack)
        self.repo_tab = RepoTab()
        self.global_caches_tab = GlobalCachesTab()
        self.containers_tab = ContainersTab()
        self.windows_storage_tab = WindowsStorageTab()
        self.history_tab = HistoryTab()
        
        self.content_stack.addWidget(self.dashboard_tab) # 0
        self.content_stack.addWidget(self.repo_tab) # 1
        self.content_stack.addWidget(self.global_caches_tab) # 2
        self.content_stack.addWidget(self.containers_tab) # 3
        self.content_stack.addWidget(self.windows_storage_tab) # 4
        self.content_stack.addWidget(self.history_tab) # 5
        
        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.content_stack)
        
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.sidebar.setCurrentRow(0)

    def _add_sidebar_item(self, text, stack_index):
        item = QListWidgetItem(text)
        item.setSizeHint(QSize(220, 50))
        self.sidebar.addItem(item)
        self.page_mapping[self.sidebar.count() - 1] = stack_index

    def _add_sidebar_header(self, text):
        item = QListWidgetItem(text)
        item.setSizeHint(QSize(220, 30))
        item.setFlags(Qt.NoItemFlags) # Unselectable
        item.setTextAlignment(Qt.AlignBottom)
        # We can adjust style for header in theme.py or here
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setForeground(Qt.gray)
        self.sidebar.addItem(item)
        
    def navigate_to_stack(self, stack_index):
        for row, idx in self.page_mapping.items():
            if idx == stack_index:
                self.sidebar.setCurrentRow(row)
                break

    def change_page(self, current_row):
        stack_idx = self.page_mapping.get(current_row)
        if stack_idx is not None:
            self.content_stack.setCurrentIndex(stack_idx)
            if stack_idx == 5:
                self.history_tab.load_data()
