import os

import chromadb
from chromadb.utils import embedding_functions


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

KNOWLEDGE_DIR = os.path.join(
    BASE_DIR,
    "knowledge",
    "resource-knowledge",
)

CHROMA_DIR = os.path.join(
    BASE_DIR,
    "chroma",
)

COLLECTION_NAME = "student3_resource_knowledge"

embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

collection = chroma_client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=embedding_function,
)


def load_resource_chunks():
    """Load the campus resource knowledge file and split it into resource chunks."""
    knowledge_file = os.path.join(
        KNOWLEDGE_DIR,
        "campus_resources.txt",
    )

    with open(knowledge_file, "r", encoding="utf-8") as file:
        content = file.read()

    blocks = content.split("\n\n")

    resource_chunks = [
        block.strip()
        for block in blocks
        if block.strip().startswith("Resource:")
    ]

    return resource_chunks


def index_knowledge():
    """Index campus resource chunks into the Student 3 ChromaDB collection."""
    chunks = load_resource_chunks()

    ids = []
    metadatas = []

    for index, chunk in enumerate(chunks, start=1):
        first_line = chunk.splitlines()[0]
        resource_name = first_line.replace("Resource:", "").strip()

        ids.append(f"student3_resource_{index}")

        metadatas.append({
            "resource_name": resource_name,
            "source": "campus_resources.txt",
        })

    collection.upsert(
        ids=ids,
        documents=chunks,
        metadatas=metadatas,
    )

    return {
        "status": "indexed",
        "collection": COLLECTION_NAME,
        "document_count": len(chunks),
    }


def get_confidence(distance):
    """Convert Chroma distance into a simple confidence label."""
    if distance <= 0.45:
        return "high"
    if distance <= 0.70:
        return "medium"
    return "low"


def retrieve_resource_context(query, top_k=3):
    """Retrieve the most relevant campus resources for a natural-language query."""
    if not isinstance(query, str) or not query.strip():
        return {
            "error": "query is required",
            "matches": [],
        }

    result = collection.query(
        query_texts=[query.strip()],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        distance_value = round(float(distance), 4)

        matches.append({
            "resource_name": metadata["resource_name"],
            "source": metadata["source"],
            "citation": (
                f"{metadata['source']}#"
                f"{metadata['resource_name'].replace(' ', '-')}"
            ),
            "distance": distance_value,
            "confidence": get_confidence(distance_value),
            "context": document,
        })

    return {
        "query": query.strip(),
        "top_k": top_k,
        "matches": matches,
    }


if __name__ == "__main__":
    index_result = index_knowledge()

    print("Index result:")
    print(index_result)

    print("\nSemantic retrieval test:")

    retrieval_result = retrieve_resource_context(
        "I need somewhere quiet to study."
    )

    for match in retrieval_result["matches"]:
        print(f"\nResource: {match['resource_name']}")
        print(f"Confidence: {match['confidence']}")
        print(f"Distance: {match['distance']}")
        print(f"Citation: {match['citation']}")