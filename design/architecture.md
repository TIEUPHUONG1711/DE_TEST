```text
                    5 Internal Systems
                            |
                            v
                     Daily Log Files
                            |
                            v
                      Amazon S3 Raw
                            |
                            v
                       AWS Lambda
              (Triggered when file arrives)
                            |
                            v
                      AWS Glue Job
              (Validate -> Clean -> Transform)
                            |
              +-------------+-------------+
              |                           |
              v                           v
     Amazon S3 Quarantine        Amazon S3 Processed
       (Invalid Records)              (Parquet)
                                          |
                                          v
                                  AWS Glue Crawler
                                          |
                                          v
                                AWS Glue Data Catalog
                                          |
                                          v
                                    Amazon Athena
                                          |
                                          v
                                        Reports
```

## Supporting Controls

The following controls apply across the architecture and are not part of the main data flow:

- **Amazon CloudWatch:** collects Lambda and Glue logs and alerts on job failures or unusually high rejection rates.
- **AWS IAM least privilege:** limits each component to only the required actions and S3 locations.
- **S3 security:** Block Public Access, encryption at rest, and TLS apply to Raw, Quarantine, Processed, and Athena query-result data.
