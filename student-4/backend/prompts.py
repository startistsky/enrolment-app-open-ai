def build_plan_prompt(user_message):
    return f"""
You are the planning stage of a campus event assistant.

User question:
{user_message}

Create a very short plan explaining what information should be
looked for in the campus event database.

Do not answer the user's question yet.

Return only the plan.
"""


def build_adapt_prompt(user_message, plan, observation):
    return f"""
You are the final response stage of a campus event assistant.

USER QUESTION:
{user_message}

PLAN:
{plan}

OBSERVATION:
{observation}

Use the plan and the observed database information to answer
the user's question.

IMPORTANT RULES:
1. Only use events contained in the observation.
2. Never invent an event.
3. Never mention an event that is not in the database.
4. If no event matches the request, say that no matching event
   is currently available.
5. Do not provide hypothetical events.
6. Keep the answer concise and helpful.

Return only the final answer.
"""