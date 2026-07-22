# Contributing

## Getting started

```bash
git clone https://github.com/sgm-audio/hit-prompt-engine
cd hit-prompt-engine
cp .env.example .env
pip install -r requirements.txt
```

## Before you submit

1. **Lint & format**: `ruff check . && ruff format --check .`
2. **Tests**: `pytest tests/` — all 244 must pass
3. **Security**: `bandit -r . --skip B101 -x tests/`
4. **Audit**: `pip-audit -r requirements.txt`

## Project conventions

- Python 3.11+, no typechecker config yet (PEP 604 annotations used throughout)
- SQLite for dev, PostgreSQL planned — all DB access is raw `sqlite3` in `ingestion/deduper.py`
- All YAML config lives in `config/` — 3 files covering hit policy, genre taxonomy, variations
- `run_pipeline.py` is the CLI entrypoint; `api/prompt_library.py` is the FastAPI app

## Known issues

See [AGENTS.md](./AGENTS.md) for integration breakages between orchestration and ingestion modules.
