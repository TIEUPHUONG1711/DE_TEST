# Task A — Review of the AI Response

I reviewed the response using AWS documentation, the supplied reading, the DataPack, and Accelerator practice. Each issue lists its verification source.

## 1. S3 Standard-IA as the cheapest default

**Problem:** Standard-IA is for long-lived, infrequently accessed data and has retrieval charges, a 30-day minimum duration, and a 128 KB minimum billable object size. Recent logs may be accessed frequently.

**Correction:** Choose storage from access and retention needs. Recent logs can start in S3 Standard, then move to IA/archive classes through lifecycle rules.

**Source:** Accelerator AWS practice; AWS, [*Understanding and managing Amazon S3 storage classes*](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html).

## 2. Glue polling production RDS every five minutes

**Problem:** Frequent production polling is not automatically a safe near-real-time pattern. It can add source load, reread data, and needs incremental-state and failure handling. It also conflicts with the daily-log use case.

**Correction:** For this assessment's daily log-file workload, prefer immutable raw files in S3 followed by batch processing. If low-latency database changes are actually required, assess CDC and its source impact instead of assuming polling.

**Source:** AWS, [*Creating tasks for ongoing replication using AWS DMS*](https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Task.CDC.html).

## 3. Parquet described as row-based

**Problem:** Parquet is columnar, not row-based. It supports column compression, selective reads, and block skipping—not simply fast writes.

**Correction:** Use Parquet when it fits the schema and query patterns, especially for Athena-style analytics.

**Source:** Accelerator data-pipeline practice; AWS, [*Use columnar storage formats — Amazon Athena*](https://docs.aws.amazon.com/athena/latest/ug/columnar-storage.html).

## 4. Lambda for a 30–45 minute transform

**Problem:** Lambda has a maximum execution time of 15 minutes, so it cannot run the described transform.

**Correction:** Use Glue for this batch ETL. ECS/Fargate can be evaluated for custom containers. Lambda may trigger the job, but should not run the long transform.

**Source:** Accelerator AWS practice; AWS, [*Configure Lambda function timeout*](https://docs.aws.amazon.com/lambda/latest/dg/configuration-timeout.html).

## 5. A fixed 4,000-token chunk is always best

**Problem:** No size is best for every document. Large chunks may mix topics; small chunks may lose context. The choice depends on structure, model limits, and evaluation.

**Correction:** For these SOPs and policies, chunk by meaningful headings, preserve metadata, and tune size/overlap using retrieval evaluation.

**Source:** `reading/01_chunking_basics.md`; Accelerator Knowledge Engineering practice; the POC produced 22 heading-based chunks from eight documents.

## 6. Overwrite the KB without versioning

**Problem:** The newest file may not be approved or effective, and overwriting destroys audit history. Conflicting `POL-01 v1/v2` in the DataPack demonstrates this risk.

**Correction:** Store approval/status, effective date, version, owner, and source. Retrieval should first require approved/active content, then respect its effective date and version; old content remains `superseded` for audit. Rebuild and rerun evaluation after updates.

**Source:** `reading/01_chunking_basics.md`; supplied `POL-01` versions; the POC version-trap evaluation.

## Overall Review

The response turns context-dependent decisions into universal rules and contains factual errors about Parquet and Lambda. It should not be used without checking workload requirements, document structure, version status, and evaluation results.
