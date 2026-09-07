from .ai_service import ask_smart, evaluate_agent_result, load_prompt
from .agent_tools import (
    get_job_tool,
    analyse_job_tool,
    get_job_requirements_tool
)

# agentic loop 

# Plan action
def choose_action(message):
    """
    PLAN 
    Decide which tool should be used based on the user's question.
    """

    text = message.lower()

    if any(
        word in text
        for word in [
            "ats",
            "keyword",
            "resume",
            "cv"
        ]
    ):
        return "analyse_job"

    if any(
        word in text
        for word in [
            "requirement",
            "qualification",
            "skill",
            "experience"
        ]
    ):
        return "requirements"

    return "job_information"

# Observe 
def observe_result(action,tool_result,message):
    """
    OBSERVE:
    Evaluate whether the tool result is sufficient for answering the user's question.
    """

    if tool_result is None:
        return {
            "success": False,
            "needs_adaptation": True,
            "reason": "Tool returned no result."
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
def adapt_action(action, observation, message):
    """
    ADAPT:
    Decide what the agent should do after observing the previous action's result.
    """
    if not observation["needs_adaptation"]:
        return action

    # If job analysis failed, fall back to requirements information.
    if action == "analyse_job":
        return "requirements"

    # If requirements were unavailable, fall back to general job information.
    if action == "requirements":
        return "job_information"

    return "job_information"

# Act
def execute_action(action,job):
    """
    ACT:
    Execute the tool selected during planning.
    """
    if action == "analyse_job":
        return analyse_job_tool(job)

    elif action == "requirements":
        return get_job_requirements_tool(job)

    else:
        return get_job_tool(
            job["id"])

# Final response 
def generate_response(message, job, action, tool_result, observation):
    """
    Generate the final response using the observed tool information.
    """

    prompt = load_prompt(
        "generate_response",
        message=message,
        job=job,
        action=action,
        tool_result=tool_result,
        observation=observation
    )
    return ask_smart(prompt)

# Human approval 
def create_pending_approval(response, planned_action, action, observation):
    """
    HUMAN REVIEW
    The agent has completed its AI reasoning but 
    must receive human approval before the workflow is considered complete.
    """

    return {
        "success": True,

        # Frontend uses this to render approval controls.
        "status": "awaiting_approval",

        # AI response shown to the student.
        "response": response,

        # Evidence of the agentic process.
        "planned_action": planned_action,
        "action": action,
        "observation": observation,

        "adapted": (planned_action != action),

        # Explicitly identify the next workflow step.
        "requires_human_approval": True
    }

# Orchestration main agent 
def run_career_agent(job, message):
    """Agentic AI Workflow
    PLAN -> ACT -> OBSERVE -> ADAPT (if required)
    -> ACT (again if required) -> OBSERVE again-> GENERATE RESPONSE -> HUMAN REVIEW
    The backend does not block while waiting for approval. 
    It returns an awaiting_approval state to the frontend. 
    """

    # validate job
    if not job:
        return {
            "success": False,
            "error": "Job not found."
        }

    # validate message
    if not message or not message.strip():
        return {
            "success": False,
            "error": "Message is required."
        }

    try: 
        # Plan action 
        planned_action = choose_action(message)
        action = planned_action

        # print for testing
        print("---PLAN---")
        print(f"User message: {message}")
        print(f"Planned action: {planned_action}")

        # Act
        tool_result = execute_action(action,job)
        print("---ACT---")
        print(f"Executing action: {action}")
        print(f"Tool result received: {tool_result}")

        # Observe
        observation = observe_result(action,tool_result,message)
        print("---OBSERVE---")
        print(f"Observation: {observation}")

        # Adapt 
        adapted_action = adapt_action(action,observation,message)
        print("---ADAPT---")
        print(f"Original action: {action}")
        print(f"Adapted action: {adapted_action}")

        # If adaptation selected a different action, execute it.
        if adapted_action != action:
            action = adapted_action
            print("---ADAPTATION---")
            print(f"Changing from {action} to {adapted_action}")

            # Act again 
            tool_result = execute_action(
                action,
                job
            )

            # Observe again
            observation = observe_result(
                action,
                tool_result,
                message
            )
            print("---SECOND OBSERVE---")
            print(f"Observation after adaptation: {observation}")

        # Generate response
        response = generate_response(
            message,
            job,
            action,
            tool_result,
            observation
        )
        print("---AI RESPONSE---")
        print(response)

        # Human review 
        result = create_pending_approval(response,planned_action,action,observation)
        print("---HUMAN REVIEW REQUIRED")

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


