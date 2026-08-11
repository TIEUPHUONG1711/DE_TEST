# AI Work Log

This log records the meaningful uses of AI that influenced the submitted work. Prompts are summarized from the working conversation. I reviewed and verified the outputs before including them in the repository.

## Entry 01 — Plan the Data Pipeline

**Task**  
Turn the Part A requirements into an implementation plan that could be completed and explained within the assessment time.

**Prompt**  
Asked AI to break the pipeline into simple stages covering ingestion, profiling, validation, cleaning, transformation, reporting, testing, documentation, and AWS design.

**Output and evaluation**  
AI produced a comprehensive plan, but the first version included more abstractions and stages than I could confidently explain. The requirement coverage was useful, while the implementation needed to remain small.

**Verification and corrections**  
I compared the plan with both assessment documents and mapped every required deliverable to a repository file. I kept the required stages but combined validation and cleaning into one explainable function and avoided unnecessary frameworks.

## Entry 02 — Implement Safe JSONL Ingestion

**Task**  
Read JSONL without stopping the complete pipeline when one source line is malformed.

**Prompt**  
Asked AI for a Python function that reads JSONL line by line, records malformed lines separately, and preserves source line numbers.

**Output and evaluation**  
AI proposed `json.loads()` inside `try/except` instead of loading the whole file with pandas. This approach isolated bad lines, but source-line traceability had to be retained for both successful records and errors.

**Verification and corrections**  
I added `_source_line_number`, stored parse-error details, and created focused pytest cases for valid JSON, malformed JSON, empty lines, and non-object JSON. Running `pytest -q` confirmed the current suite passes. The real run produced 2,923 raw lines, 2,905 parsed records, and 18 parse errors.

## Entry 03 — Profile the Supplied Logs

**Task**  
Identify the actual data-quality issues before deciding how to clean them.

**Prompt**  
Asked AI which profiling metrics were necessary for schema, missing values, timestamps, duplicates, services, levels, dates, trace IDs, and messages.

**Output and evaluation**  
AI proposed the core schema and missing-value checks. I added daily counts, trace-ID presence, common messages, and common ERROR messages because they help explain the seven-day dataset and later transformations.

**Verification and corrections**  
I ran `python pipeline/src/pipeline.py` on the supplied file. It reproducibly found 28 exact duplicate occurrences, 20 invalid timestamps, 18 missing levels, and 1,706 missing optional `trace_id` values. Profiling reports issues only; it does not mutate the raw records.

## Entry 04 — Define Fix/Drop/Keep Rules

**Task**  
Handle each observed issue deliberately without inventing missing business data.

**Prompt**  
Asked AI to propose simple Fix/Drop/Keep rules with reasons for malformed JSON, duplicate records, invalid timestamps, missing levels, whitespace, and optional trace IDs.

**Output and evaluation**  
AI recommended dropping unrecoverable events and keeping optional fields as null. The proposed `Heartbeat ok` to `INFO` mapping was reasonable but was an assumption rather than a confirmed customer rule.

**Verification and corrections**  
I inspected the affected messages and confirmed all 18 missing-level records contain `Heartbeat ok`. I documented this assumption, dropped 18 malformed lines, 28 duplicate occurrences, and 20 invalid timestamps, and retained missing `trace_id` as null. The accounting check passes: `2,923 raw = 2,857 clean + 66 dropped`; the 18 fixed records remain inside the clean count.

## Entry 05 — Transform and Store Parquet

**Task**  
Convert retained records into a structured analytical dataset.

**Prompt**  
Asked AI for a simple pandas transformation that normalizes timestamps to UTC, creates `event_date`, sets stable datatypes, writes Parquet, and verifies the output.

**Output and evaluation**  
AI proposed one transformation function and Parquet storage. The design was appropriate because Parquet preserves datatypes and suits column-based analytics, while UTC provides one consistent time standard.

**Verification and corrections**  
I ran the pipeline, read `pipeline/output/cleaned_logs.parquet` back with pandas, and verified 2,857 rows and 10 columns. The timestamp column is timezone-aware UTC and the output is overwritten intentionally instead of appended, preventing duplicates on reruns.

## Entry 06 — Extract Error Type and Code

**Task**  
Normalize parameterized ERROR messages so equivalent errors can be grouped.

**Prompt**  
Asked AI to design a deterministic parser for `error_type` and `error_code` using the message patterns in the DataPack, without using an LLM in the pipeline.

**Output and evaluation**  
AI proposed a small regular expression. This was easier to test and explain than an LLM, but it only covers known patterns and must not guess unseen error types.

**Verification and corrections**  
I added tests for known ERROR formats and non-ERROR messages. Unknown ERROR patterns receive `error_type = UNKNOWN` and a null code. The regenerated Parquet groups parameterized messages under stable types such as `ConnTimeout`, `HTTP 502`, and `PaymentDeclined` while preserving the original message for audit.

