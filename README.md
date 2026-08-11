# Data Engineer Assessment

This repository contains the deliverables for the Data Engineer assessment, including a local data pipeline, a mini knowledge base, an AWS design, and the AI proficiency work log.

## Part A — Data Pipeline

### Input Dataset

The pipeline reads `data/app_logs_7days.jsonl`. Each physical line is expected to contain one JSON object representing an application event.

### Ingestion Strategy

The input is read one line at a time with `json.loads()`. A malformed line is recorded as a parse error without stopping ingestion of the remaining file. Each successfully parsed record receives a source line number for auditability.

The raw input file is never modified. Its SHA-256 checksum is calculated so that each generated result can be traced to the exact input version.

### Initial Data Profiling

| Metric | Count |
|---|---:|
| Raw lines | 2,923 |
| Parsed JSON records | 2,905 |
| JSON parse errors | 18 |
| Exact duplicate occurrences | 28 |
| Invalid timestamps | 20 |
| Records with a missing `level` | 18 |
| Records with a missing optional `trace_id` | 1,706 |

The valid timestamp range after conversion to UTC is from `2026-07-27T00:02:47+00:00` to `2026-08-02T23:56:35+00:00`.

#### Records by UTC Date

| Date | Records |
|---|---:|
| 2026-07-27 | 406 |
| 2026-07-28 | 383 |
| 2026-07-29 | 392 |
| 2026-07-30 | 518 |
| 2026-07-31 | 392 |
| 2026-08-01 | 395 |
| 2026-08-02 | 399 |

The date distribution contains 2,885 records with valid timestamps. The remaining 20 parsed records have invalid timestamps and therefore cannot be assigned to a date during profiling.

#### Additional Findings

- `trace_id` is present in 1,199 records and missing in 1,706 records.
- The most frequent message is `Daily report job started`, with 233 occurrences.
- The most frequent exact ERROR message is `ERR ConnTimeout db-primary after 30s retry=3`, with 115 occurrences.
- Parameterized messages contain values such as transaction IDs and user IDs, so they require deterministic normalization before error-type analysis.

The dataset contains five services:

- `auth-service`
- `payment-api`
- `web-portal`
- `batch-report`
- `notification-worker`

Profiling only detects and counts data-quality issues. No records are fixed or removed during this stage. The Fix/Drop/Keep decisions will be documented and applied during validation and cleaning.

### Raw Record Validation

Parsed records are validated against required fields, string datatypes, timezone-aware ISO-8601 timestamps, the five known services, the allowed `INFO`/`WARN`/`ERROR` levels, and leading or trailing whitespace. Exact duplicates are detected using all source fields while excluding the internal source-line metadata.

Validation found 66 parsed records with issues:

| Validation issue | Records |
|---|---:|
| Exact duplicate | 28 |
| Invalid timestamp | 20 |
| Missing `level` | 18 |

The 18 malformed JSON lines are tracked separately as ingestion parse errors because they cannot be validated as records. Validation only identifies issues; Fix/Drop/Keep actions are applied in the cleaning stage.

### Cleaning Decisions

| Issue | Action | Reason |
|---|---|---|
| Malformed JSON | Drop and record in rejection metadata | The truncated event cannot be reconstructed without guessing. |
| Exact duplicate | Drop the repeated occurrence; keep the first | Prevents duplicate events from inflating the analysis. |
| Invalid timestamp | Drop and record in rejection metadata | The event cannot be assigned reliably to a reporting date. |
| Missing `level` with `Heartbeat ok` | Fix to `INFO` | A successful heartbeat is informational; this is an explicit POC assumption. |
| Other missing or invalid required fields | Drop | Required analytical fields are not inferred without evidence. |
| Missing optional `trace_id` | Keep as null | `trace_id` is optional and is not required for the four reports. |
| Leading/trailing whitespace | Trim | This normalization preserves the field's meaning. |
| Valid service/level with noncanonical case | Normalize | Services use lowercase and levels use uppercase. |

The cleaning functions copy retained records instead of mutating the ingested source records. Unknown issue types default to Drop so questionable data is not silently admitted to the clean dataset.

#### Cleaning Results

| Metric | Count |
|---|---:|
| Raw lines | 2,923 |
| Clean records | 2,857 |
| Dropped records | 66 |
| Fixed records (included in clean records) | 18 |
| Unchanged records | 2,839 |

Dropped-record breakdown:

- 18 malformed JSON lines.
- 20 records with invalid timestamps.
- 28 repeated exact-duplicate occurrences.

