"""
template_renderer.py
Bridges Python session data to the Node.js docx template engine.

Builds the structured JSON the templates expect (contact, tagline, summary,
skills, experience, projects, education, certifications) from:
  - cv_facts (ground truth from the original CV)
  - rewrite_result (the JD-tailored rewrite, if available)

If a rewrite exists, its tailored content takes priority (since it's the
JD-optimized version), falling back to original cv_facts content for any
fields the rewrite didn't touch (e.g. contact info, education - rewriter.py
doesn't touch these, they come straight from cv_facts).
"""

import os
import json
import subprocess
import tempfile
import uuid

TEMPLATES_ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
VALID_TEMPLATES = ["modern", "minimal", "technical", "executive", "compact"]


def build_template_input(cv_facts: dict, rewrite_result: dict = None, role_tagline: str = None) -> dict:
    """
    Merges cv_facts + optional rewrite_result into the flat structure the
    docx templates expect.
    """
    contact = cv_facts.get("contact", {})

    if rewrite_result:
        summary = rewrite_result.get("tailored_summary") or cv_facts.get("summary", "")
        skills = rewrite_result.get("reordered_skills") or cv_facts.get("skills", [])

        # Rewritten experience/projects replace originals ONLY if rewrite produced
        # entries for them; otherwise fall back to original facts so nothing
        # silently disappears from the output CV.
        experience = rewrite_result.get("rewritten_experience") or cv_facts.get("experience", [])
        projects = rewrite_result.get("rewritten_projects") or cv_facts.get("projects", [])
    else:
        summary = cv_facts.get("summary", "")
        skills = cv_facts.get("skills", [])
        experience = cv_facts.get("experience", [])
        projects = cv_facts.get("projects", [])

    # Preserve dates from original facts when merging rewritten experience/projects,
    # since rewriter.py's schema includes dates but title-matching guards against
    # any mismatch by falling back to the original entry's dates if missing.
    experience = _merge_dates(experience, cv_facts.get("experience", []), key="title")
    projects = _merge_dates(projects, cv_facts.get("projects", []), key="name")

    return {
        "contact": {
            "name": contact.get("name", ""),
            "email": contact.get("email", ""),
            "phone": contact.get("phone", ""),
            "location": contact.get("location", ""),
            "linkedin": contact.get("linkedin", ""),
            "github": contact.get("github", "")
        },
        "tagline": role_tagline or "",
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "projects": projects,
        "education": cv_facts.get("education", []),
        "certifications": cv_facts.get("certifications", [])
    }


def _merge_dates(rewritten_items: list, original_items: list, key: str) -> list:
    """
    If a rewritten experience/project entry is missing 'dates' (the rewriter
    doesn't always carry these through), look up the matching original entry
    by title/name and copy its dates over so they don't disappear from the
    rendered CV.
    """
    original_by_key = {item.get(key, "").lower(): item for item in original_items}
    merged = []

    for item in rewritten_items:
        item_copy = dict(item)
        if not item_copy.get("dates"):
            match = original_by_key.get(item.get(key, "").lower())
            if match:
                item_copy["dates"] = match.get("dates", "")
        merged.append(item_copy)

    return merged


def render_template(template_name: str, cv_data: dict) -> str:
    """
    Renders a single template. Returns the path to the generated .docx file.
    Raises ValueError for unknown template names, RuntimeError if the Node
    process fails.
    """
    if template_name not in VALID_TEMPLATES:
        raise ValueError(f"Unknown template '{template_name}'. Must be one of: {VALID_TEMPLATES}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        input_path = os.path.join(tmp_dir, "input.json")
        with open(input_path, "w", encoding="utf-8") as f:
            json.dump(cv_data, f)

        output_filename = f"{template_name}_{uuid.uuid4().hex[:8]}.docx"
        output_path = os.path.join(tempfile.gettempdir(), output_filename)

        result = subprocess.run(
            ["node", "render.js", template_name, input_path, output_path],
            cwd=TEMPLATES_ENGINE_DIR,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Template rendering failed for '{template_name}': {result.stderr}")

        return output_path


def render_all_templates(cv_data: dict, template_names: list = None) -> dict:
    """
    Renders multiple templates (default: all 5). Returns a dict mapping
    template_name -> generated file path. If one template fails, the others
    still complete - failures are reported separately rather than aborting
    the whole batch.
    """
    names = template_names or VALID_TEMPLATES
    results = {}
    errors = {}

    for name in names:
        try:
            results[name] = render_template(name, cv_data)
        except Exception as e:
            errors[name] = str(e)

    return {"generated": results, "errors": errors}


if __name__ == "__main__":
    sample_facts = {
        "contact": {"name": "Test User", "email": "test@example.com", "phone": "123",
                     "location": "City", "linkedin": "", "github": ""},
        "summary": "Test summary.",
        "skills": ["Python", "Flask"],
        "experience": [],
        "projects": [{"name": "Test Project", "description": "desc", "bullets": ["did a thing"]}],
        "education": [{"degree": "BS CS", "institution": "Uni", "dates": "2020-2024", "details": ""}],
        "certifications": []
    }
    data = build_template_input(sample_facts)
    out = render_all_templates(data, ["modern"])
    print(out)
