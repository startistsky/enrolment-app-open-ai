from llm_client import generate


def run(user_request, evidence):
    return generate("planner", {"user_request": user_request, "evidence": evidence}, {"plan": str, "evidence_required": list})
