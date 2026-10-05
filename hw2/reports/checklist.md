# Checklist — HW2 Corrections

| Requirement | Status | Path |
|-------------|--------|------|
| Correction branch | Done | `hw2/accounting-correction` |
| Preserve / supersede old results | Done | `backups/pre_correction_d51066f/`, `outputs/SUPERSEDED_UNVERIFIED_README.md` |
| Remove tracked yfinance cache | Staged delete | `.gitignore` updated for `.cache/` |
| Fix return accounting | Done | `src/sis_hw2/backtest/engine.py` |
| Regression test (±10% → 0%) | Passed | `tests/test_accounting.py` |
| Next-close execution | Done | engine |
| ADV 20 sessions / momentum sessions | Done | `signals/factors.py` |
| Rank after top-N | Done | factors + construct |
| TTM vs labelled annual | Done | factors |
| Historical shares preferred | Done | `data/process.py` |
| Corrected rerun on cached data | Done | `outputs/tables/` |
| READ_ME_FIRST | Done | `reports/READ_ME_FIRST.md` |
| Exec summary / spec / log / slides | Updated | `reports/` |
| Sharadar PIT rebuild | Blocked | Needs your API access (env var) |
| Untouched OOS holdout | N/A | 2026 previously examined — disclosed |

## Reproduce
```bash
cd hw2 && source .venv/bin/activate
export PYTHONPATH=$PWD/src MPLBACKEND=Agg
pytest tests/test_accounting.py -q
python scripts/run_research.py --skip-download
```
