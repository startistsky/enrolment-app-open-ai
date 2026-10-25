import argparse
import asyncio
import json
import sys
import traceback
from pathlib import Path

import requests
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

# preserve R1 agentic loop 
# added release 2 review by using the release2_reviews.py
MCP_URL = "http://localhost:9001/mcp"
RAG_URL = "http://localhost:9101"

VALID_MODES = ["mcp", "rag", "all", "multi-agent-review", "testing-review", "cloud-review"]


def print_section(title):
    print()
    print("=" * 60)
    print(title)
    print("=" * 60)


def print_step(name, message):
    print(f"{name}: {message}")


async def validate_mcp():
    print_section("MCP VALIDATION MODE")

    print_step(
        "PLAN",
        "Validate the shared MCP server using a registered tool."
    )

    print_step(
        "ACT",
        f"Connect to {MCP_URL} and call resource_count."
    )

    try:
        async with streamable_http_client(MCP_URL) as (
            read_stream,
            write_stream,
        ):
            async with ClientSession(
                read_stream,
                write_stream,
            ) as session:
                await session.initialize()

                tools_response = await session.list_tools()
                tool_names = [
                    tool.name
                    for tool in tools_response.tools
                ]

                print_step(
                    "OBSERVE",
                    f"Available tools: {', '.join(tool_names)}"
                )

                if "resource_count" not in tool_names:
                    print_step(
                        "REVIEW",
                        "Required MCP tool resource_count was not found."
                    )
                    print_step(
                        "ADAPT",
                        "Check shared MCP tool registration."
                    )
                    print("MCP VALIDATION: FAIL")
                    return False

                result = await session.call_tool(
                    "resource_count",
                    arguments={},
                )

                if getattr(result, "isError", False):
                    print_step(
                        "REVIEW",
                        "resource_count returned an MCP error."
                    )
                    print_step(
                        "ADAPT",
                        "Check the MCP tool implementation."
                    )
                    print("MCP VALIDATION: FAIL")
                    return False

                content = getattr(result, "content", [])

                if not content:
                    print_step(
                        "REVIEW",
                        "resource_count returned no result."
                    )
                    print_step(
                        "ADAPT",
                        "Check the MCP tool implementation."
                    )
                    print("MCP VALIDATION: FAIL")
                    return False

                result_text = " ".join(
                    getattr(item, "text", str(item))
                    for item in content
                )

                print_step(
                    "OBSERVE",
                    f"resource_count result: {result_text}"
                )

                print_step(
                    "REVIEW",
                    "Shared MCP server returned a valid tool result."
                )

                print_step(
                    "ADAPT",
                    "No adaptation required."
                )

                print("MCP VALIDATION: PASS")
                return True

    except Exception as exc:
        print_step(
            "OBSERVE",
            f"MCP connection or tool call failed: {exc}"
        )
        traceback.print_exception(exc)

        print_step(
            "REVIEW",
            "Shared MCP validation could not complete."
        )
        print_step(
            "ADAPT",
            "Check the MCP client connection and retry."
        )
        print("MCP VALIDATION: FAIL")
        return False