## Entry 07 — Build the Business Report

**Task**  
Answer all four customer questions from the clean dataset with reproducible results.

**Prompt**  
Asked AI to implement small pandas functions for ERROR counts by service and date, IQR anomaly detection, Top 3 error types by service, and cleaning statistics from the quality report.

**Output and evaluation**  
AI suggested IQR as an explicit anomaly rule and a consistency check between independent groupings. I accepted it for the POC but documented that seven days are insufficient for production seasonality analysis.

**Verification and corrections**  
I ran `python pipeline/src/report.py`. The output shows `payment-api` with 139 errors, `2026-07-30` with 140 errors above the 42.75 IQR upper bound, and the expected Top 3 types. ERROR totals grouped by service and date both equal 287. Cleaning metrics are read from `data_quality_report.json` instead of recalculated.

## Entry 08 — Design KB Chunking and Metadata

**Task**  
Build a local searchable KB from the eight supplied Markdown documents.

**Prompt**  
Asked AI to propose an explainable chunking strategy, required metadata, and a local search index after considering the two reading documents.

**Output and evaluation**  
AI recommended heading-based chunks with source, section, version, date, owner, and status metadata, plus SQLite FTS5. This matched the structured SOP/policy documents better than arbitrary fixed-size chunks.

**Verification and corrections**  
I compared the approach with `reading/01_chunking_basics.md`, ran `python kb/build_kb.py`, and inspected `kb/chunks.jsonl`. The result is reproducible: eight documents produce 22 chunks, with 20 active and two superseded chunks.

## Entry 09 — Debug the Chunking Test

**Task**  
Find why the heading-splitting unit test returned no sections.

**Prompt**  
Asked AI to review the failing pytest assertion and identify whether the problem was in the chunking function or the test input.

**Output and evaluation**  
AI identified that indentation inside the triple-quoted test string prevented headings from starting with `##`. The chunking logic itself was not the cause.

**Verification and corrections**  
I normalized the fixture with `textwrap.dedent`, reran pytest, and confirmed the two expected sections were returned. The complete current suite now reports `20 passed`.

## Entry 10 — Handle Conflicting Policy Versions

**Task**  
Prevent the KB from answering with the obsolete backup policy.

**Prompt**  
Asked AI to compare the supplied policy documents and propose a version/freshness mechanism that preserves history but retrieves only the current rule.

**Output and evaluation**  
AI identified the conflict between `POL-01 v1` and `POL-01 v2` and proposed `superseded` and `active` statuses. Keeping v1 for audit was preferable to deleting or overwriting it.

**Verification and corrections**  
I recorded both versions under the same document family, marked v1 superseded and v2 active, and filtered search with `status = 'active'`. A version-trap evaluation retrieves v2 with the current 23:30 schedule, 30-day retention, and restore approval rule; v1 is absent from normal search results.

## Entry 11 — Evaluate and Improve Retrieval

**Task**  
Create ten KB evaluation questions and measure whether expected sources appear in the Top 3 results.

**Prompt**  
Asked AI to design direct, multi-source, version-trap, and out-of-scope cases with expected answers, sources, pass criteria, and Retrieval Hit@3.

**Output and evaluation**  
The first automated run passed 7 of 9 source-bearing questions (77.78%). Q05 and Q07 missed one required chunk because the questions used Vietnamese phrases while the documents used `escalation` and `rerun`. The JSON question file also initially contained two unescaped line breaks, which caused a parse error.

**Verification and corrections**  
I fixed the invalid JSON, inspected the actual Top 3 chunks, and added only two documented query expansions: `chuyển` to `escalation` and `chạy lại` to `rerun`. Running `python kb/evaluate.py` now gives 9/9 and Hit@3 = 100%. I manually reviewed Q01, Q05, and out-of-scope Q10; all three passed groundedness checks.

## Entry 12 — Review the AWS Paper Design

**Task**  
Design a daily AWS version of the local pipeline without claiming a deployment.

**Prompt**  
Asked AI to review a simple S3 → Lambda → Glue → Parquet → Catalog → Athena architecture and identify required security controls and uncertainties.

**Output and evaluation**  
AI added Quarantine, CloudWatch, IAM least privilege, encryption, and operational notes. It initially treated Lambda as the default trigger, but Lambda is not always necessary for a scheduled daily batch.

**Verification and corrections**  
I checked the design against the assessment scope and kept the main diagram simple. The final document clearly states that Lambda suits immediate file-arrival processing, while EventBridge could trigger Glue directly for one daily batch. It also states that volume, retention, cost, and alert thresholds require customer confirmation and that the design has not been deployed or benchmarked on AWS.
