# Prompt transcript (submission appendix)

This file records prompts that are actually available from the Cursor session that produced this project. It is intended to travel with the submission so a grader need not access Cursor chat history.

## Platforms

| Role | Tool | Model |
|------|------|-------|
| Coding / replication | Cursor | **unknown** (not displayed in-session) |
| Implementation brief drafting (before Cursor coding) | ChatGPT | **unknown / not recorded** |
| Report review instructions (this revision request) | Prepared with ChatGPT assistance (per user message) | **unknown / not recorded** |

## Prompt 1 — Planning (user)

User provided three local paths (homework PDF, SPY workbook, Zarattini–Aziz–Barbon paper) and asked to plan and understand what the project requires before implementing.

**Purpose:** Scope the assignment (AI replication of the paper’s SPY intraday momentum strategy; test on instructor data; four Step 3 write-up deliverables).

**Assistant response (summary):** Summarized homework Steps 1–3, paper variants A/B/C, data notes, and asked scope questions (replication depth; code vs write-up).

## Prompt 2 — Full implementation brief (user)

A long specification beginning “You are my AI coding and quantitative-research assistant for B9339…” requiring complete implementation, verification, analysis, and draft write-up. It stated that the initial prompt was prepared with ChatGPT from the homework and paper; coding platform is Cursor; authors’ code must not be the primary replicator; workbook-specific audit findings were supplied as ChatGPT input to be re-verified.

**Purpose:** Authorize end-to-end build with explicit methodology, audit, tests, and report requirements.

**Outcome:** Project under `systematic_investment_strategies/` with code, tests, outputs, and draft `HW1_report.md`.

The full text of Prompt 2 is lengthy. An exact copy is preserved at:

- `logs/prompts/prompt2_implementation_brief.txt` (extracted from the user message in this session)

If that extract is incomplete relative to the user’s original paste, that limitation is stated in the extract header.

## Prompt 3 — Revision for submission quality (user)

Request dated 2026-09-22 to revise the existing project and `HW1_report.md` into a complete, internally consistent submission: fix hit-ratio/trade-count errors, expand AI-process documentation, add worked P&L verification, embed figures, produce PDF, etc. ChatGPT’s role in preparing the implementation brief and reviewing the report is to be acknowledged.

**Purpose:** Correct report errors and strengthen verification/readability without parameter-chasing.

**Outcome:** This revised report and supporting appendices.

## Earlier Cursor messages not separately archived

An earlier planning exchange exists in the same Cursor chat. No additional failed-prompt transcripts were manufactured. Where before/after metric pairs for intermediate buggy code are unavailable, the report states that honestly.
