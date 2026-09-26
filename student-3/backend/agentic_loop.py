import os
import subprocess
import sys
from pathlib import Path

import requests


# =========================================================
# STUDENT 3 AGENTIC AI DEVELOPMENT LOOP
# =========================================================

BACKEND_URL = os.getenv(
    "STUDENT3_BACKEND_URL",
    "http://localhost:8003"
)

MODEL_NAME = "qwen2.5:0.5b"

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MAX_ITERATIONS = 2


# =========================================================
# DISPLAY HELPERS
# =========================================================

def print_section(title):
    print("\n")
    print("=" * 70)
    print(title)
    print("=" * 70)


def print_subsection(title):
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)


# =========================================================
# PLAN
# =========================================================

def plan():
    print_section("PLAN")

    print(
        "Goal:"
    )

    print(
        "Validate that Student 3 Campus AI provides grounded "
        "campus resource recommendations using the current "
        "database records."
    )

    print("\nChecks:")

    print(
        "1. Verify Student 3 backend health."
    )

    print(
        "2. Verify campus resource data can be retrieved."
    )

    print(
        "3. Test printer recommendation filtering."
    )

    print(
        "4. Test available computer lab filtering."
    )

    print(
        "5. Test capacity-aware study room filtering."
    )

    print(
        "6. Validate MCP resource tools and structured results."
    )

    print(
        "7. Validate RAG semantic retrieval with citations "
        "and confidence."
    )

    print(
        "8. Review the MCP and RAG integration behaviour."
    )

    print(
        "9. Request human approval before accepting the result."
    )

    print(
        "10. Retest the implementation using automated tests."
    )


# =========================================================
# ACT
# =========================================================

