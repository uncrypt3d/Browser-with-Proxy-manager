# Proxy Manager (Terminal / GUI) 🚀

Proxy Manager with GUI for validating proxies, rotating them per HTTP request or browser session, and launching proxied Chrome browsers — all stable and user-friendly!

---

## Overview

Proxy Manager GUI is a desktop app built with PyQt6 and Selenium that helps you:

- Load and validate your proxy list with automatic cleaning  
- Rotate proxies per HTTP request or per browser session  
- Launch Chrome browsers routed through proxies  
- Test proxies via HTTP requests  
- Configure settings via an editable `config.ini`  
- Use your own Chrome binary or bundled portable Chrome  
- Keep GUI responsive with multi-threaded operations  

Ideal for developers, testers, or anyone needing rotating proxy automation without fuss.

---

## Features

- Proxy validation with real HTTP checks  
- Per-request or per-session proxy rotation  
- Chrome browser launching with proxies via Selenium  
- Simple PyQt6 GUI with browse, validate, and launch buttons  
- Configurable via `config.ini` for proxy file, Chrome path, and more  
- Background threads keep the UI smooth  
- Cross-platform ready (adjust Chrome binary path accordingly)  

---

## Installation

### Requirements

- Python 3.9+  
- Google Chrome / Chromium (or portable Chrome)  
- ChromeDriver matching your Chrome version ([Download here](https://chromedriver.chromium.org/downloads))  
- Python packages: `pyqt6`, `selenium`, `requests`  

Install required packages via:

```bash
pip install pyqt6 selenium requests
```

### Setup

1. Clone or download this repository  
2. Prepare your proxy list file (`proxies.txt`) with one proxy per line in `IP:PORT` format  
3. Edit `config.ini` or use the GUI to set your proxy file and options  
4. Ensure Chrome binary exists at the configured path or in `chrome-win64/chrome.exe`  

---

## Usage

Run the app with:

WITHOUT GUI "TERMINAL MODE":
```bash
python app.py
```

WITH GUI VIA TERMINAL:
```bash
python gui.py
```

WITHOUT PYTHON use exe from releases or build it yourself.

How to use:

1. **Browse Proxy File:** Select your proxy list file  
2. **Validate and Load Proxies:** Test and load valid proxies  
3. **Launch Browser with Proxy:** Open Chrome routed through a random proxy  
4. Browse manually (e.g., check your IP on [https://httpbin.org/ip](https://httpbin.org/ip))  
5. Close the browser to return to the GUI  

---

## Configuration (`config.ini`)

```ini
[SETTINGS]
proxy_file = proxies.txt
max_valid_proxies = 10
rotate_mode = request  ; options: 'request' or 'session'
test_url = https://api.ipify.org?format=json
browser_binary_path = C:\Path\To\Chrome\chrome.exe  ; optional, specify your Chrome binary path
```

---

## Developer Notes

- Proxy validation via `requests` through proxies  
- Browser sessions via Selenium WebDriver with proxy ChromeOptions  
- Multi-threading to avoid GUI blocking  
- ChromeDriver version must match your installed Chrome version  
- For packaging with PyInstaller, use:

```bash
pyinstaller --onefile --windowed --add-data "chrome-win64;chrome-win64" gui.py
```

---

## Troubleshooting

- **Browser won’t launch?** Check ChromeDriver version matches your Chrome  
- **Proxy file issues?** Verify file path and proxy formatting (`IP:PORT`)  
- **Proxy validation fails?** Some proxies may be dead or slow; increase timeout if needed  
- **GUI freezes?** Ensure you use the latest code with threading for background tasks  
- **Too many logs?** ChromeOptions includes `--log-level=3` to suppress verbose logs  

---

## Contributing

Contributions, bug reports, and feature requests are welcome!  
Please open issues or pull requests with clean, documented code.

---

## License

MIT License © 2025 uncrypt3d

---

## Acknowledgments

- PyQt6 for the GUI  
- Selenium for browser automation  
- Requests for HTTP proxy testing  
- Chrome & ChromeDriver teams for web automation tools  

---

## Contact

For questions or support, contact via GitHub 'issues / discussions'.

---

Enjoy your hassle-free proxy management! 🎉
