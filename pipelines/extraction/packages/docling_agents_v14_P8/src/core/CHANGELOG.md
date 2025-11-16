# DoclingAgent – Change Log

Conventions
- Log conversions and page-level queries. Machine logs in `logs/agents/docling_agent/runs.jsonl`.

Entries

2025-09-24 – Conversion caching log entry
- Rationale: Track Docling version and conversion success for audit.
- Change: Log per-document convert+cache event with options and version.
- Outcome: Inventory plus logs provide provenance per run.