All 18 fixed records had a missing `level` and the message `Heartbeat ok`; they were assigned `INFO`. The accounting check passes: `2,923 raw = 2,857 clean + 66 dropped`.

The pipeline writes these metrics, the input checksum, accounting status, and representative rejected/fixed samples to `pipeline/results/data_quality_report.json`. This file is the single source for the cleaning statistics used by the business report.

### Transformation and Storage

The 2,857 retained records are converted to a structured DataFrame with the following schema:

| Column | Type | Description |
|---|---|---|
| `timestamp` | UTC datetime | Normalized event timestamp |
| `event_date` | date | UTC date used for daily reporting |
| `service` | string | Normalized service name |
| `level` | string | `INFO`, `WARN`, or `ERROR` |
| `message` | string | Original log message after safe trimming |
| `request_id` | string | Request identifier |
| `trace_id` | nullable string | Optional trace identifier |
| `error_type` | nullable string | Stable type extracted from ERROR messages |
| `error_code` | nullable string | HTTP or business error code when present |
| `source_line_number` | integer | Original source line for auditability |

`error_type` and `error_code` are extracted with a small deterministic regular expression. No LLM is used in the production cleaning path, and messages that do not match the known pattern receive `UNKNOWN` rather than a guessed type.

The structured dataset is written to `pipeline/output/cleaned_logs.parquet`. Parquet was selected because it preserves datatypes, compresses columnar data efficiently, supports selective analytical reads, and integrates directly with pandas, AWS Glue, and Athena. The pipeline overwrites the same local output intentionally, then reads it back and verifies the row count.

Run the pipeline from the repository root:

```powershell
python pipeline/src/pipeline.py
```

### Business Analysis Results

The report reads only `cleaned_logs.parquet` and `data_quality_report.json`, then writes `pipeline/results/analysis_results.json`.

1. **Service with the most errors:** `payment-api` with **139** ERROR records.
2. **Daily error anomaly:** `2026-07-30` with **140** ERROR records. The IQR upper bound is `42.75`, so this date is a high outlier.
3. **Top three error types:**
   - `ConnTimeout` — `payment-api`: 114
   - `HTTP 502` — `web-portal`: 41
   - `NullPointer` — `batch-report`: 37
4. **Cleaning impact:** 66 dropped records and 18 fixed records. The detailed breakdown comes directly from the Data Quality Report.

As a consistency check, grouping by service and grouping by UTC date both produce **287 total ERROR records**. The anomaly result is only a POC signal because seven days are too short for a production baseline or seasonality analysis.

Run the business report after the pipeline:

```powershell
python pipeline/src/report.py
```

### AWS Daily Pipeline Design

The proposed production design is documented in:

- [`design/architecture.md`](design/architecture.md) — architecture diagram.
- [`design/aws_design.md`](design/aws_design.md) — service choices, daily flow, IAM/security, and uncertainties.

The main data flow is:

```text
Five internal systems
→ S3 Raw
→ Lambda
→ Glue ETL
→ S3 Quarantine / S3 Processed (Parquet)
→ Glue Crawler and Data Catalog
→ Athena
→ Reports
```

S3 Raw preserves the source files for audit and reruns. Lambda receives a new-file event and starts Glue; Glue performs validation, cleaning, and transformation. Rejected-record details go to Quarantine, while clean Parquet goes to Processed. The Crawler publishes the schema to the Data Catalog, and Athena queries the processed dataset. CloudWatch monitoring, IAM least privilege, S3 Block Public Access, TLS, and encryption apply across the architecture.

This is a paper design only; it has not been deployed or benchmarked on AWS. The main uncertainty is the required trigger model: Lambda is appropriate if processing must start when each file arrives, while EventBridge can start Glue directly for one scheduled daily batch. File volume, retention, cost, and alert thresholds also require customer confirmation.

### Ingestion, Profiling, Validation, and Cleaning Tests

The focused tests cover ingest edge cases, the main profiling metrics, duplicate and timestamp rejection, the missing-level fix, source immutability, and raw/clean/dropped reconciliation.

Current verified result: **20 focused tests passed**, including the pipeline and KB tests.

Run the tests from the repository root:

```powershell
pytest -q
```

## Part B — Mini Knowledge Base

### Knowledge Base Design

The knowledge base is built from the eight Markdown documents in `kb/docs/`. The original files are kept unchanged so every retrieved chunk can be traced back to its source.

