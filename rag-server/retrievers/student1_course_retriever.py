import math
import os
import re
from pathlib import Path
from pprint import pprint
from threading import RLock

import requests


STUDENT1_BACKEND_URL = os.getenv(
    "STUDENT1_BACKEND_URL", "http://localhost:8001",
).rstrip("/")
REQUEST_TIMEOUT_SECONDS = 5
MAX_TOP_K = 10
CHROMA_PATH = Path(__file__).resolve().parents[1] / "chroma-data"
COLLECTION_NAME = "student1-course-knowledge"
# Cosine similarity, not the former lexical score. Reject weak neighbours;
# .45 rejects weak secondary matches in the live course examples while retaining
# their intended matches. Accepted values < .55 are low, < .75 medium, else high.
# These conservative model-specific thresholds are heuristics, not probabilities.
MIN_SIMILARITY = 0.45
_SYNC_LOCK = RLock()
_collection = None


def _get_collection():
    """Lazy setup keeps initialization/model failures inside the error contract."""
    global _collection
    if _collection is None:
        import chromadb

        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            configuration={"hnsw": {"space": "cosine"}},
        )
        # Never interpret an existing index with a different metric as cosine.
        if collection.configuration["hnsw"]["space"] != "cosine":
            raise ValueError("Course collection must use cosine distance")
        _collection = collection
    return _collection


def _fetch_courses():
    """Return live courses, or structured backend error information."""
    try:
        response = requests.get(
            f"{STUDENT1_BACKEND_URL}/api/courses",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        courses = response.json()
    except (requests.RequestException, ValueError) as exc:
        return {"error": "Student 1 backend unavailable", "detail": str(exc)}
    if not isinstance(courses, list):
        return {
            "error": "Invalid response from Student 1 backend",
            "detail": "Expected the courses response to be a JSON list",
        }
    return courses


def _semantic_error():
    # Fixed detail avoids leaking stack traces, filesystem paths or internals.
    return {
        "error": "Semantic retrieval unavailable",
        "detail": "Unable to initialize, synchronize or query course knowledge.",
    }


def sync_course_knowledge():
    """Sync an authoritative API snapshot; return counts and original records.

    Invalid snapshots fail closed before any writes/deletes. A successful empty
    snapshot removes stale entries. Upserts precede deletion so embedding errors
    cannot delete the old index. The lock serializes sync/query in this process.
    """
    with _SYNC_LOCK:
        courses = _fetch_courses()
        if isinstance(courses, dict):
            return courses
        records = {}
        documents = {}
        metadata = {}
        fields = (
            ("Course Code", "course_code"), ("Course Name", "course_name"),
            ("Lecturer", "lecturer"), ("Semester", "semester"),
            ("Credit Points", "credit_points"),
            ("Description", "course_description"),
        )
        for course in courses:
            if (not isinstance(course, dict)
                    or any(not isinstance(course.get(key), str)
                           or not course[key].strip()
                           for key in ("course_code", "course_name"))
                    or any(isinstance(course.get(key), (dict, list))
                           for _, key in fields)):
                return {
                    "error": "Invalid response from Student 1 backend",
                    "detail": "Course snapshot contains an invalid record; index unchanged.",
                }
            code = course["course_code"].strip().upper()
            source_id = f"course:{code}"
            if source_id in records:
                return {
                    "error": "Invalid response from Student 1 backend",
                    "detail": "Course snapshot contains duplicate codes; index unchanged.",
                }
            records[source_id] = course
            documents[source_id] = "\n".join(
                f"{label}: {course.get(key) if course.get(key) is not None else ''}"
                for label, key in fields
            )
            metadata[source_id] = {
                "feature": "student1-course-management",
                "course_code": code,
                "source": "Course Management backend",
                "citation": f"Course Management record: {code}",
            }
        try:
            collection = _get_collection()
            existing_ids = set(collection.get(include=[])["ids"])
            ids = sorted(records)
            # Chroma's default local ONNX embedding function embeds documents
            # and query_texts with the same model; no separate transformer stack.
            for start in range(0, len(ids), 100):
                batch = ids[start:start + 100]
                collection.upsert(
                    ids=batch, documents=[documents[key] for key in batch],
                    metadatas=[metadata[key] for key in batch],
                )
            stale_ids = sorted(existing_ids - records.keys())
            for start in range(0, len(stale_ids), 100):
                collection.delete(ids=stale_ids[start:start + 100])
            return {"upserted": len(ids), "deleted": len(stale_ids), "records": records}
        except Exception:
            return _semantic_error()


def retrieve_course_context(query, top_k=3):
    """Retrieve live course context through Chroma cosine similarity search."""
    if not isinstance(query, str) or not query.strip():
        return {
            "query": "", "matches": [], "insufficient_context": True,
            "message": "A retrieval query is required",
        }
    original_query = query.strip()
    if isinstance(top_k, bool) or not isinstance(top_k, int) or top_k <= 0:
        top_k = 3
    top_k = min(top_k, MAX_TOP_K)
    empty = {"query": original_query, "matches": [], "insufficient_context": True}
    with _SYNC_LOCK:
        synced = sync_course_knowledge()
        if "error" in synced:
            return {**empty, **synced}
        records = synced["records"]
        matches = []
        try:
            if records:
                results = _get_collection().query(
                    query_texts=[original_query], n_results=min(top_k, len(records)),
                    include=["distances", "metadatas"],
                )
                for source_id, distance, metadata in zip(
                    results["ids"][0], results["distances"][0], results["metadatas"][0],
                ):
                    # Cosine distance = 1 - cosine similarity. Score is similarity
                    # on [0, 1], rounded only after threshold/confidence decisions.
                    similarity = 1.0 - float(distance)
                    if not math.isfinite(similarity) or similarity < MIN_SIMILARITY:
                        continue
                    if source_id not in records:
                        continue
                    similarity = min(1.0, similarity)
                    # Only boost confidence for an accepted Chroma result; this
                    # identifier check never retrieves, ranks or admits records.
                    code = records[source_id]["course_code"].strip().upper()
                    exact_code = re.search(
                        rf"(?<!\w){re.escape(code)}(?!\w)", original_query.upper(),
                    ) is not None
                    matches.append({
                        "source_id": source_id, "citation": metadata["citation"],
                        "confidence": ("high" if exact_code or similarity >= .75 else
                                       "medium" if similarity >= .55 else "low"),
                        "score": round(similarity, 6), "context": records[source_id],
                    })
        except Exception:
            return {**empty, **_semantic_error()}
    matches.sort(key=lambda match: (-match["score"], match["source_id"]))
    if not matches:
        return {
            **empty,
            "message": "Insufficient context: no relevant Course Management information was found.",
        }
    return {"query": original_query, "matches": matches, "insufficient_context": False}


if __name__ == "__main__":
    for example_query in (
        "Tell me about COMP1001",
        "Who teaches Machine Learning?",
        "What course covers databases?",
        "Which subject is about relational data?",
        "Tell me about quantum agriculture",
    ):
        print(f"\nQuery: {example_query}")
        pprint(retrieve_course_context(example_query), sort_dicts=False)
