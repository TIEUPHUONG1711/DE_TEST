# AWS Daily Log Pipeline Design

This is a proposed AWS design for running the local POC pipeline as a daily batch process. It has not been deployed or benchmarked on AWS. The architecture diagram is available in [`architecture.md`](./architecture.md).

## Services and Reasons

- **S3 Raw** keeps original JSONL files for audit and reruns. **Lambda** receives the S3 event and starts Glue; it coordinates only and does not run ETL.
- **Glue Job** performs ingest, validation, cleaning, transformation, and post-clean checks as managed batch ETL.
- **S3 Quarantine** stores rejection details for investigation. **S3 Processed** stores clean Parquet, which preserves schema, compresses well, and reduces Athena scan cost.
- **Glue Crawler and Data Catalog** discover and publish the Parquet schema. **Athena** queries it with SQL without a database server.
- **CloudWatch** stores Lambda/Glue logs and alerts on job failure or a high rejection rate.

## Daily Data Flow

1. Five systems upload daily files to a date-based S3 Raw prefix.
2. The S3 event invokes Lambda, which starts Glue with the input path and run date.
3. Glue parses JSONL, validates fields, applies documented Fix/Drop/Keep rules, and transforms valid records.
4. Rejections go to S3 Quarantine; clean Parquet goes to a date-based S3 Processed prefix.
5. The Crawler updates the Catalog, Athena runs the reports, and CloudWatch reports failures or excessive rejections.

## IAM and Security

Enable S3 Block Public Access, TLS, and encryption at rest; use SSE-KMS when customer-managed keys are required. Apply least privilege: Lambda may inspect object metadata and start only the named Glue job; Glue may read Raw and write Processed, Quarantine, and job logs; Athena users may read Processed and write query results but cannot modify Raw. Configure separate lifecycle policies after retention requirements are confirmed.

## Uncertainties

- The assessment does not specify whether the pipeline must run immediately when a new file arrives or wait for all files and run once per day.
- If immediate processing is required, Lambda can start Glue. For one daily batch, Lambda can be removed and EventBridge can start Glue on a schedule.
- The number and size of files, pipeline run frequency, and report query frequency are unknown, so the final service choice and cost cannot yet be estimated.
- The required retention periods for Raw, Quarantine, and Processed data in S3 are not specified.
- Alert rules are not specified. Examples to confirm include pipeline failure, missing input files, or an excessive rejected-record rate.
