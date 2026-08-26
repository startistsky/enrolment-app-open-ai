from ai_service import career_chat

# acts as orchestration layer
def run_career_agent(job, message):
    """
    Run the AI Career Agent for a selected job.

    The agent uses the selected job's information to provide
    personalised career and application guidance.
    """

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

        response = career_chat(
            message.strip(),
            job
        )

        return {
            "success": True,
            "response": response
        }

    except Exception as error:

        print(
            "CAREER AGENT ERROR:",
            repr(error)
        )

        return {
            "success": False,
            "error": str(error)
        }