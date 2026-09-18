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
from core.allure_helper import AllureHelper


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


def clean_html_text(value: str) -> str:
    """
    Strips away FitNesse's auto-generated HTML anchor tags (<a href="...">...</a>)
    and returns only the visible text inside the link.
    """
    val_str = str(value).strip()
    
    # Extract the text between <a ...> and </a>
    match = re.search(r'<a[^>]*>([\s\S]*?)</a>', val_str)
    if match:
        return match.group(1).strip()
        
    # Fallback: strip any HTML tags
    cleaned = re.sub(r'<[^<]+?>', '', val_str).strip()
    return cleaned


class UiFixture:
    """
    Generic, step-by-step browser automation fixture for FitNesse.
    """

    def __init__(self, page_name: str = "UI Test Run") -> None:
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
        self._allure = None
        
        # 1. Natively extract and sanitize the FitNesse page name passed from constructor or system environment!
        env_page_name = os.environ.get("FITNESSE_PAGE_NAME")
        if env_page_name:
            self._test_name = clean_html_text(env_page_name)
        else:
            self._test_name = clean_html_text(page_name)
        
        # 2. Dynamically extract the FitNesse parent Suite Name!
        self._suite_name = "UI Tests"
        env_page_path = os.environ.get("FITNESSE_PAGE_PATH")
        if env_page_path:
            parts = [p.strip() for p in env_page_path.split(".") if p.strip()]
            if len(parts) >= 3:
                # E.g. "FrontPage.SwagLabs.LoginPage" -> suite is "SwagLabs"
                self._suite_name = parts[-2]
            elif len(parts) == 2:
                # E.g. "FrontPage.SwagLabs" -> suite is "SwagLabs"
                self._suite_name = parts[-1]

    # UI-Level Configuration Setters (Allows managing config directly from FitNesse UI!)
    def set_test_name(self, name: str) -> None:
        """Dynamically overrides the test case name inside Allure (resolves collapsing)."""
        self._test_name = clean_html_text(name)
        if self._allure:
            self._allure.test_name = self._test_name
        logger.info(f"[UiFixture] Allure Test Name set dynamically: '{self._test_name}'")

    def setTestName(self, name: str) -> None:
        self.set_test_name(name)

    def set_suite_name(self, name: str) -> None:
        """Dynamically overrides the suite name inside Allure."""
        self._suite_name = clean_html_text(name)
        if self._allure:
            self._allure.suite_name = self._suite_name
        logger.info(f"[UiFixture] Allure Suite Name set dynamically: '{self._suite_name}'")

    def setSuiteName(self, name: str) -> None:
        self.set_suite_name(name)
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
            
            # Query the local One-Time POP queue to dynamically resolve the running page name with ZERO table edits!
            try:
                import urllib.request
                import json
                with urllib.request.urlopen("http://127.0.0.1:8090/pop-run", timeout=2) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    retrieved_name = res_data.get("page_name", "")
                    if retrieved_name and retrieved_name != "UI Test Run":
                        self._test_name = retrieved_name
                        logger.info(f"[UiFixture] Auto-popped running page name from queue: '{self._test_name}'")
            except Exception as pop_err:
                logger.debug(f"[UiFixture] Failed to pop active page from queue: {pop_err}")
            
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
            
            # Lazy initialize the Allure UI Results helper, skipping parent suite pages to avoid empty cards!
            if self._test_name != self._suite_name:
                self._allure = AllureHelper(test_name=self._test_name, suite_name=self._suite_name)
            
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
            
            if self._allure:
                self._allure.add_step(f"Start Headed {b_type.upper()} Browser" if not headless_mode else f"Start Headless {b_type.upper()} Browser", "passed")
            
            self._log_simple_step(f"Start Browser (browser: {b_type}, headless: {headless_mode})")
                
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
            if self._allure:
                self._allure.add_step("Close Browser & Free Resources", "passed")
                self._allure.write_result()
        except Exception:
            pass
        finally:
            self._allure = None
            
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
            
            if self._allure:
                self._allure.add_step(f"Navigate to {target_url}", "passed")
            
            self._log_simple_step(f"Navigate to '{target_url}'")
                
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
            
            if self._allure:
                self._allure.add_step(f"Fill field '{element_name}' with value '{value}'", "passed")
            
            self._log_simple_step(f"Fill field '{element_name}' with value '{value}'")
                
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
            
            if self._allure:
                self._allure.add_step(f"Click element '{element_name}'", "passed")
            
            self._log_simple_step(f"Click element '{element_name}'")
                
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
            
            if self._allure:
                self._allure.add_step(f"Wait for text '{text}'", "passed")
            
            self._log_simple_step(f"Wait for text '{text}' to appear (timeout: {t_ms}ms)")
                
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
            if not is_visible:
                self._capture_failure_state(f"verify_text_present_failed_{text}")
            else:
                self._log_simple_step(f"Verify text present '{text}'")
            return is_visible
        except Exception:
            self._capture_failure_state(f"verify_text_present_failed_{text}")
            return False

    def verifyTextPresent(self, text: str) -> bool:
        return self.verify_text_present(text)

    def verify_element_present(self, element_name: str) -> bool:
        """Returns True if an element matching the POM locator is present on the page."""
        if not self._page:
            return False
        try:
            locator = LoginPage.get_locator(self._page, element_name)
            is_present = locator.count() > 0
            if not is_present:
                self._capture_failure_state(f"verify_element_present_failed_{element_name}")
            else:
                self._log_simple_step(f"Verify element present '{element_name}'")
            return is_present
        except Exception:
            self._capture_failure_state(f"verify_element_present_failed_{element_name}")
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

            # Symmetrically Translate technical keys into highly professional corporate QA labels!
            raw_key = str(reason_prefix).strip()
            attachment_label = "Failure Screenshot"
            error_message = f"Execution failed on step: {raw_key.replace('_', ' ').title()}"

            if raw_key.startswith("click_failed_"):
                el = raw_key.replace("click_failed_", "")
                attachment_label = f"Failure Screenshot - Click failed on '{el}'"
                error_message = f"Click button failed on element '{el}'"
            elif raw_key.startswith("fill_failed_"):
                el = raw_key.replace("fill_failed_", "")
                attachment_label = f"Failure Screenshot - Fill failed on '{el}'"
                error_message = f"Fill field failed on element '{el}'"
            elif raw_key.startswith("verify_text_present_failed_"):
                txt = raw_key.replace("verify_text_present_failed_", "")
                attachment_label = f"Failure Screenshot - Text not present '{txt}'"
                error_message = f"Verification failed: Text '{txt}' was not found on the page."
            elif raw_key.startswith("verify_element_present_failed_"):
                el = raw_key.replace("verify_element_present_failed_", "")
                attachment_label = f"Failure Screenshot - Element not present '{el}'"
                error_message = f"Verification failed: Element '{el}' was not found on the page."
            elif raw_key.startswith("wait_text_failed_"):
                txt = raw_key.replace("wait_text_failed_", "")
                attachment_label = f"Failure Screenshot - Wait for text failed '{txt}'"
                error_message = f"Timeout failed: Wait for text '{txt}' timed out."

            # Symmetrical Allure UI Reporting Sourcing!
            if self._allure:
                try:
                    # Read the screenshot bytes and attach to Allure
                    with open(screenshot_path, "rb") as sf:
                        screenshot_bytes = sf.read()
                    self._allure.add_attachment(attachment_label, screenshot_bytes, "image/png", "png")
                    self._allure.set_failed(error_message)
                    # Write the final failed result immediately so it is captured on crash
                    self._allure.write_result()
                    self._allure = None
                except Exception as allure_err:
                    logger.debug(f"[UiFixture] Failed to attach screenshot to Allure: {allure_err}")

            # Symmetrical Simple Report UI Sourcing!
            # Registers the failure screenshot directly into report.html's audit trail!
            try:
                from core.report_generator import add_record
                import datetime
                add_record({
                    "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "method": "SCREENSHOT",
                    "url": f"failure-{raw_key}",
                    "status_code": 500, # Pass integer to prevent TypeError crashes in report generator!
                    "response_time_ms": 0,
                    "request_body": f"UI Assertion failed on step: {raw_key.replace('_', ' ').title()}",
                    "response_body": f'<div style="text-align: center; padding: 10px;"><img src="/{self._screenshot_dir_path}/{screenshot_name}" style="max-width: 100%; max-height: 450px; border: 2px solid var(--fail); border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);" alt="Failure Screenshot" /></div>',
                    "curl": f"http://localhost:8080/{self._screenshot_dir_path}/{screenshot_name}",
                    "json_file": "" # No JSON file for UI failures!
                })
            except Exception as simple_err:
                logger.debug(f"[UiFixture] Failed to log failure to Simple Report: {simple_err}")

            url = f"http://localhost:8080/{self._screenshot_dir_path}/{screenshot_name}"
            self._last_error_html = f'<a href="{url}" target="_blank" style="color: #ef4444; font-weight: bold;">[VIEW FAILURE SCREENSHOT]</a>'
            logger.info(f"[UiFixture] Failure screenshot saved successfully: {screenshot_path}")
        except Exception as e:
            logger.error(f"[UiFixture] Capturing failure screenshot failed: {e}")

    def _log_simple_step(self, step_name: str, status: str = "PASSED", body: str = "") -> None:
        """Symmetrically logs Playwright execution steps directly to report.html's audit trail!"""
        try:
            from core.report_generator import add_record
            import datetime
            add_record({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "method": "STEP",
                "url": step_name,
                "status_code": 200 if status == "PASSED" else 500,
                "response_time_ms": 0,
                "request_body": "",
                "response_body": body,
                "curl": "",
                "json_file": "" # No JSON file for UI steps!
            })
        except Exception as simple_err:
            logger.debug(f"[UiFixture] Failed to log step to Simple Report: {simple_err}")
