import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "kb"))
from textwrap import dedent
from build_kb import (
      build_chunks,
      create_fts_index,
      split_markdown_sections,
  )
from search_kb import build_fts_query, search_kb

def test_split_markdown_by_h2_heading() -> None:
      markdown = dedent(
      """
      # Document title

      ## First section

      First content.

      ## Second section

      Second content.
      """
  )

      sections = split_markdown_sections(markdown)

      assert sections == [
          {
              "section": "First section",
              "content": "First content.",
          },
          {
              "section": "Second section",
              "content": "Second content.",
          },
      ]
      
def test_builds_expected_chunks_and_metadata() -> None:
      metadata_path = PROJECT_ROOT / "kb" / "document_metadata.json"

      chunks = build_chunks(metadata_path)

      assert len(chunks) == 22
      assert len({chunk["chunk_id"] for chunk in chunks}) == 22

      required_fields = {
          "chunk_id",
          "document_id",
          "document_family",
          "title",
          "section",
          "version",
          "effective_date",
          "owner",
          "status",
          "source_path",
          "content",
      }

      for chunk in chunks:
          assert required_fields.issubset(chunk)
          assert chunk["content"]
          
          
def test_backup_version_status() -> None:
      metadata_path = PROJECT_ROOT / "kb" / "document_metadata.json"

      chunks = build_chunks(metadata_path)

      v1_chunks = [
          chunk
          for chunk in chunks
          if chunk["document_id"] == "POL-01_v1"
      ]

      v2_chunks = [
          chunk
          for chunk in chunks
          if chunk["document_id"] == "POL-01_v2"
      ]

      assert len(v1_chunks) == 2
      assert len(v2_chunks) == 2

      assert all(
          chunk["status"] == "superseded"
          for chunk in v1_chunks
      )

      assert all(
          chunk["status"] == "active"
          for chunk in v2_chunks
      )                
      
      
def test_search_returns_active_backup_version(
      tmp_path: Path,
  ) -> None:
      metadata_path = (
          PROJECT_ROOT / "kb" / "document_metadata.json"
      )

      chunks = build_chunks(metadata_path)
      database_path = tmp_path / "knowledge_base.db"

      create_fts_index(chunks, database_path)

      results = search_kb(
          database_path=database_path,
          question="sao lưu giữ 30 ngày",
          top_k=3,
      )

      assert results
      assert results[0]["document_id"] == "POL-01_v2"

      assert all(
          result["status"] == "active"
          for result in results
      )

      assert all(
          result["document_id"] != "POL-01_v1"
          for result in results
      )
      
def test_search_returns_empty_for_stop_words_only() -> None:
      query = build_fts_query("là gì và thế nào")

      assert query == ""            