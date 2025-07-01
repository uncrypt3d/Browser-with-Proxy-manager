import configparser
import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QFileDialog,
    QLabel, QLineEdit, QCheckBox, QHBoxLayout, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt
from app import ProxyManager, run_browser_session, run_http_client, CONFIG_FILE


class ProxyApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Proxy Manager GUI")
        self.resize(800, 600)

        self.layout = QVBoxLayout()
        self.config = configparser.ConfigParser()
        self.config.read(CONFIG_FILE)
        self.settings = self.config['SETTINGS'] if 'SETTINGS' in self.config else {}

        self.proxy_file = self.settings.get('proxy_file', 'proxies.txt')
        self.max_valid = int(self.settings.get('max_valid_proxies', '10'))
        self.test_url = self.settings.get('test_url', 'https://api.ipify.org?format=json')
        self.rotate_mode = self.settings.get('rotate_mode', 'request').lower()
        self.chrome_path = self.settings.get('browser_binary_path', '')

        self.pm = None

        self.layout.addWidget(QLabel("Proxy File:"))
        file_layout = QHBoxLayout()
        self.proxy_edit = QLineEdit(self.proxy_file)
        file_layout.addWidget(self.proxy_edit)
        browse = QPushButton("Browse")
        browse.clicked.connect(self.browse_file)
        file_layout.addWidget(browse)
        self.layout.addLayout(file_layout)

        self.layout.addWidget(QLabel("Chrome Executable Path:"))
        chrome_layout = QHBoxLayout()
        self.chrome_edit = QLineEdit(self.chrome_path)
        chrome_layout.addWidget(self.chrome_edit)
        chrome_browse = QPushButton("Browse")
        chrome_browse.clicked.connect(self.browse_chrome)
        chrome_layout.addWidget(chrome_browse)
        self.layout.addLayout(chrome_layout)

        self.rotate_checkbox = QCheckBox("Rotate Proxy Per Request")
        self.rotate_checkbox.setChecked(self.rotate_mode == 'request')
        self.layout.addWidget(self.rotate_checkbox)

        self.validate_btn = QPushButton("Validate & Clean Proxies")
        self.validate_btn.clicked.connect(self.validate_proxies)
        self.layout.addWidget(self.validate_btn)

        self.launch_btn = QPushButton("Launch Browser with Proxy")
        self.launch_btn.clicked.connect(self.launch_browser)
        self.layout.addWidget(self.launch_btn)

        self.run_http_btn = QPushButton("Run HTTP Mode (Test URLs)")
        self.run_http_btn.clicked.connect(self.run_http_mode)
        self.layout.addWidget(self.run_http_btn)

        self.proxy_table = QTableWidget()
        self.proxy_table.setColumnCount(2)
        self.proxy_table.setHorizontalHeaderLabels(["Proxy", "Status"])
        self.layout.addWidget(self.proxy_table)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.layout.addWidget(self.output)

        self.setLayout(self.layout)

    def log(self, msg):
        self.output.append(msg)
        self.output.verticalScrollBar().setValue(self.output.verticalScrollBar().maximum())

    def browse_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Proxy File", "", "Text Files (*.txt);;All Files (*)")
        if file_name:
            self.proxy_edit.setText(file_name)

    def browse_chrome(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Select Chrome Executable", "", "Executables (*.exe);;All Files (*)")
        if file_name:
            self.chrome_edit.setText(file_name)
            self.save_config_value('browser_binary_path', file_name)
            self.log(f"[INFO] Chrome path saved: {file_name}")

    def save_config_value(self, key, value):
        if 'SETTINGS' not in self.config:
            self.config['SETTINGS'] = {}
        self.config['SETTINGS'][key] = value
        with open(CONFIG_FILE, 'w') as configfile:
            self.config.write(configfile)

    def load_and_validate_proxies(self, proxy_file, rotate_per_request, chrome_path):
        pm = ProxyManager(
            proxy_file=proxy_file,
            max_valid_proxies=self.max_valid,
            rotate_per_request=rotate_per_request,
            test_url=self.test_url,
            chrome_path=chrome_path
        )
        return pm

    def validate_proxies(self):
        self.proxy_table.setRowCount(0)
        proxy_file = self.proxy_edit.text().strip()
        rotate_mode = 'request' if self.rotate_checkbox.isChecked() else 'session'
        chrome_path = self.chrome_edit.text().strip()

        if not os.path.isfile(proxy_file):
            self.log(f"[ERROR] Proxy file not found: {proxy_file}")
            return

        self.save_config_value('proxy_file', proxy_file)
        self.save_config_value('rotate_mode', rotate_mode)
        self.save_config_value('browser_binary_path', chrome_path)

        self.log(f"[INFO] Validating proxies from: {proxy_file}")
        try:
            self.pm = self.load_and_validate_proxies(
                proxy_file=proxy_file,
                rotate_per_request=(rotate_mode == 'request'),
                chrome_path=chrome_path
            )

            if not self.pm.proxies:
                self.log("[ERROR] No valid proxies found after validation.")
                return

            self.log(f"[SUCCESS] Valid proxies: {len(self.pm.proxies)}")
            self.populate_proxy_table(self.pm.proxies)
        except Exception as e:
            self.log(f"[ERROR] {str(e)}")

    def populate_proxy_table(self, proxies):
        self.proxy_table.setRowCount(len(proxies))
        for row, proxy in enumerate(proxies):
            self.proxy_table.setItem(row, 0, QTableWidgetItem(proxy))
            self.proxy_table.setItem(row, 1, QTableWidgetItem("VALID"))

    def launch_browser(self):
        if not self.pm or not getattr(self.pm, 'proxies', None):
            self.log("[ERROR] Validate proxies first.")
            return
        try:
            current_proxy = self.pm.get_next_proxy()
            self.log(f"[INFO] Launching browser with proxy: {current_proxy}")
            driver = self.pm.launch_browser_with_proxy(proxy_url=current_proxy)
            driver.get("https://httpbin.org/ip")
            self.log(f"[INFO] Browser launched successfully")
        except Exception as e:
            self.log(f"[ERROR] Failed to launch browser: {e}")

    def run_http_mode(self):
        proxy_file = self.proxy_edit.text().strip()
        chrome_path = self.chrome_edit.text().strip()
        rotate_mode = 'request' if self.rotate_checkbox.isChecked() else 'session'

        self.save_config_value('proxy_file', proxy_file)
        self.save_config_value('rotate_mode', rotate_mode)
        self.save_config_value('browser_binary_path', chrome_path)

        try:
            self.pm = self.load_and_validate_proxies(
                proxy_file=proxy_file,
                rotate_per_request=(rotate_mode == 'request'),
                chrome_path=chrome_path
            )
            run_http_client(self.pm, logger=self.log)
        except RuntimeError as e:
            self.log(f"[ERROR] {e}")
        except Exception as e:
            self.log(f"[ERROR] Unexpected error: {e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ProxyApp()
    window.show()
    sys.exit(app.exec())
