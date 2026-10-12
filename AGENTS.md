# Framework rules for AI coding tools and developers

This file is the single source of truth. `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` and
`.cursor/rules/framework.mdc` only point here. Read it fully before you change anything.

`tests/unit/test_architecture.py` turns the structural rules below into failing tests. If a change makes it fail, the change
is wrong; do not edit the test to make it pass without the owner's approval.

## 1. What this is

A FitNesse (Slim, vendored `waferslim`, Python) automation framework for **UI, API, accessibility and visual** testing.
QA writes tests as **wiki tables** (column tables first, script tables for sequences). One copy of the folder is made per
application; the framework code is shared, the application layer is replaced.

**Golden rule: extend the framework inside its layers. Do not redesign it, rename its parts or add a second way of doing
something it already does.**

## 2. Layers and what may import what

| Layer | Folder | Holds | May import |
|---|---|---|---|
| Engines | `core/` | step engine, reports, visual / layout / accessibility / schema engines, config, the user store server | `core` only (the server also reads `pages`) |
| Fixtures | `fixtures/ui`, `fixtures/api`, `fixtures/visual`, `fixtures/accessibility` | Slim fixture classes that QA calls from wiki tables | `core`; `ui` may use `pages` and the visual mixin; `visual` and `accessibility` may use `fixtures.ui` |
| Application | `pages/`, `fixtures/ui/scenario/*`, `fixtures/visual/baseline/`, `data/` | page objects, scenarios, reference images, users | `core` (pages), fixtures as needed |
| Wiki | `FitNesseRoot/` | test suites, the page header (UI, Step Builder), theme | nothing (it is data) |
| Vendored | `waferslim/`, `fitnesse-standalone.jar` | the Slim server and FitNesse | **do not edit**; the only project hooks are the default-package search in `execution.py` and the report call in `server.py` |

Forbidden: `core` importing `fixtures`; `pages` importing `fixtures`; `fixtures/api` importing UI, visual or
accessibility fixtures or `pages`.

## 3. Where a change goes

| You want to... | Do this |
|---|---|
| Test a new screen | Add `pages/<name>_page.py` (subclass `BasePage`, locators as UPPER_CASE class attributes). No engine change |
| Add a UI scenario | New folder `fixtures/ui/scenario/<name>/` with a `DecisionFixture` subclass declaring `COLUMNS` |
| Add an API field or check | Extend `request_columns()` and `BaseRequestFixture` in `fixtures/api/base_fixture.py` |
| Add a visual / layout / accessibility check | `core/<engine>.py` for the logic, `fixtures/<area>/<name>_test.py` for the table |
| Add a report | Generator in `core/`, route in `core/user_store_server.py`, link in the profile menu of the page header |
| Add a setting | One line in `core/config.py` (`Config.NAME = os.getenv(...)`) and one in `.env.example` |
| Add a wiki example | `FitNesseRoot/FrontPage/<Suite>/<Page>.wiki` (see section 6) |

Every column fixture must declare `COLUMNS` (see `core/fixture_meta.py`) with snake_case names; the Step Builder and the wiki
lint test read them. A new fixture is found automatically: do not add import tables to pages.

## 4. Hard rules

1. **No hardcoded ports, hosts, application names or credentials in code or in the page header.** Use `Config`
   (`Config.fitnesse_url()`, `Config.store_url()`, `Config.APP_NAME`, `Config.MOCK_SERVER_PORT`) and, in the header,
   `iciStore(path)` / `ICI_APP`. Environment URLs are `${UI_BASE_URL}` / `${API_BASE_URL}` in wiki pages.
2. **Secrets never reach logs, reports, Allure or the screen.** Use `core.flow.shown_value()` for typed values and give secret
   columns `secret=True`.
3. **Never kill processes by name** (`java.exe`, `python.exe`). Free only this copy's ports (see `start_server.bat`).
4. **Do not delete or overwrite data you did not create** (results, baselines, reference images, users, wiki pages). Look at
   the target first; ask when unsure.
5. **No new dependency** in `requirements.txt` without asking. The schema check is built in on purpose.
6. **No new top-level folder.** Put files in the layer they belong to.
7. **Keep existing behaviour.** Defaults must stay as they are; a new option is off or empty by default.
8. **Application-specific code stays in the application layer.** Framework files must not name a product, screen or user.

## 5. Ask the owner before you

- change a layer boundary, the Slim decision-table protocol (`DecisionFixture`), a report format or `PageHeader` structure,
- edit `start_server.bat`, `.github/workflows`, `requirements.txt` or `waferslim/`,
- change the default of any setting, remove a feature, or rename a column or a fixture (wiki pages depend on them).

## 6. Wiki and page header rules (they break silently)

- Write `.wiki` files as **UTF-8 without BOM, LF endings**. A BOM makes FitNesse treat the page as a normal page.
- A test page starts with `---\nTest\n---`, a suite page with `---\nSuite\n---`. Page names are CamelCase.
- `FitNesseRoot/PageHeader/content.txt` is one literal block that **ends at the first closing `-!`**. The file must contain that
  sequence exactly once, at the very end. Never type it inside a script, comment or string.
- Undefined `${Var}` is rewritten by FitNesse to "undefined variable"; URLs in cells are auto-linked. Use the helpers in
  `core/html_utils.py` (`clean_html_text`, `clean_html_url`) when reading cells.
- Column headers: inputs are plain words (`wcag version`), outputs end with `?` (`status?`). The fixture method is the same
  name in snake_case.

## 7. Working method

1. Read the surrounding code and match its style, naming and comment density.
2. Make the smallest change that fits the layers above.
3. Add or update tests in `tests/unit/` (UI behaviour of the header is tested with Playwright in `test_step_builder_ui.py`).
4. Run the suite and fix everything it reports:

   ```
   python -m pytest -q -p no:allure_pytest_bdd tests/unit
   ```

   (`-p no:allure_pytest_bdd` is required: the two Allure plugins clash otherwise.)
5. Update `README.md` when behaviour or a setting changes. Say plainly what you could not verify.

**Done means:** the suite passes, no rule above is broken, existing pages still work, and nothing generated (results,
reports, `.env`) is left in the change.

## 8. Environment notes

- Windows. The shell may be PowerShell (no `&&`, no here-docs) or Git Bash; `python` must be on the path of the shell you use.
- Servers: FitNesse on `FITNESSE_PORT` (8080), user store / reports on `STORE_PORT` (8090), mock server on
  `MOCK_SERVER_PORT` (8089). Start with `start_server.bat`; it also clears old results.
- Do not run suites against a server the owner may be using without checking the port first.
- CI is GitHub Actions (`.github/workflows/automation-tests.yml`). It calls `python -m core.ci_run` and
  `python -m core.ci_reports`; keep the logic in those modules, not in the workflow YAML. There is no Jenkins pipeline.