def get_backend_health():
    response = requests.get(
        f"{BACKEND_URL}/health",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def get_resources():
    response = requests.get(
        f"{BACKEND_URL}/resources",
        timeout=5
    )

    response.raise_for_status()

    return response.json()


def request_recommendation(question):
    response = requests.post(
        f"{BACKEND_URL}/recommend",
        json={
            "question": question
        },
        timeout=60
    )

    response.raise_for_status()

    return response.json()

def request_rag_recommendation(question):
    """Request grounded resource context from the R1 RAG endpoint."""
    response = requests.post(
        f"{BACKEND_URL}/rag/recommend",
        json={
            "question": question
        },
        timeout=30
    )

    response.raise_for_status()

    return response.json()

def request_mcp_resource_count():
    """Request the resource count through the shared MCP integration."""
    response = requests.get(
        f"{BACKEND_URL}/api/mcp/resource-count",
        timeout=10
    )

    response.raise_for_status()

    return response.json()


def request_mcp_resource_by_type(resource_type):
    """Request resources by type through the shared MCP integration."""
    response = requests.get(
        f"{BACKEND_URL}/api/mcp/resource-by-type/{resource_type}",
        timeout=10
    )

    response.raise_for_status()

    return response.json()

def act():
    print_section("ACT")

    results = {}

    print(
        "Checking Student 3 backend..."
    )

    health = get_backend_health()

    results["health"] = health

    print(
        f"Backend status: {health.get('status')}"
    )


    print(
        "\nRetrieving current campus resources..."
    )

    resources = get_resources()

    results["resources"] = resources

    print(
        f"Retrieved {len(resources)} campus resources."
    )


    test_cases = [
        {
            "name": "Printer Recommendation",
            "question": "Where can I print something?",
            "expected_type": "Printer",
            "require_available": False,
            "capacity": None
        },
        {
            "name": "Available Computer Lab",
            "question": (
                "I need a computer lab that is "
                "currently available."
            ),
            "expected_type": "Computer Lab",
            "require_available": True,
            "capacity": None
        },
        {
            "name": "Study Room Capacity",
            "question": (
                "I need a study room for 6 people."
            ),
            "expected_type": "Study Room",
            "require_available": False,
            "capacity": 6
        }
    ]


    recommendation_results = []


    for test_case in test_cases:

        print_subsection(
            f"ACT TEST: {test_case['name']}"
        )

        print(
            f"Question: {test_case['question']}"
        )


        data = request_recommendation(
            test_case["question"]
        )


        candidates = data.get(
            "candidate_resources",
            []
        )


        print(
            f"Candidate count: {len(candidates)}"
        )


        for candidate in candidates:

            print(
                "- "
                f"{candidate.get('resource_name')} "
                f"[{candidate.get('resource_type')}] "
                f"- "
                f"{candidate.get('availability_status')}"
            )


        print(
            "\nAI Recommendation:"
        )

        print(
            data.get(
                "recommendation",
                "No recommendation returned."
            )
        )


        recommendation_results.append({
            "test_case": test_case,
            "response": data
        })


    results[
        "recommendation_results"
    ] = recommendation_results

        # =====================================================
    # R1 MCP TOOL VALIDATION
    # =====================================================

    print_subsection(
        "ACT TEST: R1 MCP Resource Tools"
    )

    print(
        "Calling MCP tool: resource_count"
    )

    mcp_count_data = request_mcp_resource_count()

    mcp_count_result = mcp_count_data.get(
        "result",
        {}
    )

    print(
        "MCP resource_count result: "
        f"{mcp_count_result.get('resource_count')}"
    )


    print(
        "\nCalling MCP tool: "
        "resource_by_type(resource_type='Printer')"
    )

    mcp_type_data = request_mcp_resource_by_type(
        "Printer"
    )

    mcp_type_result = mcp_type_data.get(
        "result",
        {}
    )

    print(
        "MCP Printer count: "
        f"{mcp_type_result.get('resource_count')}"
    )

    for resource in mcp_type_result.get(
        "resources",
        []
    ):
        print(
            "- "
            f"{resource.get('resource_name')} "
            f"[{resource.get('resource_type')}]"
        )

    results["mcp_count_result"] = (
        mcp_count_data
    )

    results["mcp_type_result"] = (
        mcp_type_data
    )
    
    print_subsection(
        "ACT TEST: R1 RAG Grounded Recommendation"
    )

    rag_question = (
        "I need somewhere quiet to study."
    )

    print(
        f"Question: {rag_question}"
    )

    rag_data = request_rag_recommendation(
        rag_question
    )

    rag_matches = rag_data.get(
        "matches",
        []
    )

    print(
        f"RAG match count: {len(rag_matches)}"
    )

    for match in rag_matches:
        print(
            "- "
            f"{match.get('resource_name')} "
            f"| confidence={match.get('confidence')} "
            f"| citation={match.get('citation')}"
        )

    results["rag_result"] = rag_data


    return results


# =========================================================
# OBSERVE
# =========================================================

def observe(results):
    print_section("OBSERVE")

    observations = []


    health_ok = (
        results.get(
            "health",
            {}
        ).get("status")
        == "ok"
    )


    observations.append({
        "check": "Backend health",
        "passed": health_ok,
        "details": (
            "Backend responded successfully."
            if health_ok
            else "Backend health check failed."
        )
    })


    resource_count = len(
        results.get(
            "resources",
            []
        )
    )


    observations.append({
        "check": "Resource retrieval",
        "passed": resource_count > 0,
        "details": (
            f"{resource_count} resources retrieved."
        )
    })


    for item in results[
        "recommendation_results"
    ]:

        test_case = item[
            "test_case"
        ]

        response = item[
            "response"
        ]

        candidates = response.get(
            "candidate_resources",
            []
        )


        correct_type = all(
            candidate.get(
                "resource_type"
            )
            == test_case[
                "expected_type"
            ]
            for candidate in candidates
        )


        has_candidates = (
            len(candidates) > 0
        )


        type_passed = (
            has_candidates
            and correct_type
        )


        observations.append({
            "check": (
                f"{test_case['name']} "
                "candidate type"
            ),
            "passed": type_passed,
            "details": (
                f"Expected: "
                f"{test_case['expected_type']}; "
                f"Candidates: "
                f"{len(candidates)}"
            )
        })


        if test_case[
            "require_available"
        ]:

            availability_ok = all(
                candidate.get(
                    "availability_status"
                )
                == "Available"
                for candidate
                in candidates
            )


            observations.append({
                "check": (
                    f"{test_case['name']} "
                    "availability"
                ),
                "passed": (
                    has_candidates
                    and availability_ok
                ),
                "details": (
                    "All candidates should "
                    "be Available."
                )
            })


        recommendation = str(
            response.get(
                "recommendation",
                ""
            )
        ).strip()


        observations.append({
            "check": (
                f"{test_case['name']} "
                "AI response"
            ),
            "passed": bool(
                recommendation
            ),
            "details": (
                "Recommendation returned."
                if recommendation
                else
                "Recommendation was empty."
            )
        })

        # =====================================================
    # R1 MCP EVIDENCE VALIDATION
    # =====================================================

    mcp_count_data = results.get(
        "mcp_count_result",
        {}
    )

    mcp_count_result = mcp_count_data.get(
        "result",
        {}
    )

    mcp_resource_count = mcp_count_result.get(
        "resource_count"
    )

    mcp_count_ok = (
        mcp_count_data.get("mode") == "mcp"
        and mcp_count_data.get("tool") == "resource_count"
        and mcp_resource_count == resource_count
    )

    observations.append({
        "check": "MCP resource_count tool",
        "passed": mcp_count_ok,
        "details": (
            f"MCP returned {mcp_resource_count} resources; "
            f"database returned {resource_count}."
        )
    })


    mcp_type_data = results.get(
        "mcp_type_result",
        {}
    )

    mcp_type_result = mcp_type_data.get(
        "result",
        {}
    )

    mcp_printers = mcp_type_result.get(
        "resources",
        []
    )

    mcp_printer_count = mcp_type_result.get(
        "resource_count"
    )

    mcp_type_ok = (
        mcp_type_data.get("mode") == "mcp"
        and mcp_type_data.get("tool") == "resource_by_type"
        and mcp_type_result.get("resource_type") == "Printer"
        and mcp_printer_count == 2
        and len(mcp_printers) == 2
        and all(
            resource.get("resource_type") == "Printer"
            for resource in mcp_printers
        )
    )

    observations.append({
        "check": "MCP resource_by_type tool",
        "passed": mcp_type_ok,
        "details": (
            f"MCP returned {mcp_printer_count} Printer resources "
            "with structured resource data."
        )
    })

    # =====================================================
    # R1 RAG EVIDENCE VALIDATION
    # =====================================================

    rag_result = results.get("rag_result", {})
    rag_matches = rag_result.get("matches", [])

    has_rag_matches = len(rag_matches) > 0

    observations.append({
        "check": "RAG semantic retrieval",
        "passed": has_rag_matches,
        "details": f"{len(rag_matches)} semantic matches returned."
    })

    citations_ok = (
        has_rag_matches
        and all(
            bool(str(match.get("citation", "")).strip())
            for match in rag_matches
        )
    )

    observations.append({
        "check": "RAG citations",
        "passed": citations_ok,
        "details": (
            "All retrieved resources include citations."
            if citations_ok
            else "One or more RAG citations are missing."
        )
    })

    confidence_ok = (
        has_rag_matches
        and all(
            match.get("confidence") in {"high", "medium", "low"}
            for match in rag_matches
        )
    )

    observations.append({
        "check": "RAG confidence",
        "passed": confidence_ok,
        "details": (
            "All retrieved resources include a valid confidence level."
            if confidence_ok
            else "One or more confidence values are invalid."
        )
    })

    top_resource_ok = (
        has_rag_matches
        and rag_matches[0].get("resource_name")
        == "Building 1 Quiet Study Area"
    )

    observations.append({
        "check": "RAG relevance",
        "passed": top_resource_ok,
        "details": (
            "Quiet-study query ranked Building 1 Quiet Study Area first."
            if top_resource_ok
            else "Expected quiet-study resource was not ranked first."
        )
    })


    for observation in observations:

        status = (
            "PASS"
            if observation[
                "passed"
            ]
            else
            "FAIL"
        )

        print(
            f"[{status}] "
            f"{observation['check']}"
        )

        print(
            f"       "
            f"{observation['details']}"
        )


    return observations


# =========================================================
# REVIEW
# =========================================================

def review(observations):
    print_section("REVIEW AGENT")

    print(
        f"AI Model: {MODEL_NAME}"
    )


    failed_checks = [
        observation
        for observation
        in observations
        if not observation[
            "passed"
        ]
    ]


    if not failed_checks:

        review_status = "PASS"

        review_message = (
            "The current implementation demonstrates "
            "integrated MCP and grounded RAG behaviour. "
            "The shared MCP resource tools return valid "
            "structured results through the Student 3 backend. "
            "Candidate filtering remains consistent with the "
            "current resource data, and RAG retrieval returns "
            "relevant semantic matches with citations and "
            "confidence evidence."
        )

        recommendation = (
            "Accept the current implementation "
            "and continue to automated regression testing."
        )

    else:

        review_status = "IMPROVEMENT REQUIRED"

        failed_names = [
            observation[
                "check"
            ]
            for observation
            in failed_checks
        ]

        review_message = (
            "One or more validation checks failed: "
            + ", ".join(
                failed_names
            )
            + "."
        )

        recommendation = (
            "Review candidate filtering, RAG retrieval, "
            "citations, confidence evidence and recommendation "
            "logic before accepting the implementation."
        )


    print(
        f"Review status: "
        f"{review_status}"
    )

    print(
        "\nAssessment:"
    )

    print(
        review_message
    )

    print(
        "\nRecommendation:"
    )

    print(
        recommendation
    )


    return {
        "status": review_status,
        "message": review_message,
        "recommendation": recommendation,
        "failed_checks": failed_checks
    }


# =========================================================
# HUMAN DECISION
# =========================================================

def human_decision():
    print_section("HUMAN DECISION")

    print(
        "1 - Accept"
    )

    print(
        "2 - Partially Accept"
    )

    print(
        "3 - Reject"
    )


    while True:

        decision = input(
            "\nDecision: "
        ).strip()


        if decision in [
            "1",
            "2",
            "3"
        ]:

            return decision


        print(
            "Please enter 1, 2 or 3."
        )


# =========================================================
# ADAPT
# =========================================================

def adapt(
    decision,
    review_result
):
    print_section("ADAPT")


    if decision == "1":

        print(
            "Human Review: ACCEPT"
        )

        print(
            "\nThe current recommendation implementation "
            "has been accepted."
        )

        print(
            "No additional code change is required "
            "for this iteration."
        )

        return {
            "accepted": True,
            "continue_loop": False,
            "feedback": None
        }


    if decision == "2":

        print(
            "Human Review: PARTIALLY ACCEPT"
        )

        feedback = input(
            "\nEnter improvement feedback:\n> "
        ).strip()


        print(
            "\nAdaptation required:"
        )

        print(
            feedback
            if feedback
            else
            "Further refinement is required."
        )


        return {
            "accepted": False,
            "continue_loop": True,
            "feedback": feedback
        }


    print(
        "Human Review: REJECT"
    )

    feedback = input(
        "\nExplain why the implementation "
        "was rejected:\n> "
    ).strip()


    print(
        "\nAdaptation required:"
    )

    if feedback:

        print(
            feedback
        )

    else:

        print(
            review_result[
                "recommendation"
            ]
        )


    return {
        "accepted": False,
        "continue_loop": True,
        "feedback": feedback
    }


# =========================================================
# RETEST
# =========================================================

def retest():
    print_section("RETEST")

    print(
        "Running Student 3 automated test suite..."
    )

    print(
        "\nCommand:"
    )

    print(
        "python -m pytest student-3/tests -v"
    )


    command = [
        sys.executable,
        "-m",
        "pytest",
        "student-3/tests",
        "-v"
    ]


    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        text=True
    )


    return (
        result.returncode == 0
    )


