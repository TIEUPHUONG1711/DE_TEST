import argparse
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

STOP_WORDS = {
      "ai",
      "bao",
      "có",
      "của",
      "được",
      "gì",
      "khi",
      "là",
      "nào",
      "nhiêu",
      "thế",
      "và",
  }

QUERY_EXPANSIONS = {
      "chuyển": ["escalation"],
      "chạy lại": ["rerun"],
  }


def build_fts_query(question: str) -> str:
      normalized_question = question.lower()
      tokens = re.findall(r"\w+", normalized_question)

      useful_tokens = [
          token
          for token in tokens
          if token not in STOP_WORDS
      ]

      for phrase, expanded_tokens in QUERY_EXPANSIONS.items():
          if phrase in normalized_question:
              useful_tokens.extend(expanded_tokens)

      useful_tokens = list(dict.fromkeys(useful_tokens))

      return " OR ".join(
          f'"{token}"'
          for token in useful_tokens
      )


def search_kb(
      database_path: Path,
      question: str,
      top_k: int = 3,
  ) -> list[dict[str, Any]]:
      fts_query = build_fts_query(question)

      if not fts_query:
          return []

      with sqlite3.connect(database_path) as connection:
          connection.row_factory = sqlite3.Row

          rows = connection.execute(
              """
              SELECT
                  chunk_id,
                  document_id,
                  title,
                  section,
                  version,
                  effective_date,
                  owner,
                  status,
                  source_path,
                  content,
                  bm25(chunks) AS score
              FROM chunks
              WHERE chunks MATCH ?
                AND status = 'active'
              ORDER BY score
              LIMIT ?
              """,
              (fts_query, top_k),
          ).fetchall()

      return [
          dict(row)
          for row in rows
      ]
      
def main() -> None:
      parser = argparse.ArgumentParser(
          description="Search the local knowledge base."
      )

      parser.add_argument(
          "question",
          help="Question or search text.",
      )

      parser.add_argument(
          "--top-k",
          type=int,
          default=3,
          help="Number of chunks to return.",
      )

      args = parser.parse_args()

      results = search_kb(
          database_path=Path("kb/knowledge_base.db"),
          question=args.question,
          top_k=args.top_k,
      )

      print(
          json.dumps(
              results,
              indent=2,
              ensure_ascii=False,
          )
      )      
      
if __name__ == "__main__":
      main()      
