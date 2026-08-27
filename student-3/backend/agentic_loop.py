import os
import requests

from app import (
    AI_MODEL,
    AI_SERVICE_URL,
    build_resource_context,
    fetch_current_resources,
    select_candidate_resources
)


# ---------------------------------------------------------
# Agentic Loop Configuration
# ---------------------------------------------------------

MAX_ITERATIONS = 3


# ---------------------------------------------------------
# Helper: Call Ollama using selected candidates
# ---------------------------------------------------------

def generate_recommendation(
    question,
    candidates
):
    """
    Ask the shared Ollama service to recommend
    from the already filtered candidate resources.
    """

    resource_context = build_resource_context(
        candidates
    )

    prompt = f"""
You are Campus AI, a university campus resource
recommendation assistant.

You may ONLY recommend resources from the
candidate resource list below.

Do not invent:
- resource names
- locations
- opening hours
- capacities
- availability
- facilities

Use only the information provided.

Recommend the best 1 to 3 options.

For each recommendation:
- use the exact resource name
- explain briefly why it matches the user's need
- mention useful facts such as availability,
  capacity, location or opening hours

Keep the response concise.

CANDIDATE RESOURCES:

{resource_context}

USER REQUEST:

{question}

Give the recommendation now.
"""

    response = requests.post(
        AI_SERVICE_URL,
        json={
            "model": AI_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2
            }
        },
        timeout=60
    )

    response.raise_for_status()

    data = response.json()

    return (
        data.get(
            "response",
            ""
        ).strip()
    )


# ---------------------------------------------------------
# Helper: Display Candidate Resources
# ---------------------------------------------------------

def print_candidates(candidates):

    print(
        f"\nCandidate resources: "
        f"{len(candidates)}"
    )

    for resource in candidates:

        print(
            f"- ID {resource.get('resource_id')}: "
            f"{resource.get('resource_name')} "
            f"[{resource.get('resource_type')}] "
            f"- {resource.get('availability_status')}"
        )


# ---------------------------------------------------------
# PLAN
# ---------------------------------------------------------

def plan(question):

    print("\n" + "=" * 60)
    print("PLAN")
    print("=" * 60)

    print(
        "Goal: Recommend a suitable campus resource "
        "based on the user's current requirements."
    )

    print(
        f"User requirement: {question}"
    )

    print(
        "Strategy:"
    )

    print(
        "1. Retrieve current campus resource records."
    )

    print(
        "2. Filter relevant candidate resources."
    )

    print(
        "3. Ask Qwen to explain the best recommendation."
    )

    print(
        "4. Request human review."
    )

    print(
        "5. Adapt if the recommendation is partially "
        "accepted or rejected."
    )


# ---------------------------------------------------------
# ACT
# ---------------------------------------------------------

def act(
    question,
    excluded_resource_ids
):

    print("\n" + "=" * 60)
    print("ACT")
    print("=" * 60)

    print(
        "Retrieving current campus resource records..."
    )

    resources = fetch_current_resources()

    print(
        f"Retrieved {len(resources)} resources."
    )


    # Use the grounded filtering logic already
    # implemented in app.py.
    candidates = select_candidate_resources(
        resources,
        question
    )


    # Remove resources rejected in earlier iterations.
    candidates = [
        resource
        for resource in candidates
        if (
            resource.get("resource_id")
            not in excluded_resource_ids
        )
    ]


    print_candidates(
        candidates
    )


    if not candidates:

        return {
            "resources": resources,
            "candidates": [],
            "recommendation": (
                "No suitable candidate resources remain "
                "after applying human feedback."
            )
        }


    print(
        "\nSending grounded candidates "
        "to shared Ollama..."
    )


    recommendation = generate_recommendation(
        question,
        candidates
    )


    return {
        "resources": resources,
        "candidates": candidates,
        "recommendation": recommendation
    }


# ---------------------------------------------------------
# OBSERVE
# ---------------------------------------------------------

def observe(result):

    print("\n" + "=" * 60)
    print("OBSERVE")
    print("=" * 60)

    print(
        f"Candidate count: "
        f"{len(result['candidates'])}"
    )

    print(
        f"AI model: {AI_MODEL}"
    )

    print("\nAI Recommendation:\n")

    print(
        result["recommendation"]
    )


# ---------------------------------------------------------
# HUMAN REVIEW
# ---------------------------------------------------------

