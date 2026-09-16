"""
Python WaferSlim Reusable UI Automation Fixture.
Mirrors the step-by-step design of API request fixtures for UI browser testing using Playwright.
Incorporates Page Object Model (POM), centralized configurations, failure-only screenshots, dynamic UI overrides, HTML URL link sanitization, and native Playwright locator objects with LoginPage.
Natively automates inline failure screenshots inside failed cells.
"""
import os
import re
from playwright.sync_api import sync_playwright
from core.config import Config
from core.logger import logger
from core.pages.login_page import LoginPage


def clean_html_url(value: str) -> str:
    """
    Strips away FitNesse's auto-generated HTML anchor tags (<a href="...">...</a>)
    and returns only the raw target URL.
    """
    val_str = str(value).strip()
    
    # Try to extract the raw URL from the href attribute
    match = re.search(r'href=["\']([^"\']+)["\']', val_str)
    if match:
        return match.group(1).strip()
        
    # Fallback: strip any HTML tags
    cleaned = re.sub(r'<[^<]+?>', '', val_str).strip()
    return cleaned


class UiFixture:
    """
    Generic, step-by-step browser automation fixture for FitNesse.
    """

    def __init__(self) -> None:
        self._workspace_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        self._fitnesse_root = os.path.join(self._workspace_dir, "FitNesseRoot")
        self._screenshot_dir_path = "files/testResults/ui-automation"
        
        # Centralized configurations load (used as defaults)
        self._default_url = Config.UI_BASE_URL
        self._default_browser = Config.UI_BROWSER
        self._default_headless = Config.UI_HEADLESS
        
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        self._screenshot_counter = 0
        self._last_error_html = ""

    # UI-Level Configuration Setters (Allows managing config directly from FitNesse UI!)
    def set_url(self, value: str) -> None:
        """Dynamically overrides the target URL from the FitNesse UI (with HTML cleanup)."""
        self._default_url = clean_html_url(value)
        logger.info(f"[UiFixture] Target URL set from UI: {self._default_url}")

    def setUrl(self, value: str) -> None:
        self.set_url(value)

    def set_browser(self, value: str) -> None:
        """Dynamically overrides the browser engine (chromium, firefox, webkit) from the FitNesse UI."""
        self._default_browser = str(value).strip().lower()
        logger.info(f"[UiFixture] Browser engine set from UI: {self._default_browser}")

    def setBrowser(self, value: str) -> None:
        self.set_browser(value)

    def set_headless(self, value: str) -> None:
        """Dynamically overrides the headless mode (true/false) from the FitNesse UI."""
        val_str = str(value).lower().strip()
        self._default_headless = val_str in ("true", "yes", "1", "t")
        logger.info(f"[UiFixture] Headless mode set from UI: {self._default_headless}")

    def setHeadless(self, value: str) -> None:
        self.set_headless(value)

    # Browser Management
    def start_browser(self, *args) -> bool:
        """Starts a native Playwright browser instance based on config or UI overrides."""
        try:
            self.close_browser()  # Clean up any existing instances first
            
            browser_type = args[0] if args else ""
            b_type = str(browser_type or self._default_browser).lower()
            headless_mode = self._default_headless
            
            # Check for temporary Live Debug override from the browser UI
            debug_file = os.path.join(self._workspace_dir, "runtime", "live-debug.txt")
            if os.path.exists(debug_file):
                try:
                    with open(debug_file, "r", encoding="utf-8") as f:
                        if f.read().strip() == "true":
                            headless_mode = False
                            logger.info("[UiFixture] Live Debug Active! Forcing headed browser execution.")
                    os.remove(debug_file)  # Delete so future runs use the default env setting
                except Exception:
                    pass
            
            logger.info(f"[UiFixture] Starting Playwright engine (browser: {b_type}, headless: {headless_mode})")
            self._playwright = sync_playwright().start()
            
            if "firefox" in b_type:
                self._browser = self._playwright.firefox.launch(headless=headless_mode)
                self._context = self._browser.new_context(viewport={"width": 1920, "height": 1080})
            elif "webkit" in b_type or "safari" in b_type:
                self._browser = self._playwright.webkit.launch(headless=headless_mode)
                self._context = self._browser.new_context(viewport={"width": 1920, "height": 1080})
            else:
                # Chromium supports true OS-level window maximization!
                if not headless_mode:
                    self._browser = self._playwright.chromium.launch(headless=headless_mode, args=["--start-maximized"])
                    self._context = self._browser.new_context(no_viewport=True)
                else:
                    self._browser = self._playwright.chromium.launch(headless=headless_mode)
                    self._context = self._browser.new_context(viewport={"width": 1920, "height": 1080})
                
            self._page = self._context.new_page()
            logger.info("[UiFixture] Browser started successfully.")
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to start browser: {e}")
            self.close_browser()
            return False

    def startBrowser(self, *args) -> bool:
        return self.start_browser(*args)

    def close_browser(self) -> None:
        """Closes the browser instance and stops Playwright."""
        try:
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.warning(f"[UiFixture] Ignored error during browser cleanup: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None
            logger.info("[UiFixture] Browser stopped and resources freed.")

    def closeBrowser(self) -> None:
        self.close_browser()

    # Navigation
    def navigate_to(self, *args) -> bool:
        """Navigates the browser to the specified URL or UI-configured default."""
        if not self._page:
            if not self.start_browser():
                return False
                
        # Support both parameterless calls and passing a direct URL with HTML cleanup
        raw_url = str(args[0]).strip() if args and str(args[0]).strip() else ""
        target_url = clean_html_url(raw_url) if raw_url else self._default_url
        
        logger.info(f"[UiFixture] Navigating to URL: '{target_url}'")
        try:
            self._page.goto(target_url, timeout=20000, wait_until="commit")
            self._last_error_html = ""
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Navigation failed: {e}")
            self._capture_failure_state("navigation_failed")
            # Return inline error link directly inside the cell!
            return self._last_error_html

    def navigateTo(self, *args) -> bool:
        return self.navigate_to(*args)

    # Actions using Page Object Model (POM) LoginPage
    def fill_field(self, element_name: str, value: str) -> bool:
        """Fills an input field matching the POM locator with the specified value."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot perform fill.")
            return "No active page opened"
            
        logger.info(f"[UiFixture] Filling element '{element_name}' with value: {value}")
        
        try:
            # Correctly retrieve the compiled Playwright Locator directly from the LoginPage Page Object
            locator = LoginPage.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.fill(value)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to fill field '{element_name}': {e}")
            self._capture_failure_state(f"fill_failed_{element_name}")
            return self._last_error_html

    def fillField(self, element_name: str, value: str) -> bool:
        return self.fill_field(element_name, value)

    def fill_field_with_value(self, element_name: str, value: str) -> bool:
        """Fills an input field - maps to FitNesse: | fill field | name | with value | val |"""
        return self.fill_field(element_name, value)

    def fillFieldWithValue(self, element_name: str, value: str) -> bool:
        return self.fill_field_with_value(element_name, value)

    def click_button(self, element_name: str) -> bool:
        """Clicks an element matching the POM locator."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot perform click.")
            return "No active page opened"
            
        logger.info(f"[UiFixture] Clicking element '{element_name}'")
        
        try:
            locator = LoginPage.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.click()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to click selector '{element_name}': {e}")
            self._capture_failure_state(f"click_failed_{element_name}")
            return self._last_error_html

    def clickButton(self, element_name: str) -> bool:
        return self.click_button(element_name)

    # Browser Waiting Utilities
    def wait_for_text_timeout(self, text: str, timeout: str) -> bool:
        """Waits for the specified text to appear on the page with a timeout in milliseconds."""
        if not self._page:
            logger.error("[UiFixture] No active page context to wait for text.")
            return False
            
        try:
            t_ms = int(str(timeout).strip())
            logger.info(f"[UiFixture] Waiting for text '{text}' to appear (timeout: {t_ms}ms)...")
            self._page.wait_for_selector(f"text={text}", state="visible", timeout=t_ms)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Timeout waiting for text '{text}': {e}")
            self._capture_failure_state(f"wait_for_text_failed_{text}")
            return self._last_error_html

    def waitForTextTimeout(self, text: str, timeout: str) -> bool:
        return self.wait_for_text_timeout(text, timeout)

    # Value Extraction Utilities
    def get_text(self, element_name: str) -> str:
        """Retrieves the text content of an element matching the POM locator."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot get text.")
            return "No active page opened"
            
        logger.info(f"[UiFixture] Retrieving text from element: '{element_name}'")
        try:
            locator = LoginPage.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            text_content = locator.text_content()
            return text_content.strip() if text_content is not None else ""
        except Exception as e:
            logger.error(f"[UiFixture] Failed to retrieve text for '{element_name}': {e}")
            self._capture_failure_state(f"get_text_failed_{element_name}")
            return self._last_error_html

    def getText(self, element_name: str) -> str:
        return self.get_text(element_name)

    # Assertions / Verifications
    def verify_text_present(self, text: str) -> bool:
        """Returns True if the specified text is present on the page."""
        if not self._page:
            return False
        try:
            is_visible = self._page.is_visible(f"text={text}", timeout=3000)
            return is_visible
        except Exception:
            return False

    def verifyTextPresent(self, text: str) -> bool:
        return self.verify_text_present(text)

    def verify_element_present(self, element_name: str) -> bool:
        """Returns True if an element matching the POM locator is present on the page."""
        if not self._page:
            return False
        try:
            locator = LoginPage.get_locator(self._page, element_name)
            return locator.count() > 0
        except Exception:
            return False

    def verifyElementPresent(self, element_name: str) -> bool:
        return self.verify_element_present(element_name)

    # Screenshots & Error Reports (Attaches failure screenshots dynamically)
    def error_report(self) -> str:
        """Returns the HTML link for any failure screenshots captured during the run."""
        return self._last_error_html or "No failures occurred"

    def errorReport(self) -> str:
        return self.error_report()

    # Dynamic Method Dispatcher (Supports custom user-defined table formatting)
    def __getattr__(self, name: str):
        """
        Dynamically intercepts and maps custom Slim method structures.
        Supports: fillField<Value>('element') -> fill_field('element', 'Value')
        """
        # Handle CamelCase fillField<Value>
        if name.startswith("fillField") and len(name) > 9:
            value_to_fill = name[9:]
            def dynamic_fill(element_name: str) -> bool:
                return self.fill_field(element_name, value_to_fill)
            return dynamic_fill

        # Handle snake_case fill_field_<value>
        if name.startswith("fill_field_") and len(name) > 11:
            value_to_fill = name[11:]
            def dynamic_fill_snake(element_name: str) -> bool:
                return self.fill_field(element_name, value_to_fill)
            return dynamic_fill_snake

        raise AttributeError(f"'UiFixture' object has no attribute '{name}'")

    # Private Helpers
    def _capture_failure_state(self, reason_prefix: str) -> None:
        """Captures a screenshot automatically only on failure states."""
        if not self._page:
            return
            
        self._screenshot_counter += 1
        screenshot_name = f"failure-{reason_prefix}-{self._screenshot_counter}.png"
        
        full_dir = os.path.join(self._fitnesse_root, self._screenshot_dir_path)
        os.makedirs(full_dir, exist_ok=True)
        screenshot_path = os.path.join(full_dir, screenshot_name)
        
        try:
            self._page.screenshot(path=screenshot_path)
            url = f"http://localhost:8080/{self._screenshot_dir_path}/{screenshot_name}"
            self._last_error_html = f'<a href="{url}" target="_blank" style="color: #ef4444; font-weight: bold;">[VIEW FAILURE SCREENSHOT]</a>'
            logger.info(f"[UiFixture] Failure screenshot saved successfully: {screenshot_path}")
        except Exception as e:
            logger.error(f"[UiFixture] Capturing failure screenshot failed: {e}")
