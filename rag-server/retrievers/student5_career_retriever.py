import os
import uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions


# Configuration
BASE_DIR = Path(__file__).resolve().parents[1]

KNOWLEDGE_DIR = BASE_DIR / "knowledge" / "career-knowledge"

CHROMA_DIR = BASE_DIR / "chroma"

COLLECTION_NAME = "student5_career_knowledge"

EMBEDDING_MODEL = os.getenv(
    "RAG_EMBEDDING_MODEL",
    "all-MiniLM-L6-v2"
)


# ChromaDB vector store
_client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)


_embedding_function = (
    embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
)


_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=_embedding_function
)

# Chunking
def chunk_text(text, chunk_size=800, overlap=100):
    """
    Split knowledge text into overlapping chunks.
    """
    text = str(text).strip()

    if not text:
        return []

    words = text.split()

    chunks = []

    start = 0

    while start < len(words):

        end = min(
            start + chunk_size,
            len(words)
        )

        chunk = " ".join(
            words[start:end]
        )

        if chunk:
            chunks.append(chunk)

        if end >= len(words):
            break

        start = max(
            end - overlap,
            start + 1
        )

    return chunks

# Load knowledge files
def load_knowledge():

    documents = []

    if not KNOWLEDGE_DIR.exists():
        return documents

    for file_path in sorted(
        KNOWLEDGE_DIR.glob("*.txt")
    ):

        try:

            text = file_path.read_text(
                encoding="utf-8"
            )

        except OSError:
            continue

        chunks = chunk_text(text)

        for index, chunk in enumerate(chunks):

            documents.append({
                "id": (
                    f"{file_path.stem}-"
                    f"{index}-"
                    f"{uuid.uuid4().hex[:8]}"
                ),

                "text": chunk,

                "source": file_path.name,

                "chunk": index
            })

    return documents

# Index knowledge
def index_knowledge():

    documents = load_knowledge()

    if not documents:
        return {
            "success": False,
            "indexed": 0,
            "message": "No knowledge files found."
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
            "chunk": document["chunk"]
        }
        for document in documents
    ]

    # Rebuild the collection so changes to knowledge files are reflected
    existing = _collection.get()

    if existing.get("ids"):

        _collection.delete(
            ids=existing["ids"]
        )

    _collection.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas
    )

    return {
        "success": True,
        "indexed": len(documents),
        "collection": COLLECTION_NAME
    }

# Retrieve
def retrieve(query, top_k=4):

    query = str(
        query or ""
    ).strip()

    if not query:
        return []

    try:

        top_k = int(top_k)

    except (
        TypeError,
        ValueError
    ):

        top_k = 4

    top_k = max(
        1,
        min(top_k, 10)
    )

    collection_count = _collection.count()

    if collection_count == 0:

        print(
            "CAREER RAG: Chroma collection is empty."
        )

        return []

    top_k = min(
        top_k,
        collection_count
    )

    result = _collection.query(
        query_texts=[query],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    documents = (
        result.get(
            "documents",
            [[]]
        )[0]
    )

    metadatas = (
        result.get(
            "metadatas",
            [[]]
        )[0]
    )

    distances = (
        result.get(
            "distances",
            [[]]
        )[0]
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

        retrieved.append({
            "text": document,

            "source": metadata.get(
                "source",
                "unknown"
            ),

            "chunk": metadata.get(
                "chunk",
                0
            ),

            "distance": distance
        })

    return retrieved
 

# RAG context
def retrieve_context(query, top_k=4):
    """
    Return formatted context suitable for Ollama.
    """

    results = retrieve(query, top_k)

    if not results:

        return {
            "context": "",
            "sources": [],
            "confidence": "low",
            "results": []
        }

    context_parts = []

    sources = []

    for index, result in enumerate(results):

        context_parts.append(
            f"""
SOURCE {index + 1}: {result["source"]}

{result["text"]}
""".strip()
        )

        if result["source"] not in sources:
            sources.append(
                result["source"]
            )

    # Simple confidence category
    if len(results) >= 3:
        confidence = "high"

    elif len(results) >= 1:
        confidence = "medium"

    else:
        confidence = "low"

    return {
        "context": "\n\n".join(
            context_parts
        ),

        "sources": sources,

        "confidence": confidence,

        "results": results
    }

# retriever carere context
def retrieve_career_context(query, top_k=4):
    """
    Public Student 5 retriever interface.

    This function is called by the shared
    RAG server:
        POST /retrieve/career
    """

    return retrieve_context(query, top_k)

# RAG health
def rag_status():
    try:
        count = _collection.count()

        return {
            "success": True,
            "available": True,
            "collection": COLLECTION_NAME,
            "documents": count,
            "embedding_model": EMBEDDING_MODEL
        }

    except Exception as error:
        return {
            "success": False,
            "available": False,
            "error": str(error)
        }


if __name__ == "__main__":

    print(
        "Indexing Student 5 "
        "career knowledge..."
    )

    result = index_knowledge()

    print(result)

    print(
        "RAG status:"
    )

    print(
        rag_status()
    )
