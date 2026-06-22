"""
Mocked end-to-end test: simulates real Groq responses to verify the full
pipeline (extract -> JD -> gap -> confirm -> rewrite -> fact-check) wires
together correctly, without needing a live API key or network call.
"""
import sys
sys.path.insert(0, ".")

from unittest.mock import patch, MagicMock
import json
from app import app

# Fake Groq responses for each pipeline stage, in call order
FAKE_CV_FACTS = {
    "contact": {"name": "Malik Taha", "email": "malik@example.com", "phone": "",
                "location": "Wah Cantt, Pakistan", "linkedin": "", "github": "MalikTaha8331"},
    "summary": "Cybersecurity student building AI-powered security tools.",
    "skills": ["Python", "Flask", "SQLite", "bcrypt", "Async programming", "REST API design"],
    "experience": [],
    "projects": [
        {"name": "NetSentinel AI", "description": "AI-powered port scanner and risk assessment tool",
         "tech_used": ["Flask", "Python", "SQLite", "Async TCP"],
         "bullets": ["Built async TCP scanner with banner grabbing",
                     "Designed Flask backend with bcrypt auth and SQLite",
                     "Built interactive dashboard frontend"]}
    ],
    "education": [{"degree": "BS Cybersecurity", "institution": "Sir Syed CASE Institute of Technology",
                    "dates": "", "details": ""}],
    "certifications": []
}

FAKE_JD_REQUIREMENTS = {
    "role_title": "Web Developer",
    "seniority_level": "entry-level",
    "required_skills": ["Flask", "REST API design", "React"],
    "preferred_skills": ["SQLite", "Git"],
    "responsibilities": ["Build and maintain web applications"],
    "domain_keywords": ["full-stack", "frontend", "backend"]
}

FAKE_GAP_RESULT = {
    "matched_skills": [
        {"skill": "Flask", "status": "present", "evidence": "Flask in skills list"},
        {"skill": "REST API design", "status": "present", "evidence": "REST API design in skills list"}
    ],
    "transferable_skills": [
        {"skill": "SQLite", "status": "transferable", "evidence": "Used SQLite in NetSentinel AI",
         "connection_reasoning": "Direct database usage in a real project"}
    ],
    "missing_skills": [
        {"skill": "React", "status": "missing", "required_or_preferred": "required"},
        {"skill": "Git", "status": "missing", "required_or_preferred": "preferred"}
    ],
    "overall_match_percentage": 0,
    "summary": "Strong backend alignment, missing frontend framework experience."
}

FAKE_REWRITE_CLEAN = {
    "tailored_summary": "Cybersecurity student with hands-on Flask backend and REST API experience.",
    "reordered_skills": ["Flask", "REST API design", "SQLite", "Python"],
    "rewritten_experience": [],
    "rewritten_projects": [
        {"name": "NetSentinel AI", "description": "Full-stack Flask web application",
         "bullets": ["Designed RESTful API architecture using Flask",
                     "Implemented SQLite-backed data persistence layer"]}
    ],
    "transferable_skills_framing": [
        {"skill_area": "Database management", "how_demonstrated": "Used SQLite for auth and scan data storage in NetSentinel AI"}
    ]
}

FAKE_REWRITE_DIRTY = {
    "tailored_summary": "Experienced React and Kubernetes developer.",
    "reordered_skills": ["React", "Kubernetes", "Flask"],
    "rewritten_experience": [],
    "rewritten_projects": []
}