# =========================================================
# PASS / FAIL
# =========================================================

def final_result(
    human_accepted,
    tests_passed
):

    print_section("FINAL RESULT")


    if (
        human_accepted
        and tests_passed
    ):

        print(
            "PASS"
        )

        print(
            "\nAgentic AI development loop "
            "completed successfully."
        )

        print(
            "\nEvidence:"
        )

        print(
            "- PLAN completed"
        )

        print(
            "- ACT completed"
        )

        print(
            "- OBSERVE completed"
        )

        print(
            "- MCP resource_count tool validated"
        )

        print(
            "- MCP resource_by_type tool validated"
        )

        print(
            "- RAG semantic retrieval validated"
        )

        print(
            "- RAG citations and confidence validated"
        )

        print(
            "- REVIEW completed"
        )

        print(
            "- HUMAN DECISION: Accept"
        )

        print(
            "- ADAPT completed"
        )

        print(
            "- Automated RETEST passed"
        )

        return True


    print(
        "NOT YET PASSED"
    )

    if not human_accepted:

        print(
            "\nThe implementation has not "
            "been accepted by the human reviewer."
        )


    if not tests_passed:

        print(
            "\nOne or more automated tests failed."
        )


    return False


# =========================================================
# MAIN AGENTIC LOOP
# =========================================================

