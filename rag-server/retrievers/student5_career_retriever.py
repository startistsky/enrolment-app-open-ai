import os
import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


BASE_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_DIR = (
BASE_DIR
/ "knowledge"
/ "career-knowledge"
)

CHROMA_DIR = BASE_DIR / "chroma"

COLLECTION_NAME = "student5_career_knowledge"

EMBEDDING_MODEL = os.getenv(
"RAG_EMBEDDING_MODEL",
"all-MiniLM-L6-v2",
)

# configuration
print("========================================")
print("CAREER RAG CONFIGURATION")
print("========================================")
print(f"BASE_DIR: {BASE_DIR}")
print(f"KNOWLEDGE_DIR: {KNOWLEDGE_DIR}")
print(f"KNOWLEDGE_EXISTS: {KNOWLEDGE_DIR.exists()}")

knowledge_files = sorted(
KNOWLEDGE_DIR.glob("*.txt")
) if KNOWLEDGE_DIR.exists() else []

print(
"KNOWLEDGE_FILES:",
[file.name for file in knowledge_files],
)

print(f"CHROMA_DIR: {CHROMA_DIR}")
print(f"COLLECTION: {COLLECTION_NAME}")
print(f"EMBEDDING_MODEL: {EMBEDDING_MODEL}")
print("========================================")

# Chromadb
_client = chromadb.PersistentClient(
path=str(CHROMA_DIR)
)

_embedding_function = (
embedding_functions.SentenceTransformerEmbeddingFunction(
model_name=EMBEDDING_MODEL,
)
)

_collection = _client.get_or_create_collection(
name=COLLECTION_NAME,
embedding_function=_embedding_function,
)

# chunking
def chunk_text(
text,
chunk_size=800,
overlap=100,
):
    """
    Split knowledge text into overlapping word chunks.
    """

    text = str(text or "").strip()

    if not text:
        return []

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = min(
            start + chunk_size,
            len(words),
        )

        chunk = " ".join(
            words[start:end]
        ).strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = max(
            end - overlap,
            start + 1,
        )

    return chunks

# load knwoledge
def load_knowledge():
    """
    Load all career knowledge .txt files.
    """

    documents = []

    if not KNOWLEDGE_DIR.exists():

        print(
            "CAREER RAG ERROR: "
            "Knowledge directory does not exist:"
        )

        print(
            KNOWLEDGE_DIR
        )

        return documents

    files = sorted(
        KNOWLEDGE_DIR.glob("*.txt")
    )

    if not files:

        print(
            "CAREER RAG ERROR: "
            "No .txt knowledge files found:"
        )

        print(
            KNOWLEDGE_DIR
        )

        return documents

    print(
        f"CAREER RAG: Found "
        f"{len(files)} knowledge files."
    )

    for file_path in files:

        try:

            text = file_path.read_text(
                encoding="utf-8"
            )

        except OSError as error:

            print(
                f"CAREER RAG: Could not read "
                f"{file_path.name}: {error}"
            )

            continue

        if not text.strip():

            print(
                f"CAREER RAG: "
                f"{file_path.name} is empty."
            )

            continue

        chunks = chunk_text(text)

        print(
            f"CAREER RAG: "
            f"{file_path.name} -> "
            f"{len(chunks)} chunks"
        )

        for index, chunk in enumerate(chunks):

            documents.append(
                {
                    "id": (
                        f"{file_path.stem}-"
                        f"{index}-"
                        f"{uuid.uuid4().hex[:8]}"
                    ),

                    "text": chunk,

                    "source": file_path.name,

                    "chunk": index,
                }
            )

    return documents

# index knowledge
def index_knowledge():
    """
    Rebuild the Chroma career collection from the
    current knowledge files.
    """

    print(
        "CAREER RAG: Starting knowledge indexing..."
    )

    documents = load_knowledge()

    if not documents:

        return {
            "success": False,
            "indexed": 0,
            "collection": COLLECTION_NAME,
            "message": (
                "No career knowledge documents were found."
            ),
        }

    ids = [
        document["id"]
        for document in documents
    ]

    texts = [
        document["text"]
        for document in documents
    ]

    metadatas = [
        {
            "source": document["source"],
            "chunk": document["chunk"],
        }
        for document in documents
    ]

    try:

        # Remove existing documents.
        existing = _collection.get(
            include=[]
        )

        existing_ids = existing.get(
            "ids",
            [],
        )

        if existing_ids:

            print(
                f"CAREER RAG: "
                f"Deleting {len(existing_ids)} "
                f"old chunks..."
            )

            _collection.delete(
                ids=existing_ids
            )

        print(
            f"CAREER RAG: Adding "
            f"{len(documents)} chunks..."
        )

        _collection.add(
            ids=ids,
            documents=texts,
            metadatas=metadatas,
        )

    except Exception as error:

        print(
            "CAREER RAG ERROR: "
            "Indexing failed:"
        )

        print(
            repr(error)
        )

        return {
            "success": False,
            "indexed": 0,
            "collection": COLLECTION_NAME,
            "error": str(error),
        }

    count = _collection.count()

    print(
        f"CAREER RAG: Successfully indexed "
        f"{count} chunks."
    )

    return {
        "success": True,
        "indexed": count,
        "collection": COLLECTION_NAME,
        "message": "Career knowledge indexed successfully.",
    }


