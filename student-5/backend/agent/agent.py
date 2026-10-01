from .ai_service import (
    ask_smart,
    evaluate_agent_result,
    load_prompt
)

from .agent_tools import (
    get_selected_job_mcp_tool,
    analyse_job_tool,
    get_job_requirements_tool,
    get_career_rag_tool
)


# ============================================================
# CONFIGURATION
# ============================================================

MAX_AGENT_STEPS = 4


# ============================================================
# PLAN
# ============================================================

def choose_action(message):
    """
    Decide which tool the agent should use first.

    Available actions:

        job_information
        requirements
        analyse_job
        career_rag
    """

    text = str(
        message or ""
    ).lower().strip()


    # --------------------------------------------------------
    # Job analysis / ATS
    # --------------------------------------------------------

    if any(
        word in text
        for word in [
            "ats",
            "keyword",
            "keywords",
            "resume",
            "cv",
            "match",
            "matching",
            "analyse",
            "analyze",
            "analysis"
        ]
    ):
        return "analyse_job"


    # --------------------------------------------------------
    # Requirements
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # Career guidance
    # --------------------------------------------------------

    if any(
        word in text
        for word in [
            "how should",
            "how can",
            "advice",
            "guidance",
            "preparation",
            "prepare",
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


    # --------------------------------------------------------
    # Default
    # --------------------------------------------------------

    return "job_information"


# ============================================================
# OBSERVE
# ============================================================

def observe_result(
    action,
    tool_result,
    message
):
    """
    Inspect the result returned by an agent tool.

    IMPORTANT:

    We do NOT call evaluate_agent_result() for known structured
    MCP/RAG tools.

    These tools already have predictable response schemas.

    This prevents valid MCP responses such as:

        {
            "success": True,
            "requirements": "...",
            "description": "..."
        }

    from being incorrectly marked as failures by the generic
    LLM evaluator.
    """

    # --------------------------------------------------------
    # No result
    # --------------------------------------------------------

    if tool_result is None:

        return {
            "success": False,
            "needs_adaptation": True,
            "reason": "Tool returned no result."
        }


    # --------------------------------------------------------
    # Invalid result
    # --------------------------------------------------------

    if not isinstance(
        tool_result,
        dict
    ):

        return {
            "success": False,
            "needs_adaptation": True,
            "reason": "Tool returned an invalid response."
        }


    # --------------------------------------------------------
    # Explicit failure
    # --------------------------------------------------------

    if tool_result.get("success") is False:

        return {
            "success": False,
            "needs_adaptation": True,
            "reason": tool_result.get(
                "error",
                "Tool request failed."
            )
        }


    # ========================================================
    # RAG
    # ========================================================

    if action == "career_rag":

        results = tool_result.get(
            "results",
            []
        )

        sources = tool_result.get(
            "sources",
            []
        )

        confidence = tool_result.get(
            "confidence",
            "low"
        )


        # ----------------------------------------------------
        # RAG returned useful information
        # ----------------------------------------------------

        if results:

            return {
                "success": True,

                "needs_adaptation": False,

                "reason": (
                    "Relevant career knowledge was "
                    "successfully retrieved from Career RAG."
                ),

                "rag": {
                    "sources": sources,
                    "confidence": confidence,
                    "results": results
                }
            }


        # ----------------------------------------------------
        # RAG succeeded technically but returned no results
        # ----------------------------------------------------

        return {
            "success": False,

            "needs_adaptation": True,

            "reason": (
                "Career RAG returned no relevant "
                "career knowledge."
            ),

            "rag": {
                "sources": sources,
                "confidence": confidence,
                "results": []
            }
        }


    # ========================================================
    # MCP: JOB INFORMATION
    # ========================================================

    if action == "job_information":

        job_data = tool_result.get(
            "job"
        )


        if not job_data:

            return {
                "success": False,

                "needs_adaptation": True,

                "reason": (
                    "MCP returned successfully but did not "
                    "include job information."
                ),

                "mcp": {
                    "tool": "career_get_job_mcp"
                }
            }


        return {
            "success": True,

            "needs_adaptation": False,

            "reason": (
                "Selected job information was successfully "
                "retrieved through MCP."
            ),

            "mcp": {
                "tool": "career_get_job_mcp"
            }
        }


    # ========================================================
    # MCP: REQUIREMENTS
    # ========================================================

    if action == "requirements":

        requirements = tool_result.get(
            "requirements",
            ""
        )

        description = tool_result.get(
            "description",
            ""
        )


        if not requirements and not description:

            return {
                "success": False,

                "needs_adaptation": True,

                "reason": (
                    "MCP returned successfully but did not "
                    "include job requirements or description."
                ),

                "mcp": {
                    "tool": "career_get_job_requirements_mcp"
                }
            }


        return {
            "success": True,

            "needs_adaptation": False,

            "reason": (
                "Job requirements and/or description were "
                "successfully retrieved through MCP."
            ),

            "mcp": {
                "tool": "career_get_job_requirements_mcp"
            }
        }


    # ========================================================
    # MCP: ANALYSIS
    # ========================================================

    if action == "analyse_job":

        analysis = tool_result.get(
            "analysis"
        )


        # ----------------------------------------------------
        # Some backends return analysis directly.
        # ----------------------------------------------------

        if analysis is None:

            analysis = tool_result


        if not analysis:

            return {
                "success": False,

                "needs_adaptation": True,

                "reason": (
                    "MCP analysis returned no analysis data."
                ),

                "mcp": {
                    "tool": "career_analyse_selected_job_mcp"
                }
            }


        return {
            "success": True,

            "needs_adaptation": False,

            "reason": (
                "Job analysis was successfully completed "
                "through MCP."
            ),

            "mcp": {
                "tool": "career_analyse_selected_job_mcp"
            }
        }


    # ========================================================
    # UNKNOWN ACTION
    # ========================================================

    return {
        "success": False,

        "needs_adaptation": True,

        "reason": f"Unknown action: {action}"
    }


# ============================================================
# ADAPT
# ============================================================

def adapt_action(
    action,
    observation,
    message
):
    """
    Decide what the agent should do after observation.

    Fallback chain:

        career_rag
            ↓
        job_information

        analyse_job
            ↓
        requirements
            ↓
        job_information

        requirements
            ↓
        job_information

        job_information
            ↓
        requirements
    """

    # --------------------------------------------------------
    # Current result is good.
    # Do not adapt.
    # --------------------------------------------------------

    if not observation.get(
        "needs_adaptation",
        True
    ):
        return action


    # --------------------------------------------------------
    # RAG failed.
    #
    # Fall back to the selected job itself so that the LLM
    # can still answer using the job description, requirements,
    # company, etc.
    # --------------------------------------------------------

    if action == "career_rag":

        return "job_information"


    # --------------------------------------------------------
    # Analysis failed.
    #
    # Requirements gives the LLM useful structured job data.
    # --------------------------------------------------------

    if action == "analyse_job":

        return "requirements"


    # --------------------------------------------------------
    # Requirements failed.
    #
    # Complete job information is the next useful source.
    # --------------------------------------------------------

    if action == "requirements":

        return "job_information"


    # --------------------------------------------------------
    # Job information failed.
    #
    # Try requirements as a secondary MCP tool.
    # --------------------------------------------------------

    if action == "job_information":

        return "requirements"


    # --------------------------------------------------------
    # Safety fallback.
    # --------------------------------------------------------

    return "job_information"


# ============================================================
# ACT
# ============================================================

def execute_action(
    action,
    job,
    message
):
    """
    Execute the selected agent action.

    MCP actions:

        job_information
        requirements
        analyse_job

    RAG action:

        career_rag
    """

    # ========================================================
    # MCP: COMPLETE JOB INFORMATION
    # ========================================================

    if action == "job_information":

        return get_selected_job_mcp_tool(
            job
        )


    # ========================================================
    # MCP: REQUIREMENTS
    # ========================================================

    if action == "requirements":

        return get_job_requirements_tool(
            job
        )


    # ========================================================
    # MCP: ANALYSIS
    # ========================================================

    if action == "analyse_job":

        return analyse_job_tool(
            job
        )


    # ========================================================
    # RAG: CAREER KNOWLEDGE
    # ========================================================

    if action == "career_rag":

        return get_career_rag_tool(
            message,
            job
        )


    # ========================================================
    # UNKNOWN ACTION
    # ========================================================

    return {
        "success": False,
        "error": f"Unknown agent action: {action}"
    }


# ============================================================
# RESPONSE GENERATION
# ============================================================

def generate_response(
    message,
    job,
    action,
    tool_result,
    observation,
    previous_result=None
):
    """
    Generate the final AI response.

    The LLM receives:

        selected job
        user question
        final action
        final tool result
        observation
        previous tool result

    The model is instructed through the
    generate_response prompt loaded by load_prompt().
    """

    prompt = load_prompt(
        "generate_response",

        message=message,

        job=job,

        action=action,

        tool_result=tool_result,

        observation=observation,

        previous_result=previous_result
    )


    return ask_smart(
        prompt
    )


# ============================================================
# HUMAN APPROVAL
# ============================================================

def create_pending_approval(
    response,
    planned_action,
    action,
    observation,
    tool_result,
    previous_result=None
):
    """
    Return the AI response together with agent execution
    evidence.

    Human approval is required before the response is
    considered final.
    """

    result = {

        "success": True,

        "status": "awaiting_approval",

        "response": response,

        "planned_action": planned_action,

        "action": action,

        "observation": observation,

        "adapted": (
            planned_action != action
        ),

        "requires_human_approval": True
    }


    # ========================================================
    # MCP EVIDENCE
    # ========================================================

    if observation.get("mcp"):

        result["mcp"] = {
            **observation["mcp"]
        }


    # ========================================================
    # RAG EVIDENCE
    # ========================================================

    if action == "career_rag":

        result["rag"] = {

            "sources": tool_result.get(
                "sources",
                []
            ),

            "confidence": tool_result.get(
                "confidence",
                "low"
            ),

            "results": tool_result.get(
                "results",
                []
            )
        }


    # ========================================================
    # PREVIOUS TOOL RESULT
    # ========================================================

    if previous_result is not None:

        result["previous_result"] = previous_result


    return result


# ============================================================
# AGENTIC LOOP
# ============================================================

def run_career_agent(
    job,
    message
):
    """
    R1/R0-style Career Agent loop:

        PLAN
          ↓
        ACT
          ↓
        OBSERVE
          ↓
        ADAPT
          ↓
        ACT
          ↓
        OBSERVE
          ↓
        ...
          ↓
        GENERATE RESPONSE
          ↓
        HUMAN APPROVAL

    Maximum number of tool executions is controlled by
    MAX_AGENT_STEPS.
    """

    # ========================================================
    # VALIDATE JOB
    # ========================================================

    if not job:

        return {
            "success": False,
            "error": "Job not found."
        }


    # ========================================================
    # VALIDATE MESSAGE
    # ========================================================

    if not message or not str(
        message
    ).strip():

        return {
            "success": False,
            "error": "Message is required."
        }


    try:

        # ====================================================
        # PLAN
        # ====================================================

        planned_action = choose_action(
            message
        )

        action = planned_action


        print(
            "--- PLAN ---"
        )

        print(
            f"User message: {message}"
        )

        print(
            f"Planned action: {planned_action}"
        )


        # ====================================================
        # LOOP STATE
        # ====================================================

        previous_result = None

        observation = None

        tool_result = None

        executed_actions = []

        adapted = False


        # ====================================================
        # AGENT LOOP
        # ====================================================

        for step in range(
            MAX_AGENT_STEPS
        ):

            print(
                f"--- AGENT STEP {step + 1}/{MAX_AGENT_STEPS} ---"
            )


            # ------------------------------------------------
            # Prevent accidental repeated action.
            # ------------------------------------------------

            if action in executed_actions:

                print(
                    f"Action '{action}' was already executed."
                )

                break


            executed_actions.append(
                action
            )


            # =================================================
            # ACT
            # =================================================

            print(
                "--- ACT ---"
            )

            print(
                f"Executing action: {action}"
            )


            tool_result = execute_action(
                action,
                job,
                message
            )


            print(
                f"Tool result: {tool_result}"
            )


            # =================================================
            # OBSERVE
            # =================================================

            observation = observe_result(
                action,
                tool_result,
                message
            )


            print(
                "--- OBSERVE ---"
            )

            print(
                f"Observation: {observation}"
            )


            # ------------------------------------------------
            # Successful result.
            # Stop tool execution.
            # ------------------------------------------------

            if not observation.get(
                "needs_adaptation",
                True
            ):

                print(
                    "Observation successful. "
                    "No further adaptation required."
                )

                break


            # =================================================
            # ADAPT
            # =================================================

            next_action = adapt_action(
                action,
                observation,
                message
            )


            print(
                "--- ADAPT ---"
            )

            print(
                f"Original action: {action}"
            )

            print(
                f"Next action: {next_action}"
            )


            # ------------------------------------------------
            # No useful next action.
            # ------------------------------------------------

            if next_action == action:

                print(
                    "No different action available."
                )

                break


            # ------------------------------------------------
            # Store first/previous result.
            # ------------------------------------------------

            if previous_result is None:

                previous_result = tool_result


            adapted = True

            action = next_action


        # ====================================================
        # MAX STEPS REACHED
        # ====================================================

        if (
            observation
            and observation.get(
                "needs_adaptation",
                False
            )
            and len(executed_actions) >= MAX_AGENT_STEPS
        ):

            print(
                "--- MAX AGENT STEPS REACHED ---"
            )


        # ====================================================
        # FALLBACK IF NO RESULT
        # ====================================================

        if tool_result is None:

            return {
                "success": False,
                "error": "Agent did not receive a tool result."
            }


        # ====================================================
        # GENERATE RESPONSE
        # ====================================================

        response = generate_response(
            message,
            job,
            action,
            tool_result,
            observation,
            previous_result
        )


        print(
            "--- AI RESPONSE ---"
        )

        print(
            response
        )


        # ====================================================
        # HUMAN REVIEW
        # ====================================================

        result = create_pending_approval(
            response=response,

            planned_action=planned_action,

            action=action,

            observation=observation,

            tool_result=tool_result,

            previous_result=previous_result
        )


        print(
            "--- HUMAN REVIEW REQUIRED ---"
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
