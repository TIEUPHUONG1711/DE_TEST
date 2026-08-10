import json
from pathlib import Path
from typing import Any
import sqlite3

def split_markdown_sections(text: str) -> list[dict[str, str]]:
      sections: list[dict[str, str]] = []
      current_heading: str | None = None
      current_lines: list[str] = []

      for line in text.splitlines():
          if line.startswith("## "):
              if current_heading is not None:
                  content = "\n".join(current_lines).strip()

                  if content:
                      sections.append(
                          {
                              "section": current_heading,
                              "content": content,
                          }
                      )

              current_heading = line.removeprefix("## ").strip()
              current_lines = []
              continue

          if current_heading is not None:
              current_lines.append(line)

      if current_heading is not None:
          content = "\n".join(current_lines).strip()

          if content:
              sections.append(
                  {
                      "section": current_heading,
                      "content": content,
                  }
              )

      return sections
  
  
def build_chunks(
      metadata_path: Path,
  ) -> list[dict[str, Any]]:
      metadata = json.loads(
          metadata_path.read_text(encoding="utf-8")
      )

      chunks: list[dict[str, Any]] = []

      for document in metadata:
          source_path = Path(document["source_path"])
          markdown_text = source_path.read_text(encoding="utf-8")

          sections = split_markdown_sections(markdown_text)

          for index, section in enumerate(sections, start=1):
              chunk = {
                  "chunk_id": (
                      f"{document['document_id']}_chunk_{index:03d}"
                  ),
                  "document_id": document["document_id"],
                  "document_family": document["document_family"],
                  "title": document["title"],
                  "section": section["section"],
                  "version": document["version"],
                  "effective_date": document["effective_date"],
                  "owner": document["owner"],
                  "status": document["status"],
                  "source_path": document["source_path"],
                  "content": section["content"],
              }

              chunks.append(chunk)

      return chunks  
  

def save_chunks(
      chunks: list[dict[str, Any]],
      output_path: Path,
  ) -> None:
      output_path.parent.mkdir(parents=True, exist_ok=True)

      with output_path.open("w", encoding="utf-8") as file:
          for chunk in chunks:
              file.write(
                  json.dumps(chunk, ensure_ascii=False) + "\n"
              )  
  
def main() -> None:
      metadata_path = Path("kb/document_metadata.json")
      output_path = Path("kb/chunks.jsonl")
      database_path = Path("kb/knowledge_base.db")

      chunks = build_chunks(metadata_path)

      save_chunks(chunks, output_path)
      create_fts_index(chunks, database_path)

      active_count = sum(
          chunk["status"] == "active"
          for chunk in chunks
      )

      superseded_count = sum(
          chunk["status"] == "superseded"
          for chunk in chunks
      )

      print("Documents: 8")
      print(f"Total chunks: {len(chunks)}")
      print(f"Active chunks: {active_count}")
      print(f"Superseded chunks: {superseded_count}")
      print(f"Chunks: {output_path}")
      print(f"Database: {database_path}")

def create_fts_index(
      chunks: list[dict[str, Any]],
      database_path: Path,
  ) -> None:
      database_path.parent.mkdir(parents=True, exist_ok=True)

      with sqlite3.connect(database_path) as connection:
          connection.execute("DROP TABLE IF EXISTS chunks")

          connection.execute(
              """
              CREATE VIRTUAL TABLE chunks USING fts5(
                  chunk_id UNINDEXED,
                  document_id UNINDEXED,
                  document_family UNINDEXED,
                  title,
                  section,
                  version UNINDEXED,
                  effective_date UNINDEXED,
                  owner UNINDEXED,
                  status UNINDEXED,
                  source_path UNINDEXED,
                  content,
                  tokenize = 'unicode61 remove_diacritics 2'
              )
              """
          )

          connection.executemany(
              """
              INSERT INTO chunks (
                  chunk_id,
                  document_id,
                  document_family,
                  title,
                  section,
                  version,
                  effective_date,
                  owner,
                  status,
                  source_path,
                  content
              )
              VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
              """,
              [
                  (
                      chunk["chunk_id"],
                      chunk["document_id"],
                      chunk["document_family"],
                      chunk["title"],
                      chunk["section"],
                      chunk["version"],
                      chunk["effective_date"],
                      chunk["owner"],
                      chunk["status"],
                      chunk["source_path"],
                      chunk["content"],
                  )
                  for chunk in chunks
              ],
          )

if __name__ == "__main__":
    
      main()  