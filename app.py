import os
import configparser
import requests
import random
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from urllib.parse import urlparse
import tempfile
import zipfile

CONFIG_FILE = "config.ini"

def validate_proxy(proxy, test_url='https://api.ipify.org?format=json', timeout=6):
    try:
        parsed = urlparse(proxy)
        scheme = parsed.scheme.lower()
        if parsed.username and parsed.password:
            proxy_url = f"{scheme}://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}"
        else:
            proxy_url = proxy
        proxies = {'http': proxy_url, 'https': proxy_url}
        response = requests.get(test_url, proxies=proxies, timeout=timeout)
        if response.status_code == 200:
            print(f"[VALID] Proxy {proxy} is working.")
            return True
    except Exception:
        pass
    print(f"[INVALID] Proxy {proxy} is unreachable.")
    return False

class ProxyManager:
    def __init__(self, proxy_file, max_valid_proxies, rotate_per_request=True, test_url='https://api.ipify.org?format=json', chrome_path=None):
        self.proxy_file = proxy_file
        self.rotate_per_request = rotate_per_request
        self.test_url = test_url
        self.chrome_path = chrome_path
        self.proxies = self._load_and_clean_proxies(proxy_file, max_valid_proxies)
        self.current_proxy = None
        self.proxy_index = 0
        if not self.proxies:
            raise RuntimeError("No valid or untested proxies loaded.")

    def _load_and_clean_proxies(self, file_path, max_valid):
        proxies_status = {}

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        except FileNotFoundError:
            print(f"[ERROR] Proxy file not found: {file_path}")
            return []

        for proxy in lines:
            proxies_status[proxy] = "untested"

        valid_proxies = []

        print(f"Loading proxies from '{file_path}' and validating untested proxies...")

        for proxy, status in proxies_status.items():
            if status == "untested":
                if validate_proxy(proxy, self.test_url):
                    proxies_status[proxy] = "valid"
                    valid_proxies.append(proxy)
                else:
                    proxies_status[proxy] = "invalid"
            elif status == "valid":
                valid_proxies.append(proxy)

            if len(valid_proxies) >= max_valid:
                break

        proxies_to_keep = [p for p, s in proxies_status.items() if s == "valid" or s == "untested"]

        with open(file_path, 'w', encoding='utf-8') as f:
            for p in proxies_to_keep:
                f.write(p + '\n')

        print(f"✅ After cleanup, saved {len(proxies_to_keep)} proxies (valid + untested).")
        return proxies_to_keep

    def get_next_proxy(self):
        if self.rotate_per_request:
            proxy = self.proxies[self.proxy_index % len(self.proxies)]
            self.proxy_index += 1
            return proxy
        else:
            return self.proxies[0]

    def get_requests_proxy_dict(self):
        proxy = self.get_next_proxy()
        return self.format_proxy_dict(proxy), proxy

    def format_proxy_dict(self, proxy):
        parsed = urlparse(proxy)
        if parsed.username and parsed.password:
            auth_part = f"{parsed.username}:{parsed.password}@"
            host_port = f"{parsed.hostname}:{parsed.port}"
            proxy_auth_url = f"http://{auth_part}{host_port}"
            return {'http': proxy_auth_url, 'https': proxy_auth_url}
        else:
            if parsed.scheme:
                proxy_url = proxy
            else:
                proxy_url = f"http://{proxy}"
            return {'http': proxy_url, 'https': proxy_url}

    def _create_auth_extension(self, proxy_host, proxy_port, username, password):
        """Create a Chrome extension for proxy authentication (HTTP/HTTPS)."""
        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Chrome Proxy",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            }
        }
        """
        background_js = f"""
        var config = {{
            mode: "fixed_servers",
            rules: {{
                singleProxy: {{
                    scheme: "http",
                    host: "{proxy_host}",
                    port: parseInt({proxy_port})
                }},
                bypassList: ["localhost"]
            }}
        }};
        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
        function callbackFn(details) {{
            return {{
                authCredentials: {{
                    username: "{username}",
                    password: "{password}"
                }}
            }};
        }}
        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {{urls: ["<all_urls>"]}},
            ['blocking']
        );
        """

        pluginfile = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        with zipfile.ZipFile(pluginfile.name, 'w') as zp:
            zp.writestr("manifest.json", manifest_json)
            zp.writestr("background.js", background_js)
        return pluginfile.name

    def launch_browser_with_proxy(self, proxy_url=None):
        proxy = proxy_url or self.get_next_proxy()
        print(f"Launching browser with proxy: {proxy}")

        parsed = urlparse(proxy)
        scheme = parsed.scheme.lower() if parsed.scheme else 'http'

        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')
        chrome_options.add_argument('--proxy-bypass-list=<-loopback>')
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--disable-blink-features=BlockCredentialedSubresources')

        if self.chrome_path:
            chrome_options.binary_location = self.chrome_path

        if scheme in ['http', 'https']:
            if parsed.username and parsed.password:
                pluginfile = self._create_auth_extension(parsed.hostname, parsed.port, parsed.username, parsed.password)
                chrome_options.add_extension(pluginfile)
            else:
                chrome_options.add_argument(f'--proxy-server={proxy}')
        elif scheme in ['socks4', 'socks5']:
            chrome_options.add_argument(f'--proxy-server={proxy}')
        else:
            raise ValueError(f"Unsupported proxy scheme: {scheme}")

        return webdriver.Chrome(options=chrome_options)

def run_http_client(pm, logger=print):
    url = 'http://httpbin.org/ip'
    for i in range(5):
        proxy_dict, raw_proxy = pm.get_requests_proxy_dict()
        logger(f"\n[HTTP {i+1}] Using proxy: {raw_proxy}")
        try:
            res = requests.get(url, proxies=proxy_dict, timeout=10)
            content_type = res.headers.get('Content-Type', '')
            if 'application/json' in content_type:
                logger(f"IP Response: {res.json()}")
            else:
                logger(f"[WARNING] Non-JSON response. Content-Type: {content_type}")
                logger(f"Response body: {res.text[:200]}")
        except Exception as e:
            logger(f"[ERROR] Request failed: {e}")
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
        'browser_binary_path': r"C:\Users\!!USER!!\Desktop\chrome-win64\chrome.exe"
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
        pm = ProxyManager(proxy_file, max_valid, rotate_per_request=rotate_per_request, test_url=test_url, chrome_path=browser_path)
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
