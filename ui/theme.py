DARK_THEME_QSS = """
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: "Segoe UI", sans-serif;
    font-size: 10pt;
}

QPushButton {
    background-color: #0d47a1;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
}

QPushButton:hover {
    background-color: #1565c0;
}

QPushButton:pressed {
    background-color: #0a3575;
}

QPushButton:disabled {
    background-color: #424242;
    color: #757575;
}

/* Progress Bars */
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #2b2b2b;
    text-align: center;
    color: #ffffff;
}

QProgressBar::chunk {
    background-color: #4a88c7;
    border-radius: 4px;
}

QProgressBar#docker_bar::chunk { background-color: #9e7bb5; }
QProgressBar#node_bar::chunk { background-color: #5c9e60; }
QProgressBar#python_bar::chunk { background-color: #4a88c7; }
QProgressBar#rust_bar::chunk { background-color: #c76f4a; }
QProgressBar#total_bar::chunk { background-color: #c74a4a; }

QListWidget {
    background-color: #2b2b2b;
    border: 1px solid #323232;
    outline: none;
}

QListWidget::item {
    border-bottom: 1px solid #323232;
}

QListWidget::item:hover {
    background-color: #323232;
}

QListWidget::item:selected {
    background-color: #2f65ca;
    color: #ffffff;
}

QTreeWidget {
    background-color: #2b2b2b;
    border: 1px solid #323232;
    outline: none;
    color: #a9b7c6;
}

QTreeWidget::item {
    border-bottom: 1px solid #323232;
    padding: 4px;
}

QTreeWidget::item:hover {
    background-color: #323232;
}

QTreeWidget::item:selected {
    background-color: #2f65ca;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #313335;
    color: #a9b7c6;
    padding: 6px;
    border: 1px solid #242527;
    font-weight: bold;
}

QProgressBar {
    border: 1px solid #323232;
    border-radius: 4px;
    text-align: center;
    background-color: #3c3f41;
    color: #ffffff;
}

QProgressBar::chunk {
    background-color: #4a88c7;
    border-radius: 3px;
}
"""
