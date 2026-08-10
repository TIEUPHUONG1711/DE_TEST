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

### Ingestion, Profiling, Validation, and Cleaning Tests

The focused tests cover ingest edge cases, the main profiling metrics, duplicate and timestamp rejection, the missing-level fix, source immutability, and raw/clean/dropped reconciliation.

Current verified result: **11 focused tests passed**.

Run the tests from the repository root:

```powershell
pytest -q
```
