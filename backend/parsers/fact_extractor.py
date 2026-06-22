"""
fact_extractor.py
Converts raw CV text into structured facts: contact info, sections, skills, projects,
experience, education. This structured "ground truth" is what every later step
(scoring, rewriting, fabrication-check) gets validated against.

IMPORTANT: This module only EXTRACTS what's already in the CV. It never adds anything.
The LLM call here is constrained to extraction-only via prompt + temperature=0 + JSON schema.
"""

import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

EXTRACTION_SYSTEM_PROMPT = """You are a CV data extraction engine. Your ONLY job is to read the
CV text given and extract what is ALREADY THERE into structured JSON.

STRICT RULES:
- Do NOT add, infer, or invent any skill, tool, company, degree, or experience not explicitly
  present in the text.
- Do NOT "improve" or rewrite anything. This is extraction, not rewriting.
- If a section is missing or empty, return an empty list/string for it. Do not guess.
- If something is ambiguous, extract it as-is rather than interpreting it.

Return ONLY valid JSON, no markdown fences, no preamble, matching exactly this schema:

{
  "contact": {"name": "", "email": "", "phone": "", "location": "", "linkedin": "", "github": ""},
  "summary": "",
  "skills": ["list of every skill/tool/technology explicitly mentioned anywhere in the CV"],
  "experience": [
    {"title": "", "organization": "", "dates": "", "bullets": ["..."]}
  ],
  "projects": [
    {"name": "", "description": "", "tech_used": ["..."], "bullets": ["..."]}
  ],
  "education": [
    {"degree": "", "institution": "", "dates": "", "details": ""}
  ],
  "certifications": ["..."]
}
"""


def extract_facts(cv_text: str, groq_api_key: str) -> dict:
    """
    Calls the LLM in extraction-only mode to structure the CV into verifiable facts.
    temperature=0 to minimize creative drift during extraction.
    """
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"CV TEXT:\n\n{cv_text}"}
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
        structured = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse extraction JSON: {e}\nRaw output: {raw_content}")

    # Build a flat "fact pool" — every atomic claim that exists in the original CV.
    # This is what the fabrication-guard (fact_checker.py) will check rewrites against.
    structured["_fact_pool"] = build_fact_pool(structured)

    return structured


def build_fact_pool(structured: dict) -> list:
    """
    Flattens all extracted facts into a single lowercase set of strings for fast
    substring/fuzzy checking later. Anything NOT traceable to this pool is a
    potential fabrication if it shows up in a rewritten CV.
    """
    pool = set()

    for skill in structured.get("skills", []):
        pool.add(skill.lower().strip())

    for exp in structured.get("experience", []):
        pool.add(exp.get("title", "").lower().strip())
        pool.add(exp.get("organization", "").lower().strip())
        for bullet in exp.get("bullets", []):
            pool.add(bullet.lower().strip())

    for proj in structured.get("projects", []):
        pool.add(proj.get("name", "").lower().strip())
        for tech in proj.get("tech_used", []):
            pool.add(tech.lower().strip())
        for bullet in proj.get("bullets", []):
            pool.add(bullet.lower().strip())

    for edu in structured.get("education", []):
        pool.add(edu.get("degree", "").lower().strip())
        pool.add(edu.get("institution", "").lower().strip())

    for cert in structured.get("certifications", []):
        pool.add(cert.lower().strip())

    pool.discard("")
    return sorted(pool)


if __name__ == "__main__":
    print("This module requires a GROQ_API_KEY to run live. Import and call extract_facts().")
