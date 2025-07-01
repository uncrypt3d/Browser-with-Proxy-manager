import configparser
import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit,
    QVBoxLayout, QFileDialog, QLabel, QLineEdit
)
from app import ProxyManager

class ProxyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxy Manager GUI")
        self.resize(600, 400)

        self.layout = QVBoxLayout()

        self.label = QLabel("Proxy file path:")
        self.layout.addWidget(self.label)

        self.path_edit = QLineEdit()
        self.layout.addWidget(self.path_edit)

        self.browse_btn = QPushButton("Browse File")
        self.browse_btn.clicked.connect(self.browse_file)
        self.layout.addWidget(self.browse_btn)

        self.validate_btn = QPushButton("Validate Proxies")
        self.validate_btn.clicked.connect(self.validate_proxies)
        self.layout.addWidget(self.validate_btn)

        self.launch_btn = QPushButton("Launch Browser")
        self.launch_btn.clicked.connect(self.launch_browser)
        self.layout.addWidget(self.launch_btn)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output)

        self.setLayout(self.layout)
        self.pm = None

        # Load config
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.settings = self.config['SETTINGS'] if 'SETTINGS' in self.config else {}
        self.actions = self.config['ACTIONS'] if 'ACTIONS' in self.config else {}

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Proxy File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.path_edit.setText(file_name)

    def validate_proxies(self):
        proxy_file = self.path_edit.text() or self.settings.get('proxy_file', 'proxies.txt')
        max_valid = int(self.settings.get('max_valid_proxies', '4'))

        # Default to True if not set, convert to bool
        rotate_per_request_str = self.actions.get('rotate_per_request', 'true').lower()
        rotate_per_request = rotate_per_request_str in ('true', '1', 'yes', 'on')

        if not proxy_file:
            self.output.append("[ERROR] Please select a proxy file.")
            return
        try:
            self.pm = ProxyManager(proxy_file, max_valid_proxies=max_valid, rotate_per_request=rotate_per_request)
            self.output.append(f"Loaded {len(self.pm.proxies)} valid proxies:")
            for p in self.pm.proxies:
                self.output.append(f" - {p}")
        except Exception as e:
            self.output.append(f"[ERROR] {e}")

    def launch_browser(self):
        if not self.pm:
            self.output.append("[ERROR] Validate proxies first before launching browser.")
            return
        try:
            driver = self.pm.launch_browser_with_proxy()
            self.output.append(f"[INFO] Browser launched with proxy: {self.pm.current_proxy}")
        except Exception as e:
            self.output.append(f"[ERROR] Failed to launch browser: {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProxyApp()
    window.show()
    sys.exit(app.exec())
