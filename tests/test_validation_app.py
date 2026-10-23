import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from legal_agent_harness.validation_app import extract_graph, review_record, append_review

def test_extracts_directed_amendment_graph(tmp_path):
    data = "Федеральный закон. Статья 1252 дополнить с 2020-01-01".encode("utf-8")
    graph = extract_graph("act.txt", data, "Duma", "RU")
    assert graph["edges"][0]["from"].startswith("act:")
    assert graph["edges"][0]["to"] == "norm:1252"
    assert graph["records"][0]["predicate"] == "дополнена"
    assert graph["records"][0]["effective_from"] == "2020-01-01"

def test_review_is_bounded_and_append_only(tmp_path):
    graph = extract_graph("act.txt", b"Article 1 changed")
    review = review_record(graph, 10, "Checked", "session-1")
    assert review["expert_approved"] is True
    assert review["score"] == 10
    path = tmp_path / "reviews.jsonl"
    append_review(path, review)
    append_review(path, review)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2

def test_review_rejects_invalid_score():
    graph = extract_graph("act.txt", b"Article 1 changed")
    for score in (-1, 11):
        try:
            review_record(graph, score, "", "session-1")
        except ValueError:
            pass
        else:
            assert False