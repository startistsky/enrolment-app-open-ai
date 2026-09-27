"""Contract and synchronization regressions without network/model downloads."""
import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def retriever():
    path = Path(__file__).resolve().parents[1] / "retrievers/student1_course_retriever.py"
    spec = importlib.util.spec_from_file_location("course_retriever", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def setup(retriever, monkeypatch):
    record = {"course_code": "COMP3311", "course_name": "Database Systems",
              "course_id": 4, "lecturer": "Lecturer", "semester": "Autumn",
              "credit_points": 6, "course_description": "Relational databases"}
    collection = Mock()
    collection.get.return_value = {"ids": ["course:OLD"]}
    monkeypatch.setattr(retriever, "_fetch_courses", lambda: [record])
    monkeypatch.setattr(retriever, "_get_collection", lambda: collection)
    return record, collection


def test_sync_upserts_stable_ids_and_deletes_stale(retriever, setup):
    record, collection = setup
    result = retriever.sync_course_knowledge()
    assert result["records"]["course:COMP3311"] is record
    assert result["deleted"] == 1
    assert collection.upsert.call_args.kwargs["ids"] == ["course:COMP3311"]
    assert "Description: Relational databases" in collection.upsert.call_args.kwargs["documents"][0]
    collection.delete.assert_called_once_with(ids=["course:OLD"])


def test_empty_snapshot_removes_deleted_courses(retriever, setup, monkeypatch):
    _, collection = setup
    monkeypatch.setattr(retriever, "_fetch_courses", lambda: [])
    result = retriever.retrieve_course_context("databases")
    assert result["insufficient_context"]
    collection.delete.assert_called_once_with(ids=["course:OLD"])
    collection.query.assert_not_called()


@pytest.mark.parametrize("snapshot", [[None], [{"course_code": ""}],
                                      {"error": "Student 1 backend unavailable", "detail": "offline"}])
def test_bad_snapshot_never_mutates_index(retriever, setup, monkeypatch, snapshot):
    _, collection = setup
    monkeypatch.setattr(retriever, "_fetch_courses", lambda: snapshot)
    assert "error" in retriever.retrieve_course_context("databases")
    collection.upsert.assert_not_called()
    collection.delete.assert_not_called()


@pytest.mark.parametrize("distance,confidence", [(.2, "high"), (.4, "medium"), (.5, "low")])
def test_semantic_results_preserve_contract(retriever, setup, distance, confidence):
    record, collection = setup
    collection.query.return_value = {
        "ids": [["course:COMP3311"]], "distances": [[distance]],
        "metadatas": [[{"citation": "Course Management record: COMP3311"}]],
    }
    result = retriever.retrieve_course_context("relational data", True)
    match = result["matches"][0]
    assert match["context"] is record
    assert match["citation"] == "Course Management record: COMP3311"
    assert match["score"] == pytest.approx(1 - distance)
    assert match["confidence"] == confidence
    collection.query.assert_called_once_with(
        query_texts=["relational data"], n_results=1, include=["distances", "metadatas"],
    )


@pytest.mark.parametrize("distance", [.8, float("nan"), float("inf")])
def test_weak_or_invalid_similarity_is_rejected(retriever, setup, distance):
    _, collection = setup
    collection.query.return_value = {
        "ids": [["course:COMP3311"]], "distances": [[distance]],
        "metadatas": [[{"citation": "Course Management record: COMP3311"}]],
    }
    assert retriever.retrieve_course_context("unrelated")["matches"] == []


@pytest.mark.parametrize("operation", ["get", "upsert", "query"])
def test_chroma_failure_is_structured(retriever, setup, operation):
    _, collection = setup
    getattr(collection, operation).side_effect = RuntimeError("private internals")
    result = retriever.retrieve_course_context("databases")
    assert result["error"] == "Semantic retrieval unavailable"
    assert "private internals" not in str(result)
    if operation in ("get", "upsert"):
        collection.delete.assert_not_called()


def test_initialization_failure_is_structured(retriever, setup, monkeypatch):
    monkeypatch.setattr(retriever, "_get_collection", Mock(side_effect=RuntimeError))
    assert retriever.retrieve_course_context("databases")["error"] == "Semantic retrieval unavailable"


def test_blank_query_does_not_fetch(retriever, monkeypatch):
    fetch = Mock()
    monkeypatch.setattr(retriever, "_fetch_courses", fetch)
    assert retriever.retrieve_course_context("  ")["message"] == "A retrieval query is required"
    fetch.assert_not_called()


@pytest.mark.parametrize("query,confidence", [
    ("Tell me about COMP3311", "high"),
    ("  Tell me about (comp3311)?  ", "high"),
    ("COMP3311's lecturer", "high"),
    ("Tell me about COMP33110", "low"),
    ("Tell me about XCOMP3311", "low"),
    ("Tell me about COMP3311A", "low"),
    ("Tell me about COMP3311_extra", "low"),
    ("Tell me about COMP1001", "low"),
    ("What course covers databases?", "low"),
    ("Which subject is about relational data?", "low"),
])
def test_exact_code_only_boosts_same_chroma_record(retriever, setup, query, confidence):
    record, collection = setup
    record["course_code"] = " comp3311 "
    collection.query.return_value = {
        "ids": [["course:COMP3311"]], "distances": [[.5]],
        "metadatas": [[{"citation": "Course Management record: COMP3311"}]],
    }
    result = retriever.retrieve_course_context(query)
    match = result["matches"][0]
    assert match["confidence"] == confidence
    assert match["score"] == .5
    assert match["context"] is record
    collection.query.assert_called_once()


@pytest.mark.parametrize("ids,distances,metadatas", [
    ([], [], []),
    (["course:COMP3311"], [.8], [{"citation": "Course Management record: COMP3311"}]),
])
def test_exact_code_cannot_bypass_chroma_or_relevance_gate(
    retriever, setup, ids, distances, metadatas,
):
    _, collection = setup
    collection.query.return_value = {
        "ids": [ids], "distances": [distances], "metadatas": [metadatas],
    }
    result = retriever.retrieve_course_context("Tell me about COMP3311")
    assert result["matches"] == []
    assert result["insufficient_context"] is True
    collection.query.assert_called_once()
