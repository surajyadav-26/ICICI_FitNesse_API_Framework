# Copilot instructions

The rules for this repository are in `AGENTS.md` at the repository root. Read it fully and follow it for every suggestion
and every change.

- Extend the framework inside its layers (`core`, `fixtures`, `pages`, `FitNesseRoot`); do not redesign it.
- No hardcoded ports, URLs or application names: use `Config`.
- Keep `python -m pytest -q -p no:allure_pytest_bdd tests/unit` green, including `tests/unit/test_architecture.py`.
- Ask the owner before changing anything listed in section 5 of `AGENTS.md`.
