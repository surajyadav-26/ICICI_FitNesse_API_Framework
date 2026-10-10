"""
Page objects: one class per application page, holding its locators and its actions.

    LoginPage.USERNAME          -> usable in a wiki table as `LoginPage.username`
    LoginPage(ui).login(u, p)   -> used by fixtures

Add a page by creating pages/<name>_page.py with a BasePage subclass; the Step Builder and the wiki tables pick it up.
registry.py (same folder) discovers the page classes and resolves `Page.locator` names.
"""
