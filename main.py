import sys
import ctypes
from PySide6.QtWidgets import QApplication, QMessageBox

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    app = QApplication(sys.argv)
    
    from ui.main_window import MainWindow
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
