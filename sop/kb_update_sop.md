# Knowledge Base Update SOP

## Purpose and Scope

This SOP controls how new or revised customer documents are added to the local knowledge base (KB). It covers source documents, metadata, chunks, the SQLite FTS5 index, and evaluation results.

## Roles

- **Content Owner:** provides the document and confirms its owner, version, effective date, and whether it replaces an existing document.
- **Data Engineer:** validates the input, updates metadata, rebuilds the KB, and runs automated checks.
- **Reviewer:** verifies version decisions, reviews evaluation evidence, and approves or rejects publication.

The process runs whenever a new or revised document is received. The Content Owner should also review active documents quarterly for freshness.

## Update Procedure

1. **Receive and register the document**
   - Save the original Markdown file in `kb/docs/` without changing its business meaning.
   - Record the request date and Content Owner.

2. **Validate the document and metadata**
   - Confirm that the file is readable and has clear Markdown headings.
   - Confirm `document_id`, `document_family`, `title`, `version`, `effective_date`, `owner`, `status`, and `source_path` in `kb/document_metadata.json`.
   - Do not publish documents with missing or ambiguous ownership, version, or effective-date information; return them to the Content Owner for clarification.

3. **Resolve version changes**
   - For a new version, set the approved version to `active` and the replaced version to `superseded`.
   - Keep superseded documents for audit history, but exclude them from normal search results.
   - The Reviewer must confirm any conflicting or unclear replacement relationship.

4. **Rebuild the KB**
   - Run `python kb/build_kb.py`.
   - Check the reported document, active-chunk, and superseded-chunk counts.
   - Confirm that `kb/chunks.jsonl` and `kb/knowledge_base.db` are regenerated successfully.

5. **Test and evaluate**
   - Run `pytest -q` and require all existing tests to pass.
   - Add or update evaluation questions for the changed business rules, including expected answers, sources, and pass criteria.
   - Run `python kb/evaluate.py` and require all source-bearing questions to pass Retrieval Hit@3.
   - Manually review at least one changed rule, one version-sensitive case when applicable, and one out-of-scope case for groundedness and unsupported claims.

6. **Review and publish**
   - The Data Engineer provides the changed files, test results, retrieval results, and manual-review evidence.
   - The Reviewer approves publication only when metadata, version handling, tests, retrieval, and groundedness checks pass.
   - Commit the approved source documents, metadata, generated KB artifacts, evaluation files, and documentation together.

## Failure and Rollback

Do not publish if any required check fails. Fix the document, metadata, chunking, or retrieval logic and rerun the complete evaluation. If a published update causes a regression, restore the last approved Git revision of the documents, metadata, chunks, database, and evaluation results, then rebuild and verify the KB before republishing.
