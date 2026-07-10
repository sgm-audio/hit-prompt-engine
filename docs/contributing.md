# Contributing

See [CONTRIBUTING.md](https://github.com/sgm/hit-prompt-engine/blob/main/CONTRIBUTING.md)
in the repository root for full instructions.

## Quick checklist

1. `ruff check . && ruff format --check .`
2. `pytest tests/`
3. `bandit -r . --skip B101 -x tests/`
4. `pip-audit -r requirements.txt`
