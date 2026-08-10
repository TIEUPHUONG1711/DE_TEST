import json
from pathlib import Path
from typing import Any

from search_kb import search_kb

def evaluate_retrieval(
      questions: list[dict[str, Any]],
      database_path: Path,
      top_k: int = 3,
  ) -> dict[str, Any]:
      results: list[dict[str, Any]] = []
      evaluated_count = 0
      passed_count = 0

      for item in questions:
          retrieved_chunks = search_kb(
              database_path=database_path,
              question=item["question"],
              top_k=top_k,
          )

          retrieved_sources = {
              (
                  chunk["document_id"],
                  chunk["section"],
              )
              for chunk in retrieved_chunks
          }

          expected_sources = {
              (
                  source["document_id"],
                  source["section"],
              )
              for source in item["expected_sources"]
          }

          if expected_sources:
              retrieval_pass = expected_sources.issubset(
                  retrieved_sources
              )

              evaluated_count += 1

              if retrieval_pass:
                  passed_count += 1
          else:
              retrieval_pass = None

          results.append(
              {
                  "id": item["id"],
                  "category": item["category"],
                  "question": item["question"],
                  "expected_answer": item["expected_answer"],
                  "expected_sources": item["expected_sources"],
                  "pass_criteria": item["pass_criteria"],
                  "retrieval_pass": retrieval_pass,
                  "manual_answer_review_required": (
                      not expected_sources
                  ),
                  "retrieved_chunks": [
                      {
                          "rank": rank,
                          "document_id": chunk["document_id"],
                          "section": chunk["section"],
                          "status": chunk["status"],
                          "score": chunk["score"],
                      }
                      for rank, chunk in enumerate(
                          retrieved_chunks,
                          start=1,
                      )
                  ],
              }
          )

      hit_rate = (
          passed_count / evaluated_count
          if evaluated_count
          else 0
      )

      return {
          "summary": {
              "top_k": top_k,
              "evaluated_questions": evaluated_count,
              "passed_questions": passed_count,
              "retrieval_hit_rate": hit_rate,
          },
          "results": results,
      }
      
def main() -> None:
      questions_path = Path("kb/eval_questions.json")
      database_path = Path("kb/knowledge_base.db")
      output_path = Path("kb/eval_results.json")

      questions = json.loads(
          questions_path.read_text(encoding="utf-8")
      )

      evaluation = evaluate_retrieval(
          questions=questions,
          database_path=database_path,
          top_k=3,
      )

      output_path.write_text(
          json.dumps(
              evaluation,
              indent=2,
              ensure_ascii=False,
          ),
          encoding="utf-8",
      )

      print(
          json.dumps(
              evaluation["summary"],
              indent=2,
              ensure_ascii=False,
          )
      )

      print(f"Output: {output_path}")
      
      
if __name__ == "__main__":
      main()            