def ensure_knowledge_indexed():
    """
    Ensure the career knowledge exists in Chroma.

    If Chroma is empty, automatically index the knowledge files.
    """

    try:

        count = _collection.count()

    except Exception as error:

        print(
            "CAREER RAG ERROR: "
            "Could not inspect Chroma collection:"
        )

        print(
            repr(error)
        )

        return {
            "success": False,
            "error": str(error),
        }

    if count > 0:

        print(
            f"CAREER RAG: Collection contains "
            f"{count} chunks."
        )

        return {
            "success": True,
            "indexed": count,
            "already_indexed": True,
        }

    print(
        "CAREER RAG: Chroma collection is empty."
    )

    print(
        "CAREER RAG: Automatically indexing knowledge..."
    )

    result = index_knowledge()

    result["already_indexed"] = False

    return result

# retrieve
def retrieve(
query,
top_k=4,
):
    """
    Retrieve relevant career knowledge chunks.
    """

    query = str(
        query or ""
    ).strip()

    if not query:
        return []

    try:

        top_k = int(top_k)

    except (
        TypeError,
        ValueError,
    ):

        top_k = 4

    top_k = max(
        1,
        min(top_k, 10),
    )

    # IMPORTANT:
    #
    # Make sure knowledge has actually been indexed
    # before querying Chroma.
    #
    ensure_result = ensure_knowledge_indexed()

    if not ensure_result.get("success"):

        print(
            "CAREER RAG ERROR: "
            "Knowledge could not be indexed."
        )

        return []

    collection_count = _collection.count()

    if collection_count == 0:

        print(
            "CAREER RAG ERROR: "
            "Collection is still empty after indexing."
        )

        return []

    top_k = min(
        top_k,
        collection_count,
    )

    try:

        result = _collection.query(
            query_texts=[query],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

    except Exception as error:

        print(
            "CAREER RAG ERROR: "
            "Retrieval failed:"
        )

        print(
            repr(error)
        )

        return []

    documents = (
        result.get(
            "documents",
            [[]],
        )[0]
        or []
    )

    metadatas = (
        result.get(
            "metadatas",
            [[]],
        )[0]
        or []
    )

    distances = (
        result.get(
            "distances",
            [[]],
        )[0]
        or []
    )

    retrieved = []

    for index, document in enumerate(
        documents
    ):

        metadata = (
            metadatas[index]
            if index < len(metadatas)
            else {}
        )

        distance = (
            distances[index]
            if index < len(distances)
            else None
        )

        retrieved.append(
            {
                "text": document,

                "source": metadata.get(
                    "source",
                    "unknown",
                ),

                "chunk": metadata.get(
                    "chunk",
                    0,
                ),

                "distance": distance,
            }
        )

    return retrieved

# RAG context
def retrieve_context(
query,
top_k=4,
):
    """
    Return formatted RAG context.
    """

    results = retrieve(
        query,
        top_k,
    )

    if not results:

        return {
            "success": True,
            "context": "",
            "sources": [],
            "confidence": "low",
            "results": [],
        }

    context_parts = []

    sources = []

    for index, result in enumerate(
        results
    ):

        context_parts.append(
            (
                f"SOURCE {index + 1}: "
                f"{result['source']}\n\n"
                f"{result['text']}"
            )
        )

        source = result["source"]

        if source not in sources:

            sources.append(
                source
            )

    # Keep the existing simple confidence
    # calculation for compatibility.
    if len(results) >= 3:

        confidence = "high"

    else:

        confidence = "medium"

    return {
        "success": True,

        "context": "\n\n".join(
            context_parts
        ),

        "sources": sources,

        "confidence": confidence,

        "results": results,
    }


def retrieve_career_context(
query,
top_k=4,
):
    """
    Public Student 5 retriever interface.

    Called by:

        POST /retrieve/career
    """

    return retrieve_context(
        query,
        top_k,
    )

# RAG status
def rag_status():

    try:
        count = _collection.count()

        files = []

        if KNOWLEDGE_DIR.exists():

            files = [
                path.name
                for path in sorted(
                    KNOWLEDGE_DIR.glob("*.txt")
                )
            ]

        return {
            "success": True,
            "available": True,
            "collection": COLLECTION_NAME,
            "documents": count,
            "knowledge_directory": str(
                KNOWLEDGE_DIR
            ),
            "knowledge_files": files,
            "embedding_model": EMBEDDING_MODEL,
        }

    except Exception as error:

        return {
            "success": False,
            "available": False,
            "error": str(error),
        }

# init rag
def initialise_rag():

    print(
        "\n========================================"
    )

    print(
        "INITIALISING CAREER RAG"
    )

    print(
        "========================================"
    )

    result = ensure_knowledge_indexed()

    print(
        "RAG INITIALISATION RESULT:",
        result,
    )

    print(
        "RAG STATUS:",
        rag_status(),
    )

    print(
        "========================================\n"
    )

    return result


if __name__ == "main":
    initialise_rag()