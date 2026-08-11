# Task B — Verified Prompt Design

## 1. Final Prompt (v1)

```text
You are a deterministic application-log parser, not a chatbot.
Extract structured information from exactly one input message. Use only
information supported by the message and the rules below. Do not use external
knowledge or guess missing values.

INPUT MESSAGE
{{message}}

Return exactly one valid JSON object:
{"error_type":"string or null","component":"string or null",
 "parameters":{},"parse_status":"success | partial | failed",
 "raw_message":"exact input message"}

RULES
1. error_type: For a message beginning with "ERR", extract the stable error
   name after "ERR". Exclude IDs, components, paths, codes, durations and
   retries. Without a reliable ERR pattern, use null.
2. component: Extract only an explicitly named service, host, database,
   upstream system or module. IDs, paths, numbers and durations are not
   components. Do not repeat the component in parameters. Otherwise use null.
3. parameters: Extract explicit details only. Normalize "after <duration>" to
   "timeout", "txn" to "transaction_id", and an HTTP number to
   "status_code". Keep other explicit keys. JSON numbers remain numbers;
   values with units remain strings. Use {} when no parameters exist.
4. parse_status: success = the ERR pattern was parsed; partial = only part is
   reliable or the message is ambiguous; failed = no useful structure.
5. Preserve raw_message exactly. Return JSON only, without Markdown, comments
   or explanations. Never invent unsupported keys or values.
```

## 2. Five DataPack Test Cases

Expected outputs were defined before the LLM trial.

1. Input: `ERR ConnTimeout db-primary after 30s retry=3`
   ```json
   {"error_type":"ConnTimeout","component":"db-primary","parameters":{"timeout":"30s","retry":3},"parse_status":"success","raw_message":"ERR ConnTimeout db-primary after 30s retry=3"}
   ```
2. Input: `ERR HTTP 502 upstream=payment-api path=/checkout`
   ```json
   {"error_type":"HTTP","component":"payment-api","parameters":{"status_code":502,"path":"/checkout"},"parse_status":"success","raw_message":"ERR HTTP 502 upstream=payment-api path=/checkout"}
   ```
3. Input: `ERR PaymentDeclined txn=t811163 code=51`
   ```json
   {"error_type":"PaymentDeclined","component":null,"parameters":{"transaction_id":"t811163","code":51},"parse_status":"success","raw_message":"ERR PaymentDeclined txn=t811163 code=51"}
   ```
4. Input: `ERR SMTPConnRefused host=mail-gw`
   ```json
   {"error_type":"SMTPConnRefused","component":"mail-gw","parameters":{},"parse_status":"success","raw_message":"ERR SMTPConnRefused host=mail-gw"}
   ```
5. Ambiguous input: `Clock sync failed`
   ```json
   {"error_type":null,"component":null,"parameters":{},"parse_status":"partial","raw_message":"Clock sync failed"}
   ```

Case 5 passes only if no error label, service, code or NTP server is invented.

## 3. Evaluation on Approximately 3,000 Messages

Create a human-reviewed, stratified gold set of 200–300 common, rare, non-error and ambiguous messages; use a second reviewer for disputed labels. Run schema/safety validation on all outputs and score the gold set using:

- valid JSON and schema-compliance rates;
- exact-match accuracy for `error_type`, `component` and `parse_status`;
- parameter precision, recall and F1;
- hallucination, failure and human-review rates; and
- latency, token usage, estimated cost and repeatability.

Proposed POC gates are: valid JSON ≥99%, schema compliance ≥99%, field accuracy ≥95%, parameter F1 ≥95%, and hallucination rate = 0% on the gold set. Missing any gate fails the prompt. These are proposed POC targets, not agreed production SLAs.

For hallucination detection, compare values with the raw message and documented normalization map; unsupported values are flagged. Manually audit every flagged result and a random success sample. Human review is mandatory for invalid schema, `partial`/`failed`, unsupported values, missing critical fields, new patterns, or disagreement with a deterministic parser. After prompt changes, rerun the unchanged evaluation set.

## 4. Optional LLM Trial

Tool: ChatGPT; model/settings not displayed; run date: 2026-08-11; prompt: v1. Each case was run separately. JSON values below are unchanged; whitespace is normalized.

1. `{"error_type":"ConnTimeout","component":"db-primary","parameters":{"timeout":"30s","retry":3},"parse_status":"success","raw_message":"ERR ConnTimeout db-primary after 30s retry=3"}`
2. `{"error_type":"HTTP","component":"payment-api","parameters":{"status_code":502,"path":"/checkout"},"parse_status":"success","raw_message":"ERR HTTP 502 upstream=payment-api path=/checkout"}`
3. `{"error_type":"PaymentDeclined","component":null,"parameters":{"transaction_id":"t811163","code":51},"parse_status":"success","raw_message":"ERR PaymentDeclined txn=t811163 code=51"}`
4. `{"error_type":"SMTPConnRefused","component":"mail-gw","parameters":{},"parse_status":"success","raw_message":"ERR SMTPConnRefused host=mail-gw"}`
5. `{"error_type":null,"component":null,"parameters":{},"parse_status":"partial","raw_message":"Clock sync failed"}`

Result: 5/5 valid JSON, 5/5 schema compliant, 5/5 exact semantic matches, and zero observed hallucinations. Prompt v1 passed this small trial without revision; this does not replace the larger gold-set evaluation required before production use.
