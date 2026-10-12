# Gemini

The rules for this repository are in `AGENTS.md`. Read it fully and follow it for every change.

- Extend the framework inside its layers; do not redesign it.
- No hardcoded ports, URLs or application names: use `Config`.
- Keep `python -m pytest -q -p no:allure_pytest_bdd tests/unit` green, including `tests/unit/test_architecture.py`.
- Ask the owner before changing anything listed in section 5 of `AGENTS.md`.
