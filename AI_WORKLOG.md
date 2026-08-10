# AI Worklog

## Entry — Transform and Parquet storage

**Task**

Transform the validated log records into a structured dataset and store it in a reproducible local format.

**Prompt**

Asked AI to implement Question 2 with a simple, explainable approach that still satisfies the assessment requirements.

**Output & evaluation**

AI proposed one transform function that normalizes timestamps to UTC, derives `event_date`, extracts deterministic `error_type`/`error_code` fields, writes Parquet, and reads the file back for verification. The approach is intentionally local and does not claim an AWS deployment.

**Verify & corrections**

I ran the full test suite and obtained 11 passing tests. I ran the pipeline on the supplied input, read the generated Parquet file back with pandas, and verified 2,857 rows, 10 expected columns, a timezone-aware UTC timestamp, and the expected error-type counts. A Windows sandbox permission issue with the placeholder output file was resolved before regenerating the real Parquet artifact.

## Entry — Business report and anomaly detection

**Task**

Answer the four customer questions from the clean Parquet dataset and persist reproducible results.

**Prompt**

Asked AI to implement a simple report that groups ERROR records by service, date, and normalized error type, uses an explicit anomaly rule, and reuses cleaning statistics from the Data Quality Report.

**Output & evaluation**

AI proposed small pandas functions and IQR for the seven daily counts. It also proposed an independent consistency check between ERROR totals grouped by service and by date. IQR is explainable for a POC, but seven days are not enough for a production baseline.

**Verify & corrections**

I ran 15 tests and generated the real JSON report. I verified `payment-api` has 139 errors, `2026-07-30` has 140 errors above the 42.75 IQR upper bound, the Top 3 error type/service pairs match the Parquet data, and both independent groupings total 287 ERROR records. A test fixture initially created both a low and high IQR outlier; I corrected the fixture so the test isolates the intended high spike.
