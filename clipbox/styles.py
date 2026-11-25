"""Tema escuro compacto para as janelas do Clipbox."""

APP_QSS = """
QWidget {
    background-color: #111318;
    color: #e8eaed;
    font-family: "Segoe UI", "Inter", sans-serif;
    font-size: 13px;
}
QLabel#title {
    font-size: 18px;
    font-weight: 600;
    color: #f4f6f8;
}
QLabel#hint, QLabel#meta {
    color: #9aa0a6;
    font-size: 12px;
}
QPlainTextEdit {
    background-color: #1a1d24;
    border: 1px solid #2c313c;
    border-radius: 10px;
    padding: 10px;
    selection-background-color: #3d5afe;
}
QComboBox, QLineEdit {
    background-color: #1a1d24;
    border: 1px solid #2c313c;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 28px;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QPushButton {
    background-color: #2a3140;
    border: 1px solid #3a4254;
    border-radius: 8px;
    padding: 8px 14px;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #343c4e;
}
QPushButton:pressed {
    background-color: #232936;
}
QPushButton#primary {
    background-color: #3d5afe;
    border: 1px solid #536dfe;
    color: #ffffff;
}
QPushButton#primary:hover {
    background-color: #536dfe;
}
QPushButton:disabled {
    color: #6b7280;
    background-color: #1c2028;
}
QFrame#card {
    background-color: #161920;
    border: 1px solid #2c313c;
    border-radius: 14px;
}
QStatusBar {
    background-color: #0e1014;
    color: #9aa0a6;
}
"""
