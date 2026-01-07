# RUNBOOK - APEG
# Command registry (treat each command like an API endpoint)

## Metadata (Read Once)
- Default working dir: `/home/matt/repos/APEG`
- Shell: `bash`
- Environment file: `.env.example`

## COMMAND REGISTRY
Each row is a single, copy-pasteable command. No implied flags.
| ID | Action | Command | Scope | Preconditions | Expected | Side Effects | Safe |
|---|---|---|---|---|---|---|---|
| env.activate | Activate venv | `source .venv/bin/activate` | setup | venv exists | Shell prompt shows (.venv) | shell state changes | yes |
| dev.server | Start APEG API server (reload) | `PYTHONPATH=. uvicorn src.apeg_core.main:app --reload --host 0.0.0.0 --port 8000` | dev | deps installed; env vars set | Uvicorn running on http://0.0.0.0:8000 | opens port 8000 | yes |
| test.all | Run full test suite | `PYTHONPATH=. pytest -v` | test | deps installed; env set if needed | All tests pass | none | yes |
| test.ci | Run CI coverage gate | `pytest --cov=apeg --cov-fail-under=75` | test | deps installed | Coverage >= 75% | none | yes |
| integration.safe_writes | Verify Shopify safe writes (Phase 2 integration) | `PYTHONPATH=. python tests/integration/verify_phase2_safe_writes.py` | integration | Redis running; DEMO safety gates | Exit 0 | Shopify API calls | no |
| ecomagent.install_editable | Install EcomAgent as editable package | `cd ../EcomAgent && pip install -e .` | integration | EcomAgent repo present | ecomagent installed | installs package | yes |
| ecomagent.verify_import | Verify EcomAgent import | `python -c "from src.seo_engine.engine import SEOEngine; print('Import successful')"` | integration | EcomAgent installed | Import successful | none | yes |

## COMMAND ARGUMENTS (Optional, only if needed)
| ID | Args | Example |
|---|---|---|
| test.single | {PATH} | `PYTHONPATH=. pytest tests/unit/test_api_routes.py -v` |





