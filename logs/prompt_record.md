# Prompt and provenance record

## Sources of the initial brief

1. Course homework PDF: `data/raw/hw1.pdf` (B9339, Venetoulias, Fall 2026, HW1, due 2026-09-22 17:00 EST).
2. Paper: Zarattini, Aziz, Barbon (this version 2025-09-22), `data/raw/ZarattiniAzizBarbon.202509.pdf`.
3. Data: `data/raw/hw1.spy.20250313-20251201.intra-30m.xlsx`.
4. A detailed implementation brief in the user message of 2026-09-22 was prepared with **ChatGPT** from (1)–(2) and prior workbook inspection notes. ChatGPT model name/version: **unknown (not provided)**.

## Subsequent user prompts in this Cursor session

- Earlier planning turn: request to plan/understand the project from the three download paths.
- This completion turn: full specification requiring implementation, verification, analysis, and write-up (the long prompt beginning “You are my AI coding and quantitative-research assistant…”).

## Platform disclosure (for write-up Deliverable 1)

- **AI tool:** Cursor, used because it supports reading the paper/assignment, generating and editing Python in-repo, running tests, and iterating on errors in one workspace.
- **Language:** Python, for Excel ingestion, transparent transforms, tests, and plots.
- These are workflow reasons, not a claim that Cursor is objectively best.

## Environment

- Python 3.13.3 in project `.venv`
- Dependencies: see `requirements.txt` / `pyproject.toml`
- Config: `config.yaml`
