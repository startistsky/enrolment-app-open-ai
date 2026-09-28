from .ai_service import (
    ask_smart,
    evaluate_agent_result,
    load_prompt
)

from .agent_tools import (
    get_job_tool,
    analyse_job_tool,
    get_job_requirements_tool,
    get_career_rag_tool
)


# Plan 
def choose_action(message):
    
    """
    Decide which tools to use
    """
    text = message.lower()

    # Career / interview guidance
    if any(
        word in text
        for word in [
            "how should",
            "how can",
            "advice",
            "guidance",
            "preparation",
            "interview",
            "interviewing",
            "apply",
            "application",
            "career",
            "what should i",
            "tips"
        ]
    ):
        return "career_rag"

    # Job / ATS analysis
    if any(
        word in text
        for word in [
            "ats",
            "keyword",
            "resume",
            "cv",
            "match",
            "matching"
        ]
    ):
        return "analyse_job"

    # Job requirements
    if any(
        word in text
        for word in [
            "requirement",
            "requirements",
            "qualification",
            "qualifications",
            "skill",
            "skills",
            "experience",
            "degree"
        ]
    ):
        return "requirements"

    return "job_information"


# Observe
def observe_result(action, tool_result, message):
    """
    Evaluate the result returned by the selected tool.
    """

    if tool_result is None:
        return {
            "success": False,
            "needs_adaptation": True,
            "reason": "Tool returned no result."
        }

    if action == "career_rag":

        if not isinstance(tool_result, dict):
            return {
                "success": False,
                "needs_adaptation": True,
                "reason": "Invalid RAG response."
            }

        if tool_result.get("success") is False:
            return {
                "success": False,
                "needs_adaptation": True,
                "reason": tool_result.get(
                    "error",
                    "RAG request failed."
                )
            }

        results = tool_result.get("results", [])

        if not results:
            return {
                "success": False,
                "needs_adaptation": True,
                "reason": "RAG returned no relevant career knowledge."
            }

        return {
            "success": True,
            "needs_adaptation": False,
            "reason": "Relevant career knowledge was retrieved.",
            "rag": {
                "sources": tool_result.get("sources", []),
                "confidence": tool_result.get("confidence", "low")
            }
        }

    evaluation = evaluate_agent_result(
        message,
        tool_result
    )

    return {
        "success": evaluation["adequate"],
        "needs_adaptation": not evaluation["adequate"],
        "reason": evaluation["reason"]
    }

# Adapt
def adapt_action(
    action,
    observation,
    message
):
    """
    ADAPT

    Decide what the agent should do after
    observing the previous tool result.
    """

    if not observation["needs_adaptation"]:

        return action


    # If RAG could not find useful knowledge,
    # fall back to the actual job information.
    if action == "career_rag":

        return "job_information"


    # If job analysis failed, use requirements.
    if action == "analyse_job":

        return "requirements"


    # If requirements were unavailable,
    # use general job information.
    if action == "requirements":

        return "job_information"


    return "job_information"


# Act 
def execute_action(
    action,
    job,
    message
):
    """
    ACT

    Execute the tool selected during planning.
    """

    if action == "analyse_job":

        return analyse_job_tool(
            job
        )


    elif action == "requirements":

        return get_job_requirements_tool(
            job
        )


    elif action == "career_rag":

        return get_career_rag_tool(
            message,
            job
        )


    else:

        return get_job_tool(
            job["id"]
        )


# Response generation
def generate_response(
    message,
    job,
    action,
    tool_result,
    observation
):
    """
    Generate the final response using:

        selected job
        user question
        tool result
        observation
        RAG evidence
    """

    prompt = load_prompt(
        "generate_response",

        message=message,

        job=job,

        action=action,

        tool_result=tool_result,

        observation=observation
    )

    return ask_smart(
        prompt
    )


# Human approval 
def create_pending_approval(
    response,
    planned_action,
    action,
    observation,
    tool_result
):
    """
    HUMAN REVIEW

    Return the AI response together with
    evidence about the agentic process.

    RAG source and confidence information
    are also returned to the frontend.
    """

    result = {

        "success": True,

        "status":
            "awaiting_approval",

        "response":
            response,

        "planned_action":
            planned_action,

        "action":
            action,

        "observation":
            observation,

        "adapted":
            (
                planned_action != action
            ),

        "requires_human_approval":
            True
    }


    # Include RAG evidence when RAG was used.
    if action == "career_rag":

        result["rag"] = {

            "sources":
                tool_result.get(
                    "sources",
                    []
                ),

            "confidence":
                tool_result.get(
                    "confidence",
                    "low"
                ),

            "results":
                tool_result.get(
                    "results",
                    []
                )
        }


    return result

# Agentic Loop 
def run_career_agent(
    job,
    message
):
    """
    Agentic AI Workflow

        PLAN
          ↓
        ACT
          ↓
        OBSERVE
          ↓
        ADAPT if required
          ↓
        ACT again
          ↓
        OBSERVE again
          ↓
        GENERATE RESPONSE
          ↓
        HUMAN REVIEW

    Supported tools:

        job_information
        requirements
        analyse_job
        career_rag
    """

    # Validate job
    if not job:

        return {
            "success": False,
            "error": "Job not found."
        }

    # Validate message
    if not message or not message.strip():

        return {
            "success": False,
            "error": "Message is required."
        }


    try:

        # plan 
        planned_action = choose_action(
            message
        )

        action = planned_action


        print(
            "---PLAN---"
        )

        print(
            f"User message: {message}"
        )

        print(
            f"Planned action: "
            f"{planned_action}"
        )


        # act 
        tool_result = execute_action(
            action,
            job,
            message
        )


        print(
            "---ACT---"
        )

        print(
            f"Executing action: {action}"
        )

        print(
            f"Tool result received: "
            f"{tool_result}"
        )


        # observe
        observation = observe_result(
            action,
            tool_result,
            message
        )


        print(
            "---OBSERVE---"
        )

        print(
            f"Observation: "
            f"{observation}"
        )


        # adapt
        adapted_action = adapt_action(
            action,
            observation,
            message
        )


        print(
            "---ADAPT---"
        )

        print(
            f"Original action: {action}"
        )

        print(
            f"Adapted action: "
            f"{adapted_action}"
        )

        # second act/observe
        if adapted_action != action:
            action = adapted_action

            print("---ADAPTATION---")

            print(
                f"Changing action to: "
                f"{action}"
            )

            tool_result = execute_action(
                action,
                job,
                message
            )


            print("---SECOND ACT---")

            print(
                f"Tool result: "
                f"{tool_result}"
            )


            observation = observe_result(
                action,
                tool_result,
                message
            )

            print("---SECOND OBSERVE---")

            print(
                f"Observation after adaptation: "
                f"{observation}"
            )


        # Generate reponse
        response = generate_response(
            message,
            job,
            action,
            tool_result,
            observation
        )


        print(
            "---AI RESPONSE---"
        )

        print(
            response
        )

        # Human review
        result = create_pending_approval(
            response,
            planned_action,
            action,
            observation,
            tool_result
        )


        print(
            "---HUMAN REVIEW REQUIRED---"
        )


        return result


    except Exception as error:

        print(
            "AGENT ERROR:",
            repr(error)
        )


        return {
            "success": False,
            "error": str(error)
        }