Documents are split by level-two Markdown headings (`##`). Each section becomes one chunk. This structure-based strategy was selected because the supplied policies, SOPs, FAQ, guide, and runbook are already organized into meaningful sections. It keeps a procedure or policy rule together and is easier to explain than splitting at an arbitrary character count. A limitation is that very large sections would require a secondary size-based split in production.

Each chunk contains:

| Metadata | Purpose |
|---|---|
| `chunk_id` | Uniquely identifies the chunk |
| `document_id` | Groups chunks from the same document/version |
| `document_family` | Relates different versions of one policy |
| `title` and `section` | Preserve document structure and retrieval context |
| `version` | Supports version selection |
| `effective_date` | Indicates when the document becomes applicable |
| `owner` | Identifies the team responsible for the content |
| `status` | Marks a version as `active` or `superseded` |
| `source_path` | Provides traceability to the original document |
| `content` | Stores the searchable section text |

`kb/build_kb.py` produces 22 chunks from the eight documents: 20 active chunks and two superseded chunks. The chunks are saved to `kb/chunks.jsonl` for inspection and indexed in `kb/knowledge_base.db`.

The search index uses SQLite FTS5 with the Unicode tokenizer. `title`, `section`, and `content` are searchable, while metadata remains available for filtering and citation. SQLite FTS5 was selected because the KB is small, must run locally without an API key, and benefits from deterministic, testable full-text search. `kb/search_kb.py` returns the top three active chunks ranked with BM25.

Its main limitation is lexical matching: a question may use different terminology from the source. A small, documented query-expansion map handles the two observed differences in this POC. For a larger multilingual KB, embeddings or hybrid lexical/vector retrieval should be evaluated.

Build and search the KB from the repository root:

```powershell
python kb/build_kb.py
python kb/search_kb.py "sao lưu giữ bao lâu"
```

### Document Conflict and Version Handling

The supplied documents contain a deliberate conflict between `POL-01 v1` and `POL-01 v2`. They specify different backup schedules, retention periods, storage approaches, and restore-approval rules. Version 2 states that it replaces version 1 and has the newer effective date.

Both versions are retained for auditability, but their metadata differs:

- `POL-01 v1` is marked `superseded`.
- `POL-01 v2` is marked `active`.
- Both belong to the same `POL-01` document family.
- Search filters results with `status = 'active'`, so the superseded version cannot be used in normal answers.

The version-trap evaluation question verifies this behavior: the KB retrieves `POL-01 v2` and answers with the current rules—backup at 23:30, retention for 30 days, and restore approval by the Head of Operations. The manual evaluation also confirms that v1 was not used.

For a production update, the new document's owner, version, effective date, and replacement relationship must be validated before the previous active version is marked superseded. If these fields are missing or ambiguous, the document should not be published until the content owner confirms them.

### Evaluation Set and Results

The KB evaluation set contains 10 questions in `kb/eval_questions.json`. Each case records the question, expected answer, expected document and section, and explicit pass criteria. The set covers direct lookup, multi-source synthesis, a document-version trap, and an out-of-scope question.

Retrieval is evaluated with **Hit@3**: a source-bearing question passes only when every expected document/section appears in the first three active chunks. Nine questions can be evaluated automatically; the out-of-scope question has no expected source and therefore requires manual review.

| Metric | Result |
|---|---:|
| Total evaluation questions | 10 |
| Automatically evaluated retrieval questions | 9 |
| Retrieval questions passed | 9 |
| Retrieval Hit@3 | 100% |

The automated results are stored in `kb/eval_results.json`. Query expansion is intentionally limited to two terminology mappings found during evaluation: `chuyển` → `escalation` and `chạy lại` → `rerun`. This keeps the local lexical search understandable and deterministic while addressing terminology differences in the supplied documents.

Three representative answers were also reviewed manually in `kb/manual_eval_results.md`:

- **Q01 — Version correctness:** PASS. The answer uses active `POL-01 v2` and does not use superseded v1.
- **Q05 — Multi-source synthesis:** PASS. The answer combines the restart limit from `SOP-01` with the escalation owner from `SOP-02`.
- **Q10 — Out-of-scope refusal:** PASS. The answer states that salary, bonus, and leave information is absent instead of inventing a policy.

This manual review checks groundedness in addition to retrieval: the answer must be supported by the retrieved sources, use the current document version, and avoid unsupported claims. A limitation is that three manually reviewed answers are a small sample; a production KB should evaluate more questions whenever documents or retrieval logic change.

Run the complete retrieval evaluation from the repository root:

```powershell
python kb/evaluate.py
```