def human_review():

    print("\n" + "=" * 60)
    print("HUMAN REVIEW")
    print("=" * 60)

    print(
        "1 - Accept recommendation"
    )

    print(
        "2 - Partially Accept / Refine"
    )

    print(
        "3 - Reject recommendation"
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


# ---------------------------------------------------------
# ADAPT
# ---------------------------------------------------------

def adapt(
    decision,
    question,
    candidates,
    excluded_resource_ids
):

    print("\n" + "=" * 60)
    print("ADAPT")
    print("=" * 60)


    # -----------------------------------------------------
    # ACCEPT
    # -----------------------------------------------------

    if decision == "1":

        print(
            "Human decision: ACCEPT"
        )

        print(
            "Recommendation accepted."
        )

        return {
            "complete": True,
            "question": question,
            "excluded_resource_ids":
                excluded_resource_ids
        }


    # -----------------------------------------------------
    # PARTIAL ACCEPT
    # -----------------------------------------------------

    if decision == "2":

        print(
            "Human decision: PARTIALLY ACCEPT"
        )

        refinement = input(
            "\nWhat should be improved or refined?\n> "
        ).strip()


        if refinement:

            new_question = (
                f"{question}. "
                f"Additional requirement: {refinement}"
            )

        else:

            new_question = question


        print(
            "\nThe requirement has been refined."
        )

        print(
            f"Updated requirement: {new_question}"
        )


        return {
            "complete": False,
            "question": new_question,
            "excluded_resource_ids":
                excluded_resource_ids
        }


    # -----------------------------------------------------
    # REJECT
    # -----------------------------------------------------

    print(
        "Human decision: REJECT"
    )


    if not candidates:

        print(
            "There are no candidate resources "
            "available to exclude."
        )

        return {
            "complete": True,
            "question": question,
            "excluded_resource_ids":
                excluded_resource_ids
        }


    print(
        "\nCurrent candidate resources:"
    )


    for resource in candidates:

        print(
            f"{resource.get('resource_id')} - "
            f"{resource.get('resource_name')}"
        )


    rejected_input = input(
        "\nEnter the resource ID to exclude "
        "from the next recommendation: "
    ).strip()


    try:

        rejected_id = int(
            rejected_input
        )


        valid_ids = [
            resource.get("resource_id")
            for resource in candidates
        ]


        if rejected_id in valid_ids:

            excluded_resource_ids.add(
                rejected_id
            )

            print(
                f"Resource ID {rejected_id} "
                f"will be excluded."
            )

        else:

            print(
                "That resource ID was not "
                "in the candidate list."
            )


    except ValueError:

        print(
            "Invalid resource ID. "
            "No resource was excluded."
        )


    return {
        "complete": False,
        "question": question,
        "excluded_resource_ids":
            excluded_resource_ids
    }


# ---------------------------------------------------------
# Main Agentic Loop
# ---------------------------------------------------------

def run_agentic_loop():

    print("\n")
    print("=" * 60)
    print("STUDENT 3 CAMPUS RESOURCE AGENTIC AI")
    print("=" * 60)

    print(
        f"Model: {AI_MODEL}"
    )

    print(
        "Workflow: "
        "PLAN → ACT → OBSERVE → "
        "HUMAN REVIEW → ADAPT"
    )


    question = input(
        "\nWhat campus resource do you need?\n> "
    ).strip()


    if not question:

        print(
            "A campus resource requirement is required."
        )

        return


    excluded_resource_ids = set()


    for iteration in range(
        1,
        MAX_ITERATIONS + 1
    ):

        print("\n")
        print("#" * 60)

        print(
            f"AGENTIC LOOP ITERATION {iteration}"
        )

        print("#" * 60)


        # PLAN
        plan(
            question
        )


        try:

            # ACT
            result = act(
                question,
                excluded_resource_ids
            )


            # OBSERVE
            observe(
                result
            )


            if not result["candidates"]:

                print(
                    "\nNo candidates remain."
                )

                print(
                    "LOOP COMPLETE"
                )

                return


            # HUMAN REVIEW
            decision = human_review()


            # ADAPT
            adaptation = adapt(
                decision,
                question,
                result["candidates"],
                excluded_resource_ids
            )


            question = adaptation[
                "question"
            ]

            excluded_resource_ids = adaptation[
                "excluded_resource_ids"
            ]


            if adaptation["complete"]:

                print("\n" + "=" * 60)

                print(
                    "LOOP COMPLETE"
                )

                print("=" * 60)

                return


        except requests.Timeout as error:

            print(
                "\nERROR: AI request timed out."
            )

            print(
                str(error)
            )

            return


        except requests.RequestException as error:

            print(
                "\nERROR: Backend service unavailable."
            )

            print(
                str(error)
            )

            return


        except Exception as error:

            print(
                "\nERROR: Unexpected agentic loop failure."
            )

            print(
                str(error)
            )

            return


    print("\n" + "=" * 60)

    print(
        "MAXIMUM ITERATIONS REACHED"
    )

    print(
        "The loop stopped after "
        f"{MAX_ITERATIONS} iterations."
    )

    print("=" * 60)


# ---------------------------------------------------------
# Program Entry
# ---------------------------------------------------------

if __name__ == "__main__":
    run_agentic_loop()