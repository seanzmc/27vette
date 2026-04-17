# Roadmap Additions

## Build an Option Catalog Clean lookup formula column in the legacy Option Rules and Option Pricing sheets.
Before any migration, add a helper column that does XLOOKUP against Option Catalog Clean by RPO. Every row that returns #N/A is a row that can't migrate because its option doesn't exist canonically yet. This gives you a migration readiness score per sheet at a glance, and catches the "blocker" cases that Run 3 surfaces without needing to run an agent.

## Treat Audit Exceptions as your real progress tracker, not a quality gate.
Right now it has 3 resolved and 5 open. After each run, the agent should append new exceptions (ambiguous rows it punted on) rather than silently dropping them. This makes "done" an honest state.

## Add a scope_tested flag to Variant Catalog.
A simple column marking which variants have end-to-end trust (all clean sheets populated, helpers built, form-ready). Stingray Coupe 1LT becomes your first true-flag variant. This is your replication checklist.

## Defer the customer-facing form work until Variant Option Matrix exists for one variant.
It's tempting to start the form now in parallel, but the form's schema is the matrix's schema. Once the matrix is right for Stingray Coupe 1LT, Formidable Forms / WordPress wiring is almost mechanical.

## For agent specs, name the validation gates explicitly.
In your Script Séance spec pattern you use pnpm typecheck / lint / test. For workbook agents, the equivalent validation gates are:
    (a) does every option_id in the written sheet exist in Option Catalog Clean,
    (b) does every choice_group_id in members exist in Choice Groups Clean,
    (c) do row counts in Audit Exceptions only go up (never silent drops).
Codex/Claude Code should be told these explicitly so they check before declaring success.
