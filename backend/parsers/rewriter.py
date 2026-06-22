"""
rewriter.py
Generates the rewritten/reframed CV content using only facts that are present,
transferable, or user-confirmed. This is where "reframe, don't fabricate" is enforced.

Pipeline position: runs AFTER gap_analyzer.py and AFTER any user confirmations
for missing skills have been collected.
"""

import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

REWRITE_SYSTEM_PROMPT = """You are a professional CV rewriting engine. Your job is to
reframe a candidate's EXISTING, REAL experience to align with a target job description.

You are given:
1. CV_FACTS - the candidate's verified real experience, skills, and projects
2. JD_REQUIREMENTS - the target job's requirements
3. GAP_ANALYSIS - which skills are present/transferable/missing, with reasoning
4. USER_CONFIRMED_SKILLS - skills the user explicitly confirmed they have, even though
   not on the original CV (treat these as equally valid as CV_FACTS)

ABSOLUTE RULES - VIOLATING THESE MAKES THE OUTPUT USELESS AND HARMFUL:
- NEVER invent a tool, technology, employer, job title, certification, or metric that
  isn't in CV_FACTS or USER_CONFIRMED_SKILLS.
- NEVER change the candidate's actual job titles or employers.
- You MAY rephrase, reprioritize, and re-emphasize existing true facts using language
  that resonates with the target role (e.g. "built async TCP scanner" can be described
  as "developed backend service with concurrent I/O handling" - same fact, different framing).
- You MAY reorder sections/bullets to put the most JD-relevant facts first.
- You MAY elaborate on a real skill's relevance ONLY if the elaboration is a true
  description of work already done (e.g. if CV says "Flask app with REST endpoints",
  you can say "designed RESTful API architecture" - that's accurate elaboration, not fabrication).
- For TRANSFERABLE skills from gap analysis, you may mention the connection explicitly
  (e.g. "Built async networking tools (transferable to backend development roles)")
  but must NOT claim direct experience in the missing skill itself.
- DO NOT mention missing skills the user didn't confirm, at all.

Return ONLY valid JSON, no markdown fences:

{
  "tailored_summary": "2-3 sentence professional summary tailored to the JD, using only real facts",
  "reordered_skills": ["skills list reordered with most JD-relevant first, no additions"],
  "rewritten_experience": [
    {"title": "", "organization": "", "dates": "", "bullets": ["rewritten bullets, same facts, JD-aligned language"]}
  ],
  "rewritten_projects": [
    {"name": "", "description": "", "bullets": ["rewritten bullets emphasizing JD-relevant angles"]}
  ],
  "transferable_skills_framing": [
    {"skill_area": "", "how_demonstrated": "honest sentence connecting existing work to this area"}
  ]
}
"""


def generate_rewrite(cv_facts: dict, jd_requirements: dict, gap_result: dict,
                      user_confirmed_skills: list, groq_api_key: str) -> dict:
    user_content = (
        f"CV_FACTS:\n{json.dumps(cv_facts, indent=2)}\n\n"
        f"JD_REQUIREMENTS:\n{json.dumps(jd_requirements, indent=2)}\n\n"
        f"GAP_ANALYSIS:\n{json.dumps(gap_result, indent=2)}\n\n"
        f"USER_CONFIRMED_SKILLS:\n{json.dumps(user_confirmed_skills, indent=2)}"
    )

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.4,  # slightly higher than extraction, since this is genuine rewriting
        "messages": [
            {"role": "system", "content": REWRITE_SYSTEM_PROMPT},
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
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse rewrite JSON: {e}\nRaw output: {raw_content}")


if __name__ == "__main__":
    print("This module requires a GROQ_API_KEY to run live. Import and call generate_rewrite().")
