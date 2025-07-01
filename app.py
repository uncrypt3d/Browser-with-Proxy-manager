import os
import configparser
import requests
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

CONFIG_FILE = "config.ini"

def validate_proxy(proxy, test_url='https://api.ipify.org?format=json', timeout=6):
    proxies = {'http': proxy, 'https': proxy}
    try:
        response = requests.get(test_url, proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            print(f"[VALID] Proxy {proxy} is working.")
            return True
    except Exception:
        pass
    print(f"[INVALID] Proxy {proxy} is unreachable.")
    return False

class ProxyManager:
    def __init__(self, proxy_file, max_valid_proxies, rotate_per_request=True, test_url='https://api.ipify.org?format=json'):
        self.proxy_file = proxy_file
        self.rotate_per_request = rotate_per_request
        self.test_url = test_url
        self.proxies = self._load_and_clean_proxies(proxy_file, max_valid_proxies)
        self.current_proxy = None
        if not self.proxies:
            raise RuntimeError("No valid proxies loaded.")

    def _load_and_clean_proxies(self, file_path, limit):
        valid = []
        all_proxies = []
        print(f"Loading proxies from '{file_path}' and validating up to {limit} valid proxies...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                all_proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            print(f"[ERROR] Proxy file not found: {file_path}")
            return []

        for proxy in all_proxies:
            if len(valid) >= limit:
                break
            if validate_proxy(proxy, self.test_url):
                valid.append(proxy)

        # Overwrite file with only valid proxies:
        with open(file_path, 'w', encoding='utf-8') as f:
            for p in valid:
                f.write(p + '\n')

        print(f"✅ Loaded and saved {len(valid)} valid proxies.")
        return valid

    def get_next_proxy(self):
        if self.rotate_per_request or not self.current_proxy:
            self.current_proxy = random.choice(self.proxies)
        return self.current_proxy

    def get_requests_proxy_dict(self):
        proxy = self.get_next_proxy()
        return {'http': proxy, 'https': proxy}

    def launch_browser_with_proxy(self):
        proxy = self.get_next_proxy()
        print(f"Launching browser with proxy: {proxy}")

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument(f'--proxy-server={proxy}')
        chrome_options.add_argument('--proxy-bypass-list=<-loopback>')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--disable-blink-features=BlockCredentialedSubresources')

        chrome_options.binary_location = r"C:\Users\!!USER!!\Desktop\chrome-win64\chrome.exe"

        return webdriver.Chrome(options=chrome_options)

def run_http_client(pm):
    url = 'http://httpbin.org/ip'
    for i in range(5):
        proxy = pm.get_requests_proxy_dict()
        print(f"\n[HTTP {i+1}] Using proxy: {pm.current_proxy}")
        try:
            res = requests.get(url, proxies=proxy, timeout=10)
            content_type = res.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                print(f"IP Response: {res.json()}")
            else:
                print(f"[WARNING] Response not JSON. Content-Type: {content_type}")
                print(f"Response text: {res.text[:200]}")
        except Exception as e:
            print(f"[ERROR] Request failed: {e}")
        time.sleep(2)

def run_browser_session(pm):
    driver = None
    try:
        driver = pm.launch_browser_with_proxy()
        driver.get("https://httpbin.org/ip")
        print("✅ Browser launched. You may now browse manually.")
    except Exception as e:
        print(f"[ERROR] Failed to launch browser: {e}")
    finally:
        if driver:
            input("Press Enter to close the browser...")
            driver.quit()

def create_default_config():
    if os.path.exists(CONFIG_FILE):
        return
    config = configparser.ConfigParser()
    config['SETTINGS'] = {
        'proxy_file': 'proxies.txt',
        'max_valid_proxies': '10',
        'rotate_mode': 'request',
        'test_url': 'https://api.ipify.org?format=json',
        'browser_binary_path': r"C:\Users\!!USER!!\Desktop\chrome-win64\chrome.exe",
        'help': (
            "proxy_file = Path to your proxy list file (one proxy per line, format: IP:PORT)\n"
            "max_valid_proxies = How many valid proxies to load and use\n"
            "rotate_mode = 'request' to rotate proxy per HTTP request, 'session' to keep same proxy per session\n"
            "test_url = URL used to test proxies\n"
            "browser_binary_path = Path to your Chrome/Chromium executable\n"
        )
    }
    with open(CONFIG_FILE, 'w') as configfile:
        config.write(configfile)
    print(f"Default config created at '{CONFIG_FILE}'. Edit it to customize settings.")

def main():
    create_default_config()

    config = configparser.ConfigParser()
    config.read(CONFIG_FILE)

    settings = config['SETTINGS']
    proxy_file = settings.get('proxy_file', 'proxies.txt')
    try:
        max_valid = int(settings.get('max_valid_proxies', '10'))
    except ValueError:
        max_valid = 10

    rotate_mode = settings.get('rotate_mode', 'request').lower()
    rotate_per_request = rotate_mode == 'request'

    test_url = settings.get('test_url', 'https://api.ipify.org?format=json')

    browser_path = settings.get('browser_binary_path', None)

    try:
        pm = ProxyManager(proxy_file, max_valid, rotate_per_request=rotate_per_request, test_url=test_url)
    except RuntimeError as err:
        print(f"[FATAL] {err}")
        return

    mode = input("Choose mode: http_client or browser? ").strip().lower()
    if mode == "http_client":
        run_http_client(pm)
    elif mode == "browser":
        try:
            sessions = int(input("How many browser sessions to launch? ").strip())
        except ValueError:
            print("Invalid number.")
            return

        for i in range(sessions):
            print(f"\n[SESSION {i+1}/{sessions}] Starting browser...")
            run_browser_session(pm)
            time.sleep(2)
    else:
        print("Unknown mode selected.")

if __name__ == "__main__":
    main()
