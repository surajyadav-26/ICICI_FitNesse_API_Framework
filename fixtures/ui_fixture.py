"""
Python WaferSlim Reusable UI Automation Fixture.
Mirrors the step-by-step design of API request fixtures for UI browser testing using Playwright.
Incorporates Page Object Model (POM), centralized configurations, failure-only screenshots, dynamic UI overrides, HTML URL link sanitization, and native Playwright locator objects with PageRegistry.
"""
import os
import re
from playwright.sync_api import sync_playwright
from core.config import Config
from core.logger import logger
from core.pages.page_registry import PageRegistry


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
            
            logger.info(f"[UiFixture] Starting Playwright engine (browser: {b_type}, headless: {headless_mode})")
            self._playwright = sync_playwright().start()
            
            if "firefox" in b_type:
                self._browser = self._playwright.firefox.launch(headless=headless_mode)
            elif "webkit" in b_type or "safari" in b_type:
                self._browser = self._playwright.webkit.launch(headless=headless_mode)
            else:
                self._browser = self._playwright.chromium.launch(headless=headless_mode)
                
            self._context = self._browser.new_context(viewport={"width": 1280, "height": 800})
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
            self._capture_failure_state(f"navigation_failed")
            return False

    def navigateTo(self, *args) -> bool:
        return self.navigate_to(*args)

    def go_back(self) -> bool:
        if not self._page:
            return False
        try:
            self._page.go_back(timeout=20000, wait_until="commit")
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Go back failed: {e}")
            self._capture_failure_state("go_back_failed")
            return False

    def goBack(self) -> bool:
        return self.go_back()

    def go_forward(self) -> bool:
        if not self._page:
            return False
        try:
            self._page.go_forward(timeout=20000, wait_until="commit")
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Go forward failed: {e}")
            self._capture_failure_state("go_forward_failed")
            return False

    def goForward(self) -> bool:
        return self.go_forward()

    def reload_page(self) -> bool:
        if not self._page:
            return False
        try:
            self._page.reload(timeout=20000, wait_until="commit")
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Reload failed: {e}")
            self._capture_failure_state("reload_failed")
            return False

    def reloadPage(self) -> bool:
        return self.reload_page()

    # Actions using Page Object Model (POM) PageRegistry
    def fill_field(self, element_name: str, value: str) -> bool:
        """Fills an input field matching the POM locator with the specified value."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot perform fill.")
            return False
            
        logger.info(f"[UiFixture] Filling element '{element_name}' with value: {value}")
        
        try:
            # Retrieve the compiled Playwright Locator directly from the registry
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.fill(value)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to fill field '{element_name}': {e}")
            self._capture_failure_state(f"fill_failed_{element_name}")
            return False

    def fillField(self, element_name: str, value: str) -> bool:
        return self.fill_field(element_name, value)

    def fill_field_with_value(self, element_name: str, value: str) -> bool:
        """Fills an input field - maps to FitNesse: | fill field | name | with value | val |"""
        return self.fill_field(element_name, value)

    def fillFieldWithValue(self, element_name: str, value: str) -> bool:
        return self.fill_field_with_value(element_name, value)

    def type_text(self, element_name: str, value: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.type(value)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to type into '{element_name}': {e}")
            self._capture_failure_state(f"type_failed_{element_name}")
            return False

    def typeText(self, element_name: str, value: str) -> bool:
        return self.type_text(element_name, value)

    def press_key(self, element_name: str, key: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.press(key)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to press '{key}' on '{element_name}': {e}")
            self._capture_failure_state(f"press_failed_{element_name}")
            return False

    def pressKey(self, element_name: str, key: str) -> bool:
        return self.press_key(element_name, key)

    def check_element(self, element_name: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.check()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to check '{element_name}': {e}")
            self._capture_failure_state(f"check_failed_{element_name}")
            return False

    def checkElement(self, element_name: str) -> bool:
        return self.check_element(element_name)

    def uncheck_element(self, element_name: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.uncheck()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to uncheck '{element_name}': {e}")
            self._capture_failure_state(f"uncheck_failed_{element_name}")
            return False

    def uncheckElement(self, element_name: str) -> bool:
        return self.uncheck_element(element_name)

    def upload_file(self, element_name: str, file_path: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="attached", timeout=5000)
            locator.set_input_files(file_path)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to upload file to '{element_name}': {e}")
            self._capture_failure_state(f"upload_failed_{element_name}")
            return False

    def uploadFile(self, element_name: str, file_path: str) -> bool:
        return self.upload_file(element_name, file_path)

    def drag_and_drop(self, source_name: str, target_name: str) -> bool:
        if not self._page:
            return False
        try:
            source = PageRegistry.get_locator(self._page, source_name)
            target = PageRegistry.get_locator(self._page, target_name)
            source.wait_for(state="visible", timeout=5000)
            target.wait_for(state="visible", timeout=5000)
            source.drag_to(target)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Drag and drop failed: {e}")
            self._capture_failure_state("drag_drop_failed")
            return False

    def dragAndDrop(self, source_name: str, target_name: str) -> bool:
        return self.drag_and_drop(source_name, target_name)

    def focus_element(self, element_name: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.focus()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to focus '{element_name}': {e}")
            self._capture_failure_state(f"focus_failed_{element_name}")
            return False

    def focusElement(self, element_name: str) -> bool:
        return self.focus_element(element_name)

    def click_button(self, element_name: str) -> bool:
        """Clicks an element matching the POM locator."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot perform click.")
            return False
            
        logger.info(f"[UiFixture] Clicking element '{element_name}'")
        
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.click()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to click selector '{element_name}': {e}")
            self._capture_failure_state(f"click_failed_{element_name}")
            return False

    def clickButton(self, element_name: str) -> bool:
        return self.click_button(element_name)

    def double_click(self, element_name: str) -> bool:
        """Double-clicks an element matching the POM locator."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot perform double click.")
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.dblclick()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to double click '{element_name}': {e}")
            self._capture_failure_state(f"double_click_failed_{element_name}")
            return False

    def doubleClick(self, element_name: str) -> bool:
        return self.double_click(element_name)

    def hover_element(self, element_name: str) -> bool:
        """Hovers over an element matching the POM locator."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot hover.")
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.hover()
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to hover '{element_name}': {e}")
            self._capture_failure_state(f"hover_failed_{element_name}")
            return False

    def hoverElement(self, element_name: str) -> bool:
        return self.hover_element(element_name)

    def select_dropdown(self, element_name: str, value: str) -> bool:
        """Selects a dropdown option by visible label or value."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot select dropdown.")
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.select_option(value)
            return True
        except Exception:
            try:
                locator = PageRegistry.get_locator(self._page, element_name)
                locator.wait_for(state="visible", timeout=5000)
                locator.select_option(label=value)
                return True
            except Exception as e:
                logger.error(f"[UiFixture] Failed to select dropdown '{element_name}': {e}")
                self._capture_failure_state(f"dropdown_failed_{element_name}")
                return False

    def selectDropdown(self, element_name: str, value: str) -> bool:
        return self.select_dropdown(element_name, value)

    def selectDropdownWithValue(self, element_name: str, value: str) -> bool:
        return self.select_dropdown(element_name, value)

    def pick_date(self, element_name: str, value: str) -> bool:
        """Sets a date field value."""
        if not self._page:
            logger.error("[UiFixture] No active page context. Cannot pick date.")
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            locator.wait_for(state="visible", timeout=5000)
            locator.fill(str(value))
            locator.press("Tab")
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Failed to pick date '{element_name}': {e}")
            self._capture_failure_state(f"date_failed_{element_name}")
            return False

    def pickDate(self, element_name: str, value: str) -> bool:
        return self.pick_date(element_name, value)

    def pickDateWithValue(self, element_name: str, value: str) -> bool:
        return self.pick_date(element_name, value)

    def wait_for_text(self, text: str, timeout: int = 10000) -> bool:
        """Waits until a specific text is visible on the page."""
        if not self._page:
            return False
        try:
            self._page.get_by_text(text, exact=False).wait_for(timeout=timeout)
            return True
        except Exception:
            return False

    def waitForText(self, text: str, timeout: int = 10000) -> bool:
        return self.wait_for_text(text, timeout)

    def waitForTextTimeout(self, text: str, timeout: int) -> bool:
        return self.wait_for_text(text, int(timeout))

    def wait_for_selector(self, selector: str, timeout: int = 10000) -> bool:
        if not self._page:
            return False
        try:
            self._page.wait_for_selector(selector, state="visible", timeout=int(timeout))
            return True
        except Exception:
            return False

    def waitForSelector(self, selector: str, timeout: int = 10000) -> bool:
        return self.wait_for_selector(selector, timeout)

    def wait_for_load_state(self, state: str = "load", timeout: int = 10000) -> bool:
        if not self._page:
            return False
        try:
            self._page.wait_for_load_state(state, timeout=int(timeout))
            return True
        except Exception:
            return False

    def waitForLoadState(self, state: str = "load", timeout: int = 10000) -> bool:
        return self.wait_for_load_state(state, timeout)

    # Assertions / Verifications
    def verify_text_present(self, text: str) -> bool:
        """Returns True if the specified text is present on the page."""
        if not self._page:
            return False
        try:
            return self._page.get_by_text(text, exact=False).is_visible(timeout=3000)
        except Exception:
            return False

    def verifyTextPresent(self, text: str) -> bool:
        return self.verify_text_present(text)

    def verify_element_present(self, element_name: str) -> bool:
        """Returns True if an element matching the POM locator is present on the page."""
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            return locator.count() > 0
        except Exception:
            return False

    def verifyElementPresent(self, element_name: str) -> bool:
        return self.verify_element_present(element_name)

    def verify_url(self, expected_url: str) -> bool:
        return bool(self._page and self._page.url == expected_url)

    def verifyUrl(self, expected_url: str) -> bool:
        return self.verify_url(expected_url)

    def verify_title(self, expected_title: str) -> bool:
        if not self._page:
            return False
        try:
            return self._page.title() == expected_title
        except Exception:
            return False

    def verifyTitle(self, expected_title: str) -> bool:
        return self.verify_title(expected_title)

    def verify_field_value(self, element_name: str, expected_value: str) -> bool:
        if not self._page:
            return False
        try:
            locator = PageRegistry.get_locator(self._page, element_name)
            return locator.input_value() == expected_value
        except Exception:
            return False

    def verifyFieldValue(self, element_name: str, expected_value: str) -> bool:
        return self.verify_field_value(element_name, expected_value)

    def verify_element_enabled(self, element_name: str) -> bool:
        if not self._page:
            return False
        try:
            return PageRegistry.get_locator(self._page, element_name).is_enabled()
        except Exception:
            return False

    def verifyElementEnabled(self, element_name: str) -> bool:
        return self.verify_element_enabled(element_name)

    def verify_element_disabled(self, element_name: str) -> bool:
        if not self._page:
            return False
        try:
            return PageRegistry.get_locator(self._page, element_name).is_disabled()
        except Exception:
            return False

    def verifyElementDisabled(self, element_name: str) -> bool:
        return self.verify_element_disabled(element_name)

    def get_text(self, element_name: str) -> str:
        if not self._page:
            return ""
        try:
            return PageRegistry.get_locator(self._page, element_name).inner_text()
        except Exception:
            return ""

    def getText(self, element_name: str) -> str:
        return self.get_text(element_name)

    def get_attribute(self, element_name: str, attribute_name: str) -> str:
        if not self._page:
            return ""
        try:
            return PageRegistry.get_locator(self._page, element_name).get_attribute(attribute_name) or ""
        except Exception:
            return ""

    def getAttribute(self, element_name: str, attribute_name: str) -> str:
        return self.get_attribute(element_name, attribute_name)

    def get_field_value(self, element_name: str) -> str:
        if not self._page:
            return ""
        try:
            return PageRegistry.get_locator(self._page, element_name).input_value()
        except Exception:
            return ""

    def getFieldValue(self, element_name: str) -> str:
        return self.get_field_value(element_name)

    def capture_screenshot(self, file_name: str) -> bool:
        if not self._page:
            return False
        try:
            screenshot_path = os.path.join(self._fitnesse_root, "files", "testResults", file_name)
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            self._page.screenshot(path=screenshot_path)
            return True
        except Exception as e:
            logger.error(f"[UiFixture] Screenshot failed: {e}")
            return False

    def captureScreenshot(self, file_name: str) -> bool:
        return self.capture_screenshot(file_name)

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
