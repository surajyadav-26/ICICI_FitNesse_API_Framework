"""
Visual testing steps: compare the page (or one element) with a stored baseline screenshot.

    | ensure | verify visual match | home page |
    | ensure | verify visual match | home page | threshold | 0.5 |
    | ensure | verify element visual match | LoginPage.login box | as | login-box |
    | ignore visual region | css=.clock |           (masked in every following comparison)
    | clear visual ignores |
    | set visual threshold | 0.2 |                  (allowed % of differing pixels for the next comparisons)
    | update visual baseline | home page |          (accept the current look as the new baseline)

The first run for a name creates its baseline (status "new"). Later runs compare against it; review and approve
differences on the Visual Review page. Baselines are stored per browser and viewport, in data/visual/baselines.
"""
import os
import uuid

from core import visual_compare
from core.config import Config
from core.logger import logger
from .ui_flow import StepError, step

_STABILIZE_CSS = (
    "*,*::before,*::after{animation:none!important;transition:none!important;"
    "caret-color:transparent!important;scroll-behavior:auto!important}"
)


class VisualTestingMixin:
    """Playwright-backed visual comparison. Requires the host's page helpers (_page, _locator, _allure, _ok ...)."""

    def _init_visual(self) -> None:
        self._visual_ignores: list = []
        self._visual_threshold = Config.VISUAL_THRESHOLD

    # ── Steps ─────────────────────────────────────────────────────────────────
    @step
    def verify_visual_match(self, name: str) -> bool:
        """| ensure | verify visual match | home page |"""
        return self._visual_check(name, None, self._visual_threshold, False)

    @step
    def verify_visual_match_threshold(self, name: str, threshold: str) -> bool:
        """| ensure | verify visual match | home page | threshold | 0.5 |  (percent of pixels allowed to differ)"""
        value = self._parse_threshold(threshold)
        if value is None:
            return StepError(f"Invalid threshold '{threshold}' (use a percentage such as 0.5)")
        return self._visual_check(name, None, value, False)

    @step
    def verify_element_visual_match_as(self, element_name: str, name: str) -> bool:
        """| ensure | verify element visual match | LoginPage.login box | as | login-box |"""
        return self._visual_check(name, element_name, self._visual_threshold, False)

    @step
    def update_visual_baseline(self, name: str) -> bool:
        """| update visual baseline | home page |  - replaces the baseline with the current screenshot."""
        return self._visual_check(name, None, self._visual_threshold, True)

    @step
    def ignore_visual_region(self, element_name: str) -> bool:
        """| ignore visual region | css=.clock |  - masks dynamic content in later comparisons."""
        self._visual_ignores.append(str(element_name).strip())
        return self._ok(f"Ignore visual region '{element_name}'")

    @step
    def clear_visual_ignores(self) -> bool:
        """| clear visual ignores |"""
        self._visual_ignores = []
        return self._ok("Clear visual ignore regions")

    @step
    def set_visual_threshold(self, threshold: str) -> bool:
        """| set visual threshold | 0.2 |  - allowed % of differing pixels (default VISUAL_THRESHOLD)."""
        value = self._parse_threshold(threshold)
        if value is None:
            return StepError(f"Invalid threshold '{threshold}' (use a percentage such as 0.5)")
        self._visual_threshold = value
        return self._ok(f"Set visual threshold to {value}%")

    # ── Engine ────────────────────────────────────────────────────────────────
    @staticmethod
    def _parse_threshold(value):
        try:
            number = float(str(value).strip().rstrip("%"))
        except ValueError:
            return None
        return number if 0 <= number <= 100 else None

    def _visual_profile(self) -> str:
        browser = "chromium"
        try:
            browser = self._context.browser.browser_type.name
        except Exception:
            pass
        size = self._page.evaluate("[window.innerWidth, window.innerHeight]")
        return f"{browser}-{int(size[0])}x{int(size[1])}"

    def _stabilize_page(self) -> None:
        """Waits for fonts/load and freezes animations so the same screen always renders the same pixels."""
        try:
            self._page.wait_for_load_state("load", timeout=10000)
        except Exception:
            pass
        try:
            self._page.add_style_tag(content=_STABILIZE_CSS)
            self._page.evaluate("document.fonts ? document.fonts.ready.then(() => true) : true")
            self._page.wait_for_timeout(150)
        except Exception as error:
            logger.debug(f"[Visual] Stabilize skipped: {error}")

    def _capture_for_visual(self, element_name):
        folder = os.path.join(self._workspace_dir, "runtime", "visual-tmp")
        os.makedirs(folder, exist_ok=True)
        target = os.path.join(folder, f"{uuid.uuid4().hex}.png")
        masks = [self._locator(selector) for selector in self._visual_ignores]
        options = {"path": target, "animations": "disabled", "caret": "hide", "mask": masks, "mask_color": "#FF00FF"}
        if element_name:
            self._locator(element_name).first.screenshot(**options)
        else:
            self._page.screenshot(full_page=Config.VISUAL_FULL_PAGE, **options)
        return target

    def _visual_check(self, name, element_name, threshold, force_update):
        if not self._page:
            return StepError("No active page opened")
        try:
            visual_compare.clean_name(name)
        except ValueError as error:
            return StepError(str(error))

        captured = ""
        try:
            self._stabilize_page()
            profile = self._visual_profile()
            captured = self._capture_for_visual(element_name)
            result = visual_compare.check_against_baseline(
                captured, profile, name, threshold_pct=threshold, pixel_tolerance=Config.VISUAL_PIXEL_TOLERANCE,
                update=force_update or Config.VISUAL_UPDATE_BASELINE, test=getattr(self, "_test_name", ""))
        except Exception as error:
            logger.error(f"[Visual] Comparison failed for '{name}': {error}")
            return self._fail(f"visual_error_{name}", error)
        finally:
            if captured and os.path.exists(captured):
                os.remove(captured)

        self._report_visual(result)
        label = f"Visual {result.status}: '{name}' ({result.profile})"
        if result.status == "failed":
            logger.error(f"[Visual] {label} - {result.message}")
            return False
        if result.status == "new" and Config.VISUAL_FAIL_ON_NEW:
            logger.error(f"[Visual] {label} - no baseline existed and VISUAL_FAIL_ON_NEW is on")
            return False
        logger.info(f"[Visual] {label} - {result.message}")
        return self._ok(f"{label}: {result.message}")

    def _report_visual(self, result) -> None:
        """Attaches baseline/actual/diff to Allure and adds a side-by-side card to the simple report."""
        folder = visual_compare.result_dir(result.profile, result.name)
        if self._allure:
            try:
                for kind in ("baseline", "actual", "diff"):
                    path = os.path.join(folder, f"{kind}.png")
                    if os.path.isfile(path):
                        with open(path, "rb") as image:
                            self._allure.add_attachment(f"Visual {kind} - {result.name}", image.read(), "image/png", "png")
                if result.status == "failed":
                    self._allure.set_failed(f"Visual mismatch '{result.name}': {result.message}")
                else:
                    self._allure.add_step(f"Visual {result.status}: {result.name}", "passed")
            except Exception as error:
                logger.debug(f"[Visual] Allure attachment skipped: {error}")
        try:
            from core.report_generator import add_record
            import time
            base = f"/files/testResults/visual/{result.profile}/{result.name}"
            cell = ('<div style="flex:1;text-align:center;font-size:11px;color:#5C6E89">{}<br>'
                    '<img src="{}/{}.png" style="max-width:100%;border:1px solid #E5E8EB;border-radius:6px"></div>')
            images = "".join(cell.format(kind.title(), base, kind) for kind in ("baseline", "actual", "diff")
                             if kind != "diff" or result.status == "failed")
            add_record({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "method": "VISUAL",
                "url": f"{result.name} [{result.profile}] - {result.status.upper()} ({result.mismatch_pct}% diff)",
                "status_code": 500 if result.status == "failed" else 200,
                "response_time_ms": 0,
                "request_body": result.message,
                "response_body": f'<div style="display:flex;gap:10px;padding:8px">{images}</div>',
                "curl": "",
                "json_file": "",
            })
        except Exception as error:
            logger.debug(f"[Visual] Report record skipped: {error}")
