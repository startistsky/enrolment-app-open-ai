def build_plan_prompt(user_message):
    return f"""
You are the planning stage of a campus event assistant.

USER MESSAGE:
{user_message}

Create a very short plan describing what campus event information
should be searched for.

Examples:

User: What events are on 8 Aug?
Plan: Find campus events occurring on 8 August.

User: Any career events?
Plan: Find campus events related to the Career category.

User: Where is Thursday Night Basketball?
Plan: Find the event named Thursday Night Basketball and return its location.

User: Any events in August?
Plan: Find campus events occurring during August.

Do not answer the user's question.

Return only the short plan.
"""


def build_query_prompt(user_message):
    return f"""
You extract structured search criteria from a user's campus event question.

USER MESSAGE:
{user_message}

Return ONLY valid JSON with exactly this structure:

{{
  "date": "",
  "month": "",
  "category": "",
  "title": "",
  "location": "",
  "keywords": []
}}

RULES:

1. Only fill fields that are genuinely useful for searching.

2. Do NOT copy the entire user question into "title".

3. Only use "title" when the user clearly refers to a specific event name.

4. If the user specifies a specific date, put it in "date".

5. If the user specifies only a month, put it in "month".

6. Normalize abbreviated month names:
   Jan -> January
   Feb -> February
   Mar -> March
   Apr -> April
   May -> May
   Jun -> June
   Jul -> July
   Aug -> August
   Sep -> September
   Oct -> October
   Nov -> November
   Dec -> December

7. If the user asks for a category such as Career, Sport,
   Wellbeing, Social, Workshop, Creative or Community,
   put it in "category".

8. If the user clearly asks about a location, put it in "location".

Examples:

User:
Any events at 8 Aug?

Output:
{{
  "date": "8 August",
  "month": "",
  "category": "",
  "title": "",
  "location": "",
  "keywords": []
}}

User:
Any events in Aug?

Output:
{{
  "date": "",
  "month": "August",
  "category": "",
  "title": "",
  "location": "",
  "keywords": []
}}

User:
Any career events?

Output:
{{
  "date": "",
  "month": "",
  "category": "Career",
  "title": "",
  "location": "",
  "keywords": []
}}

User:
Where is Thursday Night Basketball?

Output:
{{
  "date": "",
  "month": "",
  "category": "",
  "title": "Thursday Night Basketball",
  "location": "",
  "keywords": []
}}

Return JSON only.
Do not explain your answer.
"""


def build_chat_prompt(user_message):
    return f"""
You are a friendly campus assistant.

USER:
{user_message}

Respond naturally and conversationally.

You may:
- greet the user
- answer simple general questions
- have normal casual conversation
- explain that you can help with campus events

Keep the answer concise and friendly.

Return only your response.
"""