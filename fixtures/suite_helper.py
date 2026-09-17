import os
from .ui_fixture import clean_html_text

# Global memory state to share the current running test and suite name across all SLiM fixtures!
CURRENT_TEST_NAME = "UI Test Run"
CURRENT_SUITE_NAME = "UI Tests"

class SuiteHelper:
    """
    Automated SLiM Suite context manager.
    Silently registered via PageHeader to provide zero-table dynamic test and suite names.
    """
    def set_page_name_and_page_path(self, page_name: str, page_path: str) -> bool:
        global CURRENT_TEST_NAME, CURRENT_SUITE_NAME
        
        # Clean and sanitize the FitNesse page name and path
        CURRENT_TEST_NAME = clean_html_text(page_name)
        
        clean_path = str(page_path).strip()
        CURRENT_SUITE_NAME = "UI Tests"
        if clean_path:
            parts = [p.strip() for p in clean_path.split(".") if p.strip()]
            if len(parts) >= 3:
                # E.g. "FrontPage.DummyAPI.Get_All_Products" -> suite is "DummyAPI"
                CURRENT_SUITE_NAME = parts[-2]
            elif len(parts) == 2:
                # E.g. "FrontPage.DummyAPI" -> suite is "DummyAPI"
                CURRENT_SUITE_NAME = parts[-1]
                
        # Also store them in os.environ for backwards compatibility with existing fixtures
        os.environ["FITNESSE_PAGE_NAME"] = CURRENT_TEST_NAME
        os.environ["FITNESSE_PAGE_PATH"] = clean_path
        
        return True

    def setPageNameAndPagePath(self, page_name: str, page_path: str) -> bool:
        return self.set_page_name_and_page_path(page_name, page_path)
