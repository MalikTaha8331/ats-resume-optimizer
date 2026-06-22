"""
jd_extractor.py
Parses a pasted Job Description into structured requirements: required skills,
nice-to-have skills, responsibilities, seniority level, and role title.
This is the "target" the CV will be scored against and reframed toward.
"""

import json
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

JD_SYSTEM_PROMPT = """You are a job description analysis engine. Extract structured
requirements from the job description text given.

Return ONLY valid JSON, no markdown fences, matching exactly this schema:

{
  "role_title": "",
  "seniority_level": "entry-level | mid-level | senior | unclear",
  "required_skills": ["hard requirements - explicitly stated as required/must-have"],
  "preferred_skills": ["nice-to-have / preferred / bonus skills"],
  "responsibilities": ["key day-to-day responsibilities mentioned"],
  "domain_keywords": ["industry/domain-specific terms an ATS would scan for, e.g. 'agile', 'CI/CD', 'cross-functional'"]
}

Extract only what is stated or strongly implied in the text. Do not invent requirements
the JD doesn't mention.
"""


def extract_jd_requirements(jd_text: str, groq_api_key: str) -> dict:
    payload = {
        "model": GROQ_MODEL,
        "temperature": 0,
        "messages": [
            {"role": "system", "content": JD_SYSTEM_PROMPT},
            {"role": "user", "content": f"JOB DESCRIPTION:\n\n{jd_text}"}
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
        raise ValueError(f"Failed to parse JD JSON: {e}\nRaw output: {raw_content}")


if __name__ == "__main__":
    print("This module requires a GROQ_API_KEY to run live. Import and call extract_jd_requirements().")
