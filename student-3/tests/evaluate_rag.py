import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAG_SERVER_DIR = PROJECT_ROOT / "rag-server"

sys.path.insert(
    0,
    str(RAG_SERVER_DIR)
)


from retrievers.student3_resource_retriever import (
    index_knowledge,
    retrieve_resource_context,
)


BENCHMARKS = [
    {
        "name": "Quiet Study",
        "query": "I need somewhere quiet to study.",
        "relevant": {
            "Building 1 Quiet Study Area",
            "UTS Library",
        },
    },
    {
        "name": "Printing",
        "query": "Where can I print something?",
        "relevant": {
            "Building 2 Printer",
            "Building 11 Printer",
        },
    },
    {
        "name": "Computer Lab",
        "query": "I need a computer lab.",
        "relevant": {
            "Building 10 Computer Lab",
            "UTS Central Computer Lab",
        },
    },
    {
        "name": "Parking",
        "query": "Where can I park near campus?",
        "relevant": {
            "Thomas Street Parking",
        },
    },
    {
        "name": "Group Study",
        "query": "I need a place for group study.",
        "relevant": {
            "Building 11 Study Room 1",
            "Building 11 Study Room 2",
            "Building 6 Study Space",
        },
    },
]


def evaluate_query(benchmark):
    result = retrieve_resource_context(
        benchmark["query"],
        top_k=5,
    )

    retrieved = [
        match["resource_name"]
        for match in result["matches"]
    ]

    relevant = benchmark["relevant"]

    relevant_retrieved = [
        resource
        for resource in retrieved
        if resource in relevant
    ]

    precision_at_5 = (
        len(relevant_retrieved) / 5
    )

    recall_at_5 = (
        len(relevant_retrieved)
        / len(relevant)
    )

    return {
        "name": benchmark["name"],
        "query": benchmark["query"],
        "retrieved": retrieved,
        "relevant_retrieved": relevant_retrieved,
        "precision_at_5": precision_at_5,
        "recall_at_5": recall_at_5,
    }


def main():
    print("=" * 70)
    print("STUDENT 3 RAG RETRIEVAL EVALUATION")
    print("=" * 70)

    index_result = index_knowledge()

    print(
        f"\nIndexed documents: "
        f"{index_result['document_count']}"
    )

    results = []

    for benchmark in BENCHMARKS:
        result = evaluate_query(
            benchmark
        )

        results.append(result)

        print("\n" + "-" * 70)

        print(
            f"Benchmark: {result['name']}"
        )

        print(
            f"Query: {result['query']}"
        )

        print("\nTop 5:")

        for index, resource in enumerate(
            result["retrieved"],
            start=1,
        ):
            marker = (
                "RELEVANT"
                if resource
                in result["relevant_retrieved"]
                else "NOT RELEVANT"
            )

            print(
                f"{index}. {resource} "
                f"[{marker}]"
            )

        print(
            f"\nPrecision@5: "
            f"{result['precision_at_5']:.2f}"
        )

        print(
            f"Recall@5: "
            f"{result['recall_at_5']:.2f}"
        )

    average_precision = (
        sum(
            result["precision_at_5"]
            for result in results
        )
        / len(results)
    )

    average_recall = (
        sum(
            result["recall_at_5"]
            for result in results
        )
        / len(results)
    )

    print("\n" + "=" * 70)

    print("SUMMARY")

    print("=" * 70)

    print(
        f"Benchmarks: {len(results)}"
    )

    print(
        f"Average Precision@5: "
        f"{average_precision:.2f}"
    )

    print(
        f"Average Recall@5: "
        f"{average_recall:.2f}"
    )


if __name__ == "__main__":
    main()