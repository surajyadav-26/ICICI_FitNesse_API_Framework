"""
Browser actions for the UI fixture: input, mouse, selection, waits, verifications,
browser handling (alerts / frames / tabs), files and test-data generation.

Slim table forms (each row is `| keyword | arg | keyword | arg |`):
    | enter text | #user | with value | admin |
    | select dropdown | #country | option | India |
    | wait for element visible | #banner | timeout | 5000 |
    | ensure | verify field value | #user | equals | admin |
Locators accept the dictionary names (username, password, login button), CSS, XPath ("//div"),
or an explicit prefix: css= xpath= id= name= text= label= placeholder= testid= role=
"""
import os
import random
import re
import string
import time
import uuid
from datetime import datetime, timedelta

from core.logger import logger
from core.pages import page_registry
from core.pages.login_page import LoginPage
from .ui_flow import StepError, step

DEFAULT_TIMEOUT_MS = 5000
_LOCATOR_PREFIXES = ("css", "xpath", "id", "name", "text", "label", "placeholder", "testid", "role")


class BrowserActionsMixin:
    """Playwright-backed actions. Requires the host class to provide the helpers noted below."""

    def _init_actions(self) -> None:
        self._frame = None
        self._current_page = ""
        self._dialog_policy = "accept"
        self._last_dialog_text = ""
        self._downloaded_files: list = []
        self._download_dir = os.path.join(self._workspace_dir, "runtime", "downloads")

    # ── Shared helpers ────────────────────────────────────────────────────────
    def _scope(self):
        return self._frame if self._frame is not None else self._page

    def _locator(self, name: str):
        text = self._page_selector(str(name).strip())
        scope = self._scope()
        prefix, _, rest = text.partition("=")
        if prefix.lower() in _LOCATOR_PREFIXES and rest:
            kind, rest = prefix.lower(), rest.strip()
            if kind == "css":
                return scope.locator(rest)
            if kind == "xpath":
                return scope.locator(f"xpath={rest}")
            if kind == "id":
                return scope.locator(f"#{rest}")
            if kind == "name":
                return scope.locator(f"[name='{rest}']")
            if kind == "text":
                return scope.get_by_text(rest)
            if kind == "label":
                return scope.get_by_label(rest)
            if kind == "placeholder":
                return scope.get_by_placeholder(rest)
            if kind == "testid":
                return scope.get_by_test_id(rest)
            role, _, role_name = rest.partition(":")
            return scope.get_by_role(role.strip(), name=role_name.strip()) if role_name else scope.get_by_role(role.strip())
        if text.startswith("//") or text.startswith("(//"):
            return scope.locator(f"xpath={text}")
        return LoginPage.get_locator(scope, text)

    def _page_selector(self, name: str) -> str:
        """Maps names from the active page, or LoginPage by default, to their selectors."""
        pages = page_registry.list_pages()
        if self._current_page in pages and name in pages[self._current_page]:
            return pages[self._current_page][name]
        page_part, _, locator_part = name.partition(".")
        if locator_part and locator_part in pages.get(page_part, {}):
            return pages[page_part][locator_part]
        if not self._current_page and name in pages.get("LoginPage", {}):
            return pages["LoginPage"][name]
        return name

    def _ok(self, description: str) -> bool:
        if self._allure:
            self._allure.add_step(description, "passed")
        self._log_simple_step(description)
        return True

    def _fail(self, key: str, error, description: str = "") -> str:
        logger.error(f"[UiFixture] {key}: {error}")
        self._last_error_html = ""
        self._capture_failure_state(key, str(error), description)
        return self._last_error_html or False

    def _timeout_ms(self, timeout) -> int:
        try:
            return int(str(timeout).strip())
        except ValueError:
            return DEFAULT_TIMEOUT_MS

    def _perform(self, description: str, key: str, action):
        """Runs action(); returns True, or the inline failure link after a screenshot."""
        if not self._page:
            logger.error(f"[UiFixture] No active page context. Cannot perform: {description}")
            return StepError("No active page opened")
        try:
            action()
            return self._ok(description)
        except Exception as error:
            return self._fail(key, error, description)

    def _verify(self, description: str, key: str, check) -> bool:
        """Runs check() -> bool; a failed or erroring check captures a screenshot and returns False."""
        if not self._page:
            return False
        try:
            passed = bool(check())
        except Exception as error:
            logger.error(f"[UiFixture] {key}: {error}")
            passed = False
        if passed:
            self._ok(description)
        else:
            self._capture_failure_state(key, "Verification did not pass", description)
        return passed

    def _peek(self, kind: str, argument: str) -> bool:
        """Quiet checks used by IF conditions (never take screenshots)."""
        if not self._page:
            return False
        try:
            if kind == "text present":
                return self._scope().get_by_text(argument).first.is_visible(timeout=1000)
            locator = self._locator(argument)
            if kind == "element present":
                return locator.count() > 0
            if kind == "element enabled":
                return locator.first.is_enabled(timeout=1000)
            return locator.first.is_visible(timeout=1000)
        except Exception:
            return False

    def _attach_page_listeners(self, page) -> None:
        """Hooks dialogs and downloads for a page (called for the first page and any new tab)."""
        def on_dialog(dialog):
            self._last_dialog_text = dialog.message
            logger.info(f"[UiFixture] Browser dialog ({dialog.type}): {dialog.message} -> {self._dialog_policy}")
            if self._dialog_policy == "dismiss":
                dialog.dismiss()
            else:
                dialog.accept()

        def on_download(download):
            try:
                os.makedirs(self._download_dir, exist_ok=True)
                target = os.path.join(self._download_dir, download.suggested_filename)
                download.save_as(target)
                self._downloaded_files.append(download.suggested_filename)
                logger.info(f"[UiFixture] File downloaded: {target}")
            except Exception as error:
                logger.error(f"[UiFixture] Download failed: {error}")

        page.on("dialog", on_dialog)
        page.on("download", on_download)

    def _on_new_page(self, page) -> None:
        self._attach_page_listeners(page)

    @step
    def use_page(self, page_name: str) -> bool:
        """| use page | LoginPage |  - locator names now resolve from data/pages/LoginPage.json first."""
        if not page_registry.page_exists(page_name):
            return StepError(f"Page '{page_name}' not found in data/pages")
        self._current_page = str(page_name).strip()
        return self._ok(f"Use page '{self._current_page}'")

    # ── 1. Browser ────────────────────────────────────────────────────────────
    @step
    def open_browser(self, *args) -> bool:
        """| open browser |  or  | open browser | firefox |"""
        return self.start_browser(*args)

    @step
    def refresh_page(self) -> bool:
        """| refresh page |"""
        return self._perform("Refresh page", "refresh_failed", lambda: self._page.reload(wait_until="load"))

    @step
    def go_back(self) -> bool:
        """| go back |"""
        return self._perform("Go back", "go_back_failed", lambda: self._page.go_back())

    @step
    def go_forward(self) -> bool:
        """| go forward |"""
        return self._perform("Go forward", "go_forward_failed", lambda: self._page.go_forward())

    # ── 2. Input ──────────────────────────────────────────────────────────────
    @step
    def enter_text_with_value(self, element_name: str, value: str) -> bool:
        """| enter text | #user | with value | admin |"""
        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            locator.fill(value)
        return self._perform(f"Enter text '{value}' into '{element_name}'", f"enter_text_failed_{element_name}", action)

    @step
    def clear_field(self, element_name: str) -> bool:
        """| clear field | #user |"""
        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            locator.fill("")
        return self._perform(f"Clear field '{element_name}'", f"clear_field_failed_{element_name}", action)

    @step
    def press_key(self, key: str) -> bool:
        """| press key | Enter |"""
        return self._perform(f"Press key '{key}'", f"press_key_failed_{key}", lambda: self._page.keyboard.press(key))

    @step
    def press_key_on(self, key: str, element_name: str) -> bool:
        """| press key | Enter | on | #search |"""
        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            locator.press(key)
        return self._perform(f"Press key '{key}' on '{element_name}'", f"press_key_failed_{element_name}", action)

    # ── 3. Mouse ──────────────────────────────────────────────────────────────
    def _mouse(self, label: str, element_name: str, method: str):
        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            if method == "click":
                locator.click()
            elif method == "dblclick":
                locator.dblclick()
            elif method == "right":
                locator.click(button="right")
            elif method == "hover":
                locator.hover()
            else:
                locator.scroll_into_view_if_needed()
        return self._perform(f"{label} '{element_name}'", f"{method}_failed_{element_name}", action)

    @step(raw=True)
    def attempt_login_with_password(self, username: str, password: str) -> bool:
        """| attempt login | admin | with password | admin123 |"""
        def action():
            username_field = self._locator("framework username")
            password_field = self._locator("framework password")
            username_field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            password_field.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            username_field.fill(username)
            password_field.fill(password)
            self._locator("framework login button").click()

        return self._perform("Attempt application login", "login_attempt_failed", action)

    @step(raw=True)
    def verify_login_error(self, expected_message: str) -> bool:
        """| ensure | verify login error | Invalid username or password. |"""
        return self._verify(
            f"Verify login error '{expected_message}'",
            "login_error_mismatch",
            lambda: self._locator("login error message").inner_text(timeout=DEFAULT_TIMEOUT_MS).strip()
            == expected_message.strip(),
        )

    @step(raw=True)
    def logout(self) -> bool:
        """| logout |"""
        def action():
            profile_menu = self._locator("profile menu")
            profile_menu.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            profile_menu.click()
            sign_out = self._locator("sign out button")
            sign_out.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            sign_out.click()

        return self._perform("Sign out of the application", "logout_failed", action)

    @step
    def click_element(self, element_name: str) -> bool:
        """| click element | #login |"""
        return self._mouse("Click", element_name, "click")

    @step
    def double_click(self, element_name: str) -> bool:
        """| double click | #row |"""
        return self._mouse("Double click", element_name, "dblclick")

    @step
    def right_click(self, element_name: str) -> bool:
        """| right click | #row |"""
        return self._mouse("Right click", element_name, "right")

    @step
    def hover_over(self, element_name: str) -> bool:
        """| hover over | #menu |"""
        return self._mouse("Hover over", element_name, "hover")

    @step
    def scroll_to_element(self, element_name: str) -> bool:
        """| scroll to element | #footer |"""
        return self._mouse("Scroll to", element_name, "scroll")

    # ── 4. Selection ──────────────────────────────────────────────────────────
    @step
    def select_dropdown_option(self, element_name: str, option: str) -> bool:
        """| select dropdown | #country | option | India |  (matches the visible label, then the value)"""
        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            try:
                locator.select_option(label=option, timeout=2000)
            except Exception:
                locator.select_option(value=option, timeout=DEFAULT_TIMEOUT_MS)
        return self._perform(f"Select '{option}' in dropdown '{element_name}'", f"select_failed_{element_name}", action)

    def _set_checked(self, label: str, element_name: str, checked: bool, radio: bool = False):
        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            if radio:
                locator.check()
            else:
                locator.set_checked(checked)
        return self._perform(f"{label} '{element_name}'", f"checkbox_failed_{element_name}", action)

    @step
    def check_checkbox(self, element_name: str) -> bool:
        """| check checkbox | #terms |"""
        return self._set_checked("Check checkbox", element_name, True)

    @step
    def uncheck_checkbox(self, element_name: str) -> bool:
        """| uncheck checkbox | #terms |"""
        return self._set_checked("Uncheck checkbox", element_name, False)

    @step
    def select_radio_button(self, element_name: str) -> bool:
        """| select radio button | #gender-male |"""
        return self._set_checked("Select radio button", element_name, True, radio=True)

    @step
    def set_toggle_to(self, element_name: str, state: str) -> bool:
        """| set toggle | #notifications | to | on |"""
        wanted = str(state).strip().lower() in ("on", "true", "yes", "1", "enabled")

        def action():
            locator = self._locator(element_name)
            locator.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            aria = locator.get_attribute("aria-checked")
            if aria is not None:  # custom switch widgets
                if (aria == "true") != wanted:
                    locator.click()
            else:
                locator.set_checked(wanted)
        return self._perform(f"Set toggle '{element_name}' to {state}", f"toggle_failed_{element_name}", action)

    # ── 5. Wait ───────────────────────────────────────────────────────────────
    def _wait_element(self, label: str, element_name: str, timeout, state: str):
        timeout_ms = self._timeout_ms(timeout)

        def action():
            locator = self._locator(element_name)
            if state == "clickable":
                locator.wait_for(state="visible", timeout=timeout_ms)
                deadline = time.time() + timeout_ms / 1000
                while not locator.first.is_enabled():
                    if time.time() > deadline:
                        raise TimeoutError(f"'{element_name}' did not become clickable")
                    time.sleep(0.1)
            else:
                locator.first.wait_for(state=state, timeout=timeout_ms)
        return self._perform(f"{label} '{element_name}'", f"wait_{state}_failed_{element_name}", action)

    @step
    def wait_for_element_visible(self, element_name: str) -> bool:
        """| wait for element visible | #banner |"""
        return self._wait_element("Wait for element visible", element_name, DEFAULT_TIMEOUT_MS, "visible")

    @step
    def wait_for_element_visible_timeout(self, element_name: str, timeout: str) -> bool:
        """| wait for element visible | #banner | timeout | 10000 |"""
        return self._wait_element("Wait for element visible", element_name, timeout, "visible")

    @step
    def wait_for_element_invisible(self, element_name: str) -> bool:
        """| wait for element invisible | #spinner |"""
        return self._wait_element("Wait for element invisible", element_name, DEFAULT_TIMEOUT_MS, "hidden")

    @step
    def wait_for_element_invisible_timeout(self, element_name: str, timeout: str) -> bool:
        """| wait for element invisible | #spinner | timeout | 10000 |"""
        return self._wait_element("Wait for element invisible", element_name, timeout, "hidden")

    @step
    def wait_for_element_clickable(self, element_name: str) -> bool:
        """| wait for element clickable | #submit |"""
        return self._wait_element("Wait for element clickable", element_name, DEFAULT_TIMEOUT_MS, "clickable")

    @step
    def wait_for_element_clickable_timeout(self, element_name: str, timeout: str) -> bool:
        """| wait for element clickable | #submit | timeout | 10000 |"""
        return self._wait_element("Wait for element clickable", element_name, timeout, "clickable")

    @step
    def wait_for_text(self, text: str) -> bool:
        """| wait for text | Welcome |  (the form with | timeout | ms | is wait_for_text_timeout)"""
        return self.wait_for_text_timeout.__wrapped__(self, text, str(DEFAULT_TIMEOUT_MS))

    @step
    def wait_for_page_load(self) -> bool:
        """| wait for page load |"""
        return self._perform("Wait for page load", "wait_page_load_failed",
                             lambda: self._page.wait_for_load_state("load", timeout=20000))

    @step
    def wait_for_timeout(self, milliseconds: str) -> bool:
        """| wait for timeout | 2000 |  - fixed pause in milliseconds"""
        pause = self._timeout_ms(milliseconds)
        return self._perform(f"Wait {pause} ms", "wait_timeout_failed", lambda: self._page.wait_for_timeout(pause))

    # ── 6. Verification (use with `| ensure | ... |`) ─────────────────────────
    @step
    def verify_text_not_present(self, text: str) -> bool:
        """| ensure | verify text not present | Error |"""
        return self._verify(f"Verify text not present '{text}'", f"verify_text_not_present_failed_{text}",
                            lambda: not self._scope().get_by_text(text).first.is_visible(timeout=1000))

    @step
    def verify_element_not_present(self, element_name: str) -> bool:
        """| ensure | verify element not present | #error |"""
        return self._verify(f"Verify element not present '{element_name}'", f"verify_element_not_present_failed_{element_name}",
                            lambda: self._locator(element_name).count() == 0)

    @step
    def verify_element_visible(self, element_name: str) -> bool:
        """| ensure | verify element visible | #banner |"""
        return self._verify(f"Verify element visible '{element_name}'", f"verify_element_visible_failed_{element_name}",
                            lambda: self._locator(element_name).first.is_visible(timeout=3000))

    @step
    def verify_element_enabled(self, element_name: str) -> bool:
        """| ensure | verify element enabled | #submit |"""
        return self._verify(f"Verify element enabled '{element_name}'", f"verify_element_enabled_failed_{element_name}",
                            lambda: self._locator(element_name).first.is_enabled(timeout=3000))

    @step
    def verify_field_value_equals(self, element_name: str, expected: str) -> bool:
        """| ensure | verify field value | #user | equals | admin |"""
        return self._verify(f"Verify field '{element_name}' value equals '{expected}'", f"verify_field_value_failed_{element_name}",
                            lambda: self._locator(element_name).first.input_value(timeout=3000) == expected)

    @step
    def verify_dropdown_value_equals(self, element_name: str, expected: str) -> bool:
        """| ensure | verify dropdown value | #country | equals | India |  (selected label or value)"""
        def check():
            selected = self._locator(element_name).first.evaluate(
                "el => { const o = el.options[el.selectedIndex]; return o ? [o.text.trim(), o.value] : []; }")
            return expected in selected
        return self._verify(f"Verify dropdown '{element_name}' value equals '{expected}'", f"verify_dropdown_failed_{element_name}", check)

    @step
    def verify_url(self, expected: str) -> bool:
        """| ensure | verify url | /dashboard |  (contains; prefix with = for an exact match)"""
        def check():
            current = self._page.url
            return current == expected[1:] if expected.startswith("=") else expected in current
        return self._verify(f"Verify URL '{expected}'", "verify_url_failed", check)

    @step
    def verify_page_title(self, expected: str) -> bool:
        """| ensure | verify page title | Dashboard |  (contains; prefix with = for an exact match)"""
        def check():
            title = self._page.title()
            return title == expected[1:] if expected.startswith("=") else expected in title
        return self._verify(f"Verify page title '{expected}'", "verify_page_title_failed", check)

    # ── 7. Browser handling ───────────────────────────────────────────────────
    @step
    def accept_alert(self) -> bool:
        """| accept alert |  - place BEFORE the step that opens the alert."""
        self._dialog_policy = "accept"
        return self._ok("Handle alert: accept")

    @step
    def dismiss_alert(self) -> bool:
        """| dismiss alert |  - place BEFORE the step that opens the alert."""
        self._dialog_policy = "dismiss"
        return self._ok("Handle alert: dismiss")

    @step
    def verify_alert_text(self, expected: str) -> bool:
        """| ensure | verify alert text | Are you sure? |  (contains, last alert shown)"""
        passed = expected in self._last_dialog_text
        if passed:
            self._ok(f"Verify alert text '{expected}'")
        else:
            logger.error(f"[UiFixture] Alert text '{self._last_dialog_text}' does not contain '{expected}'")
            self._capture_failure_state("verify_alert_text_failed")
        return passed

    @step
    def switch_to_frame(self, element_name: str) -> bool:
        """| switch to frame | #payment-iframe |"""
        def action():
            text = str(element_name).strip()
            prefix, _, rest = text.partition("=")
            selectors = {"css": rest, "id": f"#{rest}", "xpath": f"xpath={rest}", "name": f"[name='{rest}']"}
            selector = selectors.get(prefix.lower(), f"xpath={text}" if text.startswith("//") else text)
            self._frame = self._page.frame_locator(selector)
        return self._perform(f"Switch to frame '{element_name}'", f"switch_frame_failed_{element_name}", action)

    @step
    def switch_to_default_frame(self) -> bool:
        """| switch to default frame |"""
        self._frame = None
        return self._ok("Switch to default frame")

    @step
    def switch_window(self, target: str) -> bool:
        """| switch window | 2 |  (1-based tab number, or part of the tab title / URL)"""
        def action():
            pages = self._context.pages
            chosen = None
            if str(target).strip().isdigit():
                index = int(str(target).strip()) - 1
                chosen = pages[index] if 0 <= index < len(pages) else None
            else:
                chosen = next((p for p in pages if target in p.title() or target in p.url), None)
            if chosen is None:
                raise LookupError(f"No tab matches '{target}' ({len(pages)} open)")
            chosen.bring_to_front()
            self._page = chosen
            self._frame = None
        return self._perform(f"Switch to window/tab '{target}'", "switch_window_failed", action)

    @step
    def close_current_tab(self) -> bool:
        """| close current tab |"""
        def action():
            self._page.close()
            remaining = self._context.pages
            self._page = remaining[-1] if remaining else None
            self._frame = None
        return self._perform("Close current tab", "close_tab_failed", action)

    # ── 8. File ───────────────────────────────────────────────────────────────
    @step
    def upload_file_path(self, element_name: str, file_path: str) -> bool:
        """| upload file | #resume | path | C:/files/resume.pdf |"""
        def action():
            if not os.path.isfile(file_path):
                raise FileNotFoundError(file_path)
            self._locator(element_name).first.set_input_files(file_path)
        return self._perform(f"Upload file '{file_path}' to '{element_name}'", f"upload_failed_{element_name}", action)

    @step
    def verify_file_downloaded(self, file_name: str) -> bool:
        """| ensure | verify file downloaded | report.pdf |  (waits up to 10s; partial names match)"""
        def check():
            deadline = time.time() + 10
            while time.time() < deadline:
                if any(file_name in name for name in self._downloaded_files):
                    return True
                if os.path.isdir(self._download_dir) and any(file_name in n for n in os.listdir(self._download_dir)):
                    return True
                self._page.wait_for_timeout(250)  # pumps Playwright events so download handlers can run
            return False
        return self._verify(f"Verify file downloaded '{file_name}'", f"verify_download_failed_{file_name}", check)

    # ── 9. Test data ──────────────────────────────────────────────────────────
    @step
    def capture_text_to_variable_as(self, element_name: str, variable: str) -> bool:
        """| capture text to variable | #balance | as | balance |"""
        def action():
            locator = self._locator(element_name)
            locator.first.wait_for(state="visible", timeout=DEFAULT_TIMEOUT_MS)
            self._vars[str(variable).strip()] = (locator.first.text_content() or "").strip()
        return self._perform(f"Capture text of '{element_name}' into '{variable}'", f"capture_text_failed_{element_name}", action)

    @step
    def generate_test_data_into(self, data_type: str, variable: str) -> bool:
        """| generate test data | email | into | userEmail |
        Types: first_name last_name full_name email phone username password uuid number
               date text address company city"""
        value = self._generate_data(str(data_type).strip().lower().replace(" ", "_"))
        if value is None:
            return StepError(f"Unknown test data type '{data_type}'")
        self._vars[str(variable).strip()] = value
        logger.info(f"[UiFixture] Generated {data_type} into ${{{variable}}}")
        return self._ok(f"Generate test data '{data_type}' into '{variable}'")

    @staticmethod
    def _generate_data(data_type: str):
        try:
            from faker import Faker
            fake = Faker()
        except Exception:
            fake = None
        letters = lambda n: "".join(random.choices(string.ascii_lowercase, k=n))
        generators = {
            "first_name": lambda: fake.first_name() if fake else letters(6).title(),
            "last_name": lambda: fake.last_name() if fake else letters(8).title(),
            "full_name": lambda: fake.name() if fake else f"{letters(6).title()} {letters(8).title()}",
            "email": lambda: fake.unique.email() if fake else f"{letters(8)}@example.com",
            "phone": lambda: "".join(random.choices("6789", k=1) + random.choices(string.digits, k=9)),
            "username": lambda: fake.user_name() if fake else letters(8),
            "password": lambda: "".join(random.choices(string.ascii_letters + string.digits, k=10)) + "@1",
            "uuid": lambda: str(uuid.uuid4()),
            "number": lambda: str(random.randint(1000, 999999)),
            "date": lambda: (datetime.now() + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d"),
            "text": lambda: fake.sentence() if fake else f"{letters(5)} {letters(7)} {letters(6)}",
            "address": lambda: fake.address().replace("\n", ", ") if fake else f"{random.randint(1, 99)} {letters(8).title()} Street",
            "company": lambda: fake.company() if fake else f"{letters(7).title()} Ltd",
            "city": lambda: fake.city() if fake else letters(8).title(),
        }
        generator = generators.get(data_type)
        return generator() if generator else None

    # ── 11. Screenshot ────────────────────────────────────────────────────────
    @step
    def take_screenshot(self, *args) -> bool:
        """| take screenshot |  or  | take screenshot | login-page |"""
        if not self._page:
            return "No active page opened"
        label = re.sub(r"[^\w\-]", "_", str(args[0]).strip()) if args and str(args[0]).strip() else "screenshot"
        try:
            self._screenshot_counter += 1
            file_name = f"{label}-{self._screenshot_counter}.png"
            directory = os.path.join(self._fitnesse_root, self._screenshot_dir_path)
            os.makedirs(directory, exist_ok=True)
            path = os.path.join(directory, file_name)
            self._page.screenshot(path=path)
            if self._allure:
                with open(path, "rb") as image:
                    self._allure.add_attachment(f"Screenshot - {label}", image.read(), "image/png", "png")
            return self._ok(f"Take screenshot '{label}'")
        except Exception as error:
            logger.error(f"[UiFixture] Screenshot failed: {error}")
            return False
