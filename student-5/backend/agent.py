from ai_service import ask_smart
from agent_tools import (
    get_job_tool,
    analyse_job_tool,
    get_job_requirements_tool
)

def choose_action(message):
    """
    Decide which CareerConnect tool should be used.
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


def run_career_agent(job, message):

    if not job:
        return {
            "success": False,
            "error": "Job not found."
        }

    if not message or not message.strip():
        return {
            "success": False,
            "error": "Message is required."
        }

    try:

        action = choose_action(message)

        # -----------------------------
        # Tool execution
        # -----------------------------

        if action == "analyse_job":

            tool_result = analyse_job_tool(job)

        elif action == "requirements":

            tool_result = get_job_requirements_tool(job)

        else:

            tool_result = get_job_tool(
                job["id"]
            )

        # -----------------------------
        # Agent reasoning / response
        # -----------------------------

        prompt = f"""
You are CareerConnect's Career Agent.

The user asked:

{message}

Selected job:

{job}

Tool selected:

{action}

Tool result:

{tool_result}

Use the tool result to answer the user's question.

Rules:

- Stay focused on the selected job.
- Do not invent job requirements.
- Do not invent candidate information.
- Explain uncertainty when information is unavailable.
- Give practical career advice.
- Keep the response concise.

Return only the final response.
"""

        response = ask_smart(prompt)

        return {
            "success": True,
            "response": response,
            "action": action
        }

    except Exception as error:

        return {
            "success": False,
            "error": str(error)
        }