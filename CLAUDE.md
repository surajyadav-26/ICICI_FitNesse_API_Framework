# Claude Code

Follow the framework rules in @AGENTS.md. They apply to every change in this repository.

Short version:
- Extend the framework inside its layers (`core`, `fixtures`, `pages`, `FitNesseRoot`); do not redesign it.
- No hardcoded ports, URLs or application names: use `Config`.
- Run `python -m pytest -q -p no:allure_pytest_bdd tests/unit` and keep it green, including `test_architecture.py`.
- Ask the owner before changing anything listed in section 5 of AGENTS.md.