def run_agentic_loop():

    print("\n")
    print("#" * 70)
    print(
        "STUDENT 3 CAMPUS RESOURCE MANAGEMENT"
    )
    print(
        "AGENTIC AI DEVELOPMENT LOOP"
    )
    print("#" * 70)

    print(
        f"\nBackend: {BACKEND_URL}"
    )

    print(
        f"Model: {MODEL_NAME}"
    )

    print(
        "\nWorkflow:"
    )

    print(
        "PLAN → ACT → OBSERVE → REVIEW → "
        "HUMAN DECISION → ADAPT → RETEST → PASS"
    )


    for iteration in range(
        1,
        MAX_ITERATIONS + 1
    ):

        print("\n")
        print("#" * 70)

        print(
            f"ITERATION {iteration}"
        )

        print("#" * 70)


        try:

            # PLAN
            plan()


            # ACT
            results = act()


            # OBSERVE
            observations = observe(
                results
            )


            # REVIEW
            review_result = review(
                observations
            )


            # HUMAN DECISION
            decision = human_decision()


            # ADAPT
            adaptation = adapt(
                decision,
                review_result
            )


            # If accepted, perform regression tests.
            if adaptation[
                "accepted"
            ]:

                tests_passed = retest()


                final_result(
                    True,
                    tests_passed
                )

                return


            # If not accepted, allow another loop.
            if (
                adaptation[
                    "continue_loop"
                ]
                and iteration
                < MAX_ITERATIONS
            ):

                print_section(
                    "RE-PLAN"
                )

                print(
                    "Human feedback has requested "
                    "another validation iteration."
                )

                if adaptation[
                    "feedback"
                ]:

                    print(
                        "\nFeedback:"
                    )

                    print(
                        adaptation[
                            "feedback"
                        ]
                    )

                input(
                    "\nApply the required code change "
                    "if needed, then press Enter "
                    "to begin the next iteration..."
                )

                continue


            print_section(
                "LOOP STOPPED"
            )

            print(
                "Maximum agentic iterations reached."
            )

            return


        except requests.Timeout as error:

            print_section(
                "ERROR"
            )

            print(
                "A service request timed out."
            )

            print(
                error
            )

            return


        except requests.RequestException as error:

            print_section(
                "ERROR"
            )

            print(
                "Student 3 backend or AI service "
                "could not be reached."
            )

            print(
                error
            )

            return


        except Exception as error:

            print_section(
                "ERROR"
            )

            print(
                "Unexpected agentic loop error:"
            )

            print(
                error
            )

            return


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    run_agentic_loop()