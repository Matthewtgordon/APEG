# Runbook - APEG
# Command registry (treat each command as an API endpoint)

## Metadata (Read Once)
- Default working dir: `/home/matt/repos/APEG`
- Shell: `bash`
- Environment file: `.env`

## COMMAND REGISTRY
Each row is a single, copy-pasteable command. No implied flags.
| ID | Action | Command | Preconditions | Expected |
|---|---|---|---|---|
| run | Start APEG API server | `PYTHONPATH=. uvicorn src.apeg_core.main:app --reload --host 0.0.0.0 --port 8000` | deps installed; env vars set | Uvicorn running |
| lint | Lint source | `ruff check src/` | deps installed | No lint errors |

## COMMAND ARGUMENTS (Optional, only if needed)
| ID | Args | Example |
|---|---|---|
| test.single | {PATH} | `PYTHONPATH=. pytest tests/unit/test_api_routes.py -v` |

## TEST TIERS (Required - No Guessing)
| Tier | ID | Command | Preconditions | Fallback |
|---|---|---|---|---|
| SMOKE | test.smoke | `PYTHONPATH=. pytest tests/unit/ -v` | deps installed | ASK |
| TARGETED | test.targeted | `PYTHONPATH=. pytest tests/ -k {MODULE} -v` | deps installed | Run test.smoke |
| FULL | test.full | `PYTHONPATH=. pytest -v` | deps + .env | Run test.smoke and warn |

## ENVIRONMENT MODES
| Mode | Condition | Behavior |
|---|---|---|
| LIVE | .env exists | Run all tests |
| MOCK | SAFE_MOCK_OK=true | Use mock fixtures |
| SKIP | no .env | Skip integration |

## PHASE-SCOPED SCRIPTS
Only run scripts that match the current phase.
| Phase | Script | Command | Preconditions | Expected |
|---|---|---|---|---|
| 0 | `scripts/run_phase0_evidence.py` | `PYTHONPATH=. python scripts/run_phase0_evidence.py` | env configured | Evidence file updated |

## TROUBLESHOOTING MATRIX
| Error Pattern | Diagnosis | Next Command |
|---|---|---|
| `ModuleNotFoundError` | Missing dependency | `python -c "import importlib.util; print(importlib.util.find_spec('{pkg}') is not None)"` |



## COMMAND DISCOVERY RULES
If a required command is missing:
1. Use CMD-DISCOVER in GOVERNANCE.
2. Ask for confirmation.
3. Update this RUNBOOK.