def validate_rag():
    print_section("RAG VALIDATION MODE")

    endpoint = f"{RAG_URL}/retrieve/resource"

    payload = {
        "query": "quiet place to study",
        "top_k": 3,
    }

    print_step(
        "PLAN",
        "Validate shared RAG retrieval and grounding evidence."
    )

    print_step(
        "ACT",
        f"POST {endpoint} with query '{payload['query']}'."
    )

    try:
        response = requests.post(
            endpoint,
            json=payload,
            timeout=20,
        )

        print_step(
            "OBSERVE",
            f"HTTP status: {response.status_code}"
        )

        if response.status_code != 200:
            print_step(
                "REVIEW",
                "Shared RAG server returned a non-200 response."
            )
            print_step(
                "ADAPT",
                "Check the RAG server and retriever."
            )
            print("RAG VALIDATION: FAIL")
            return False

        result = response.json()

        print_step(
            "OBSERVE",
            "RAG response:"
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            )
        )

        result_text = json.dumps(
            result,
            ensure_ascii=False,
        ).lower()

        has_retrieval = any(
            key in result_text
            for key in [
                "match",
                "result",
                "context",
                "document",
                "resource",
            ]
        )

        has_citation = any(
            key in result_text
            for key in [
                "citation",
                "source",
            ]
        )

        has_confidence = "confidence" in result_text

        print_step(
            "OBSERVE",
            f"Retrieval evidence: {'PASS' if has_retrieval else 'FAIL'}"
        )

        print_step(
            "OBSERVE",
            f"Citation evidence: {'PASS' if has_citation else 'FAIL'}"
        )

        print_step(
            "OBSERVE",
            f"Confidence evidence: {'PASS' if has_confidence else 'FAIL'}"
        )

        if not (
            has_retrieval
            and has_citation
            and has_confidence
        ):
            print_step(
                "REVIEW",
                "RAG grounding evidence is incomplete."
            )
            print_step(
                "ADAPT",
                "Check retrieval output, citations and confidence."
            )
            print("RAG VALIDATION: FAIL")
            return False

        print_step(
            "REVIEW",
            "Shared RAG returned grounded retrieval evidence."
        )

        print_step(
            "ADAPT",
            "No adaptation required."
        )

        print("RAG VALIDATION: PASS")
        return True

    except requests.RequestException as exc:
        print_step(
            "OBSERVE",
            f"RAG request failed: {exc}"
        )
        print_step(
            "REVIEW",
            "Shared RAG validation could not complete."
        )
        print_step(
            "ADAPT",
            "Start the shared RAG server and retry."
        )
        print("RAG VALIDATION: FAIL")
        return False

    except ValueError as exc:
        print_step(
            "OBSERVE",
            f"Invalid JSON response: {exc}"
        )
        print_step(
            "REVIEW",
            "Shared RAG returned an invalid response."
        )
        print_step(
            "ADAPT",
            "Check the RAG response format."
        )
        print("RAG VALIDATION: FAIL")
        return False


def parse_args():
    parser = argparse.ArgumentParser(
        description="Smart Campus shared Release 1 validation and Release 2 evidence reviews."
    )

    parser.add_argument(
        "--mode",
        choices=VALID_MODES,
        default="all",
        help="Validation mode: mcp, rag, or all.",
    )

    parser.add_argument("--workflow-history", default="ai-services/multi-agent-server/workflow_history.jsonl")
    parser.add_argument("--coordination-audit", default="ai-services/multi-agent-server/coordination_audit.jsonl")
    parser.add_argument(
        "--student",
        choices=("all", "1", "2", "3", "4", "5"),
        help="Review scope for Multi-Agent, Testing, and Cloud reviews. Defaults to all for Multi-Agent and Student 1 for Testing/Cloud.",
    )
    parser.add_argument("--security-report")
    parser.add_argument("--ci-report")
    parser.add_argument("--cloud-report", default="reports/cloud-deployment-report.md")
    parser.add_argument("--log-dir", default="agentic-review-logs")
    parser.add_argument("--output")
    return parser.parse_args()


def testing_report_paths(student, report_dir="reports"):
    directory = Path(report_dir)
    combined_security = directory / "testing-review-security-report.json"
    combined_ci = directory / "testing-review-ci-report.json"
    if student == "all" or (combined_security.is_file() and combined_ci.is_file()):
        return str(combined_security), str(combined_ci)
    return (
        str(directory / f"student-{student}-pre-commit-security-report.md"),
        str(directory / f"student-{student}-post-commit-ci-report.md"),
    )

def main():
    args = parse_args()

    print_section("SMART CAMPUS SHARED AGENTIC LOOP")

    print(f"Validation mode: {args.mode}")
    print("Workflow: PLAN -> ACT -> OBSERVE -> REVIEW -> ADAPT")

    if args.mode in ("multi-agent-review", "testing-review", "cloud-review"):
        from release2_reviews import execute_review

        student = args.student or (
            "all" if args.mode == "multi-agent-review" else "1"
        )
        default_security_report, default_ci_report = testing_report_paths(student)
        security_report = args.security_report or default_security_report
        ci_report = args.ci_report or default_ci_report
        paths = {
            "multi-agent-review": (args.workflow_history, args.coordination_audit),
            "testing-review": (security_report, ci_report),
            "cloud-review": (args.cloud_report,),
        }
        try:
            result = execute_review(
                args.mode, paths[args.mode], args.log_dir, args.output,
                student=student,
            )
        except OSError:
            print("FAIL: Review log/output could not be written.")
            return 1
        return int(result["validation_status"] == "FAIL")

    results = []

    if args.mode in ["mcp", "all"]:
        results.append(
            asyncio.run(
                validate_mcp()
            )
        )

    if args.mode in ["rag", "all"]:
        results.append(
            validate_rag()
        )

    print_section("FINAL RESULT")

    if all(results):
        print("PASS")
        print("Shared agentic validation completed successfully.")
        return 0

    print("FAIL")
    print("One or more shared validation modes failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())