def make_groq_response(payload_dict):
    """Builds a fake requests.Response-like object matching Groq's API shape."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(payload_dict)}}]
    }
    return mock_resp


def run_test():
    client = app.test_client()

    with patch.dict("os.environ", {"GROQ_API_KEY": "fake-key-for-testing"}):
        import importlib
        import app as app_module
        importlib.reload(app_module)
        client = app_module.app.test_client()

        # --- Step 1: upload CV ---
        with patch("parsers.fact_extractor.requests.post", return_value=make_groq_response(FAKE_CV_FACTS)):
            resp = client.post("/api/upload-cv", json={"cv_text": "Malik Taha CV text here..."})
            print("=== upload-cv ===", resp.status_code)
            body = resp.get_json()
            session_id = body.get("session_id")
            print("session_id:", session_id)
            print("fact_pool sample:", body["cv_facts"]["_fact_pool"][:3])
            print("ATS score:", body["ats_score"]["ats_score"], "/", body["ats_score"]["max_score"],
                  "-", body["ats_score"]["verdict"])

        assert resp.status_code == 200, "upload-cv failed"
        assert "ats_score" in body, "ATS score missing from upload response!"

        # --- Step 2: analyze JD ---
        with patch("parsers.jd_extractor.requests.post", return_value=make_groq_response(FAKE_JD_REQUIREMENTS)), \
             patch("parsers.gap_analyzer.requests.post", return_value=make_groq_response(FAKE_GAP_RESULT)):
            resp = client.post("/api/analyze-jd", json={"session_id": session_id, "jd_text": "We need a web developer..."})
            print("\n=== analyze-jd ===", resp.status_code)
            body = resp.get_json()
            print("match %:", body["gap_result"]["overall_match_percentage"])
            print("confirmation questions:", body["confirmation_questions"])

        assert resp.status_code == 200, "analyze-jd failed"

        # --- Step 3: confirm skills ---
        resp = client.post("/api/confirm-skills", json={
            "session_id": session_id,
            "confirmed_skills": [{"skill": "Git", "evidence": "Used Git/GitHub for all project repos"}]
        })
        print("\n=== confirm-skills ===", resp.status_code, resp.get_json())
        assert resp.status_code == 200, "confirm-skills failed"

        # --- Step 4a: rewrite (CLEAN case) ---
        with patch("parsers.rewriter.requests.post", return_value=make_groq_response(FAKE_REWRITE_CLEAN)):
            resp = client.post("/api/rewrite", json={"session_id": session_id})
            print("\n=== rewrite (clean case) ===", resp.status_code)
            body = resp.get_json()
            print("fact_check.is_clean:", body["fact_check"]["is_clean"])
            print("fact_check.flags:", body["fact_check"]["flags"])

        assert resp.status_code == 200, "rewrite failed"
        assert body["fact_check"]["is_clean"] is True, "Expected clean rewrite to pass fact-check!"

        # --- Step 4b: rewrite (DIRTY case - simulating LLM fabrication) ---
        with patch("parsers.rewriter.requests.post", return_value=make_groq_response(FAKE_REWRITE_DIRTY)):
            resp = client.post("/api/rewrite", json={"session_id": session_id})
            print("\n=== rewrite (dirty/fabrication case) ===", resp.status_code)
            body = resp.get_json()
            print("fact_check.is_clean:", body["fact_check"]["is_clean"])
            print("fact_check.flags:", [f["flagged_term"] for f in body["fact_check"]["flags"]])
            print("warning:", body.get("warning"))

        assert body["fact_check"]["is_clean"] is False, "Expected dirty rewrite to be FLAGGED, but it passed clean!"
        flagged_terms = [f["flagged_term"] for f in body["fact_check"]["flags"]]
        assert "React" in flagged_terms, "Fabrication guard FAILED to catch React!"
        assert "Kubernetes" in flagged_terms, "Fabrication guard FAILED to catch Kubernetes!"

        # --- Step 5: regenerate with the CLEAN rewrite, then generate templates ---
        with patch("parsers.rewriter.requests.post", return_value=make_groq_response(FAKE_REWRITE_CLEAN)):
            client.post("/api/rewrite", json={"session_id": session_id})

        resp = client.post("/api/generate-templates", json={
            "session_id": session_id,
            "templates": ["modern", "compact"],
            "role_tagline": "Web Developer"
        })
        print("\n=== generate-templates ===", resp.status_code)
        body = resp.get_json()
        print("used_rewrite:", body.get("used_rewrite"))
        print("download_urls:", body.get("download_urls"))
        print("errors:", body.get("errors"))

        assert resp.status_code == 200, "generate-templates failed"
        assert body["used_rewrite"] is True, "Expected rewrite to be used for templates"
        assert "modern" in body["download_urls"], "modern template missing from output"
        assert "compact" in body["download_urls"], "compact template missing from output"
        assert not body["errors"], f"Unexpected template generation errors: {body['errors']}"

        # --- Step 6: actually download a generated file through the API ---
        download_resp = client.get(body["download_urls"]["modern"])
        print("\n=== download ===", download_resp.status_code,
              "Content-Type:", download_resp.headers.get("Content-Type"),
              "Content-Length:", download_resp.headers.get("Content-Length"))
        assert download_resp.status_code == 200, "Download route failed"
        assert len(download_resp.data) > 0, "Downloaded file is empty"

        print("\n✅ ALL TESTS PASSED — pipeline wiring + fabrication guard + template generation + download all work correctly.")


if __name__ == "__main__":
    run_test()
