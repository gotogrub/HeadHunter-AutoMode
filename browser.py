"""
HeadHunter Destroyer - Browser Management
Cross-platform support: Windows & Linux
"""

import os
import sys
import json
import shutil
import platform
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from config import HEADLESS, SLOW_MO, USER_DATA_DIR, TIMEOUTS, BROWSER


def get_platform():
    """Detect current platform."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    elif system == "linux":
        return "linux"
    elif system == "darwin":
        return "macos"
    return "unknown"


class BrowserManager:
    """Manages browser instance with persistent session support."""

    def __init__(self, browser: str = None):
        """
        Initialize browser manager.

        Args:
            browser: Browser to use ("chrome", "edge", "firefox", "auto")
                     If None, uses BROWSER from config
        """
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self.page: Page = None
        self.platform = get_platform()
        self.browser_type = browser or BROWSER
        self.cookies_file = os.path.join(USER_DATA_DIR, "hh_cookies.json")

    def start(self, use_existing_session: bool = True) -> Page:
        """
        Start browser with optional persistent session.

        Args:
            use_existing_session: If True, tries to use saved cookies
        """
        self.playwright = sync_playwright().start()

        # Ensure user data directory exists
        os.makedirs(USER_DATA_DIR, exist_ok=True)

        # Use separate profile directory
        profile_dir = os.path.join(USER_DATA_DIR, "hh_profile")

        # Common browser args for anti-detection
        browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--no-first-run",
            "--no-default-browser-check",
        ]

        # Linux-specific args (for headless environments like Kali)
        if self.platform == "linux":
            browser_args.extend([
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ])

        context_options = {
            "user_data_dir": profile_dir,
            "headless": HEADLESS,
            "slow_mo": SLOW_MO,
            "viewport": {"width": 1366, "height": 768},
            "locale": "ru-RU",
            "timezone_id": "Europe/Moscow",
            "args": browser_args,
            "ignore_default_args": ["--enable-automation"],
        }

        # Start selected browser
        self.context = self._start_browser(context_options)

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

        # Set default timeout
        self.page.set_default_timeout(TIMEOUTS["page_load"])

        # Load saved cookies if available
        if use_existing_session:
            self._load_cookies()

        return self.page

    def _start_browser(self, options: dict) -> BrowserContext:
        """
        Start browser based on selection.

        Supported browsers:
            - chrome: Google Chrome
            - edge: Microsoft Edge (Windows only)
            - firefox: Mozilla Firefox
            - auto: Chrome first, then Edge (Windows), then Firefox
        """
        browser = self.browser_type.lower()

        # Firefox needs different options
        firefox_options = {k: v for k, v in options.items()
                          if k not in ("args", "ignore_default_args")}

        if browser == "chrome":
            return self._try_chrome(options)

        elif browser == "edge":
            return self._try_edge(options)

        elif browser == "firefox":
            return self._try_firefox(firefox_options)

        else:  # auto
            return self._try_auto(options, firefox_options)

    def _try_chrome(self, options: dict) -> BrowserContext:
        """Try to start Google Chrome."""
        print("[*] Starting Google Chrome...")
        try:
            return self.playwright.chromium.launch_persistent_context(
                channel="chrome",
                **options
            )
        except Exception as e:
            print(f"[!] Chrome failed: {e}")
            print("[*] Trying Chromium...")
            return self.playwright.chromium.launch_persistent_context(**options)

    def _try_edge(self, options: dict) -> BrowserContext:
        """Try to start Microsoft Edge."""
        print("[*] Starting Microsoft Edge...")
        try:
            return self.playwright.chromium.launch_persistent_context(
                channel="msedge",
                **options
            )
        except Exception as e:
            print(f"[!] Edge failed: {e}")
            raise RuntimeError("Edge is not available. Try using chrome or firefox.")

    def _try_firefox(self, options: dict) -> BrowserContext:
        """Try to start Mozilla Firefox."""
        print("[*] Starting Mozilla Firefox...")
        return self.playwright.firefox.launch_persistent_context(**options)

    def _try_auto(self, options: dict, firefox_options: dict) -> BrowserContext:
        """Auto-detect best available browser."""
        # Try Chrome first
        try:
            print("[*] Starting Google Chrome...")
            return self.playwright.chromium.launch_persistent_context(
                channel="chrome",
                **options
            )
        except Exception as e:
            print(f"[!] Chrome not found: {e}")

        # Try Edge on Windows
        if self.platform == "windows":
            try:
                print("[*] Trying Microsoft Edge...")
                return self.playwright.chromium.launch_persistent_context(
                    channel="msedge",
                    **options
                )
            except Exception as e:
                print(f"[!] Edge failed: {e}")

        # Try plain Chromium
        try:
            print("[*] Trying Chromium...")
            return self.playwright.chromium.launch_persistent_context(**options)
        except Exception as e:
            print(f"[!] Chromium failed: {e}")

        # Last resort: Firefox
        print("[*] Trying Firefox...")
        return self.playwright.firefox.launch_persistent_context(**firefox_options)

    def _load_cookies(self):
        """Load cookies from file if exists."""
        if os.path.exists(self.cookies_file):
            try:
                with open(self.cookies_file, "r", encoding="utf-8") as f:
                    cookies = json.load(f)
                    if cookies:
                        self.context.add_cookies(cookies)
                        print("[*] Loaded saved cookies")
            except Exception as e:
                print(f"[!] Failed to load cookies: {e}")

    def save_cookies(self):
        """Save current cookies to file."""
        try:
            cookies = self.context.cookies()
            with open(self.cookies_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)
            print("[*] Cookies saved")
        except Exception as e:
            print(f"[!] Failed to save cookies: {e}")

    def stop(self):
        """Close browser and cleanup."""
        # Save cookies before closing
        if self.context:
            try:
                self.save_cookies()
            except Exception:
                pass
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def is_logged_in(self) -> bool:
        """Check if user is logged in to HH.ru."""
        try:
            self.page.goto("https://hh.ru/applicant/resumes", wait_until="domcontentloaded")

            # Wait a bit for redirects
            self.page.wait_for_timeout(2000)

            current_url = self.page.url.lower()

            # Check if we're on login page
            if "login" in current_url or "account/login" in current_url:
                return False

            # Check for user menu element (only visible when logged in)
            try:
                self.page.wait_for_selector('[data-qa="mainmenu_profileAndResumes"]', timeout=5000)
                return True
            except Exception:
                pass

            # Alternative check - resume page content
            if "/applicant/resumes" in current_url:
                content = self.page.content()
                return "resume" in content.lower() and "войти" not in content.lower()

            return False

        except Exception as e:
            print(f"[!] Error checking login: {e}")
            return False

    def wait_for_login(self):
        """Navigate to login page and wait for user to login."""
        print("\n[!] Opening HH.ru login page...")
        self.page.goto("https://hh.ru/account/login", wait_until="domcontentloaded")

        print("[!] Please login to HH.ru in the browser window...")
        print("[!] After logging in, press Enter here to continue...")
        input()

        # Save cookies after login
        self.save_cookies()

        if not self.is_logged_in():
            print("[!] Still not logged in. Please try again.")
            self.wait_for_login()
        else:
            print("[+] Successfully logged in!")

    def clear_session(self):
        """Clear saved session data."""
        if os.path.exists(self.cookies_file):
            os.remove(self.cookies_file)
            print("[*] Session cleared")

        profile_dir = os.path.join(USER_DATA_DIR, "hh_profile")
        if os.path.exists(profile_dir):
            try:
                shutil.rmtree(profile_dir)
                print("[*] Profile data cleared")
            except Exception as e:
                print(f"[!] Failed to clear profile: {e}")
