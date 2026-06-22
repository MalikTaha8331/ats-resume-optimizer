"""
gap_analyzer.py
Compares structured CV facts against structured JD requirements.
Classifies every required/preferred skill into one of three buckets:

  PRESENT      - explicitly in the CV already, just needs surfacing/emphasis
  TRANSFERABLE - not explicitly listed, but reasonably implied by existing projects/experience
                 (e.g. "async TCP scanner" implies networking/backend, but doesn't imply React)
  MISSING      - no evidence at all in the CV

This classification is what prevents fabrication: only PRESENT and TRANSFERABLE skills
are allowed to be emphasized in the rewrite. MISSING skills go into a separate
"recommended to learn / confirm with user" list and are NEVER silently added to the CV.
"""

import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

GAP_ANALYSIS_PROMPT = """You are a gap-analysis engine comparing a candidate's CV facts
against a job description's requirements.

You will be given:
1. CV_FACTS: structured facts extracted from the candidate's actual CV (ground truth)
2. JD_REQUIREMENTS: structured requirements from the target job

For EVERY skill in required_skills and preferred_skills, classify it as one of:

- "present": the skill (or a clear synonym) is explicitly stated in CV_FACTS
- "transferable": not explicitly stated, but the candidate's existing projects/experience/bullets
  reasonably demonstrate related capability (explain the connection - e.g. "built an async TCP
  scanner" is transferable evidence for "backend development" or "networking", but NOT for "React"
  or "UI design" - transferability must be genuinely defensible, not a stretch)
- "missing": no defensible evidence anywhere in CV_FACTS

CRITICAL RULE: Be conservative with "transferable". If you cannot point to a SPECIFIC bullet,
project, or skill in CV_FACTS that justifies the connection, classify as "missing" instead.
Do not rationalize weak connections.

Return ONLY valid JSON, no markdown fences:

{
  "matched_skills": [
    {"skill": "", "status": "present", "evidence": "exact source from CV_FACTS"}
  ],
  "transferable_skills": [
    {"skill": "", "status": "transferable", "evidence": "specific CV_FACTS item", "connection_reasoning": ""}
  ],
  "missing_skills": [
    {"skill": "", "status": "missing", "required_or_preferred": "required|preferred"}
  ],
  "overall_match_percentage": 0,
  "summary": "2-3 sentence honest assessment of fit"
}
"""


def analyze_gap(cv_facts: dict, jd_requirements: dict, groq_api_key: str) -> dict:
    user_content = (
        f"CV_FACTS:\n{json.dumps(cv_facts, indent=2)}\n\n"
        f"JD_REQUIREMENTS:\n{json.dumps(jd_requirements, indent=2)}"
    )

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": GAP_ANALYSIS_PROMPT},
            {"role": "user", "content": user_content}
        ]
    }

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()

    raw_content = response.json()["choices"][0]["message"]["content"]
    cleaned = raw_content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        gap_result = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse gap analysis JSON: {e}\nRaw output: {raw_content}")

    # Recompute match percentage deterministically rather than trusting the LLM's arithmetic
    total = (
        len(gap_result.get("matched_skills", []))
        + len(gap_result.get("transferable_skills", []))
        + len(gap_result.get("missing_skills", []))
    )
    if total > 0:
        matched_weight = len(gap_result.get("matched_skills", [])) + 0.5 * len(gap_result.get("transferable_skills", []))
        gap_result["overall_match_percentage"] = round((matched_weight / total) * 100, 1)
    else:
        gap_result["overall_match_percentage"] = 0

    return gap_result


def build_confirmation_questions(gap_result: dict) -> list:
    """
    For missing skills, instead of silently adding them, generate yes/no confirmation
    questions for the user. This is the safe alternative to fabrication discussed earlier.
    Only required (not preferred) missing skills are asked about by default, to keep
    the UX from being overwhelming.
    """
    questions = []
    for item in gap_result.get("missing_skills", []):
        if item.get("required_or_preferred") == "required":
            questions.append({
                "skill": item["skill"],
                "question": f"The job asks for '{item['skill']}'. Do you have real experience with this "
                             f"(even coursework, personal projects, or self-study) that wasn't on your CV?",
                "if_yes": "ask_for_brief_evidence",
                "if_no": "add_to_recommended_learning_list"
            })
    return questions


if __name__ == "__main__":
    print("This module requires a GROQ_API_KEY to run live. Import and call analyze_gap().")
