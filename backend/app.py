"""
app.py
Main Flask application wiring together the CV optimization pipeline:

  1. POST /api/upload-cv         -> extract raw text + structured facts
  2. POST /api/analyze-jd        -> extract JD requirements + run gap analysis
  3. POST /api/confirm-skills    -> accept user confirmations for missing skills
  4. POST /api/rewrite           -> generate tailored rewrite + run fact-check
  5. GET  /api/session/<id>      -> retrieve current session state (debug/UI use)

Session state is kept server-side in memory (SESSIONS dict) keyed by session_id,
since this is a portfolio project, not production infra. A real deployment would
use Redis/DB, but in-memory is fine for demo purposes and keeps it simple.
"""

import os
import uuid
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

from parsers.cv_extractor import extract_cv_text
from parsers.fact_extractor import extract_facts
from parsers.jd_extractor import extract_jd_requirements
from parsers.gap_analyzer import analyze_gap, build_confirmation_questions
from parsers.rewriter import generate_rewrite
from parsers.fact_checker import check_rewrite_for_fabrication
from ats_engine.ats_rules import calculate_ats_score
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "templates_engine"))
from templates_engine.template_renderer import build_template_input, render_all_templates, VALID_TEMPLATES

app = Flask(__name__)
CORS(app)  # frontend is served separately (static file or different port), so allow cross-origin calls

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# In-memory session store: { session_id: { cv_facts, jd_requirements, gap_result, ... } }
SESSIONS = {}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def require_groq_key():
    if not GROQ_API_KEY:
        return jsonify({
            "error": "GROQ_API_KEY is not configured on the server. "
                     "Set it as an environment variable before starting the app."
        }), 500
    return None


@app.route("/api/upload-cv", methods=["POST"])
def upload_cv():
    """
    Accepts either a file upload (multipart/form-data, field 'cv_file') or
    pasted text (JSON body, field 'cv_text'). Extracts raw text, then runs
    fact extraction to build the verified ground-truth fact pool.
    """
    key_error = require_groq_key()
    if key_error:
        return key_error

    raw_text = None
    filepath = None

    if "cv_file" in request.files:
        file = request.files["cv_file"]
        if file.filename == "":
            return jsonify({"error": "No file selected."}), 400
        if not allowed_file(file.filename):
            return jsonify({"error": "Unsupported file type. Use PDF, DOCX, or TXT."}), 400

        filename = secure_filename(file.filename)
        session_id = str(uuid.uuid4())
        filepath = os.path.join(UPLOAD_FOLDER, f"{session_id}_{filename}")
        file.save(filepath)
    else:
        data = request.get_json(silent=True) or {}
        raw_text = data.get("cv_text", "").strip()
        if not raw_text:
            return jsonify({"error": "No CV file or cv_text provided."}), 400
        session_id = str(uuid.uuid4())

    try:
        extraction = extract_cv_text(filepath=filepath, raw_text=raw_text)

        if extraction["extraction_warnings"]:
            # Still proceed, but the warnings matter a lot for ATS scoring later
            pass

        cv_facts = extract_facts(extraction["text"], GROQ_API_KEY)

        # Deterministic ATS formatting/parsability score - runs independently of
        # the LLM, so it's reproducible and explainable regardless of AI behavior.
        ats_score_result = calculate_ats_score(
            cv_text=extraction["text"],
            source_type=extraction["source_type"],
            extraction_warnings=extraction["extraction_warnings"]
        )

    except Exception as e:
        return jsonify({"error": f"CV processing failed: {str(e)}"}), 500
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)  # don't retain uploaded files longer than needed

    SESSIONS[session_id] = {
        "cv_raw_text": extraction["text"],
        "cv_facts": cv_facts,
        "extraction_warnings": extraction["extraction_warnings"],
        "ats_score_result": ats_score_result,
        "jd_requirements": None,
        "gap_result": None,
        "user_confirmed_skills": [],
        "rewrite_result": None,
        "fact_check_result": None
    }

    return jsonify({
        "session_id": session_id,
        "cv_facts": cv_facts,
        "extraction_warnings": extraction["extraction_warnings"],
        "ats_score": ats_score_result
    })


@app.route("/api/analyze-jd", methods=["POST"])
def analyze_jd():
    """
    Accepts { session_id, jd_text }. Extracts JD requirements and runs gap
    analysis against the previously-extracted CV facts.
    """
    key_error = require_groq_key()
    if key_error:
        return key_error

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    jd_text = (data.get("jd_text") or "").strip()

    if session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session_id. Upload a CV first."}), 400
    if not jd_text:
        return jsonify({"error": "jd_text is required."}), 400

    session = SESSIONS[session_id]

    try:
        jd_requirements = extract_jd_requirements(jd_text, GROQ_API_KEY)
        gap_result = analyze_gap(session["cv_facts"], jd_requirements, GROQ_API_KEY)
        confirmation_questions = build_confirmation_questions(gap_result)
    except Exception as e:
        return jsonify({"error": f"JD analysis failed: {str(e)}"}), 500

    session["jd_requirements"] = jd_requirements
    session["gap_result"] = gap_result

    return jsonify({
        "session_id": session_id,
        "jd_requirements": jd_requirements,
        "gap_result": gap_result,
        "confirmation_questions": confirmation_questions
    })


@app.route("/api/confirm-skills", methods=["POST"])
def confirm_skills():
    """
    Accepts { session_id, confirmed_skills: [{skill, evidence}] }.
    These are skills the user explicitly confirms they have, with brief evidence,
    even though absent from the original CV. This is the ONLY sanctioned way
    new skills enter the rewrite - never silently injected by the AI.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    confirmed_skills = data.get("confirmed_skills", [])

    if session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session_id."}), 400

    if not isinstance(confirmed_skills, list):
        return jsonify({"error": "confirmed_skills must be a list."}), 400

    session = SESSIONS[session_id]
    session["user_confirmed_skills"] = confirmed_skills

    return jsonify({
        "session_id": session_id,
        "confirmed_skills": confirmed_skills,
        "message": "Confirmed skills recorded. These will be treated as verified facts in the rewrite."
    })


@app.route("/api/rewrite", methods=["POST"])
def rewrite_cv():
    """
    Accepts { session_id }. Generates the tailored rewrite using CV facts + JD
    requirements + gap analysis + any user-confirmed skills, then immediately
    runs the fabrication fact-checker against it before returning.
    """
    key_error = require_groq_key()
    if key_error:
        return key_error

    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")

    if session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session_id."}), 400

    session = SESSIONS[session_id]

    if not session["jd_requirements"] or not session["gap_result"]:
        return jsonify({"error": "Run /api/analyze-jd before requesting a rewrite."}), 400

    try:
        confirmed_skill_names = [s.get("skill", "") for s in session["user_confirmed_skills"]]

        rewrite_result = generate_rewrite(
            cv_facts=session["cv_facts"],
            jd_requirements=session["jd_requirements"],
            gap_result=session["gap_result"],
            user_confirmed_skills=confirmed_skill_names,
            groq_api_key=GROQ_API_KEY
        )

        fact_check_result = check_rewrite_for_fabrication(
            rewrite_result=rewrite_result,
            fact_pool=session["cv_facts"].get("_fact_pool", []),
            user_confirmed_skills=confirmed_skill_names
        )

    except Exception as e:
        return jsonify({"error": f"Rewrite generation failed: {str(e)}"}), 500

    session["rewrite_result"] = rewrite_result
    session["fact_check_result"] = fact_check_result

    response = {
        "session_id": session_id,
        "rewrite_result": rewrite_result,
        "fact_check": fact_check_result
    }

    if not fact_check_result["is_clean"]:
        response["warning"] = (
            f"{fact_check_result['flag_count']} term(s) in the rewrite could not be verified "
            f"against your original CV or confirmed skills. Review the 'fact_check.flags' list "
            f"before using this CV - these may be legitimate elaborations or may need correction."
        )

    return jsonify(response)


@app.route("/api/generate-templates", methods=["POST"])
def generate_templates():
    """
    Accepts { session_id, templates: [...], use_rewrite: bool, role_tagline: str }.

    Generates the requested docx templates (default: all 5) using either the
    JD-tailored rewrite (if use_rewrite=true and a rewrite exists) or the
    original CV facts otherwise. Returns file paths for download.

    templates: list of names from ["modern", "minimal", "technical", "executive", "compact"].
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    requested_templates = data.get("templates", VALID_TEMPLATES)
    use_rewrite = data.get("use_rewrite", True)
    role_tagline = data.get("role_tagline", "")

    if session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session_id."}), 400

    invalid = [t for t in requested_templates if t not in VALID_TEMPLATES]
    if invalid:
        return jsonify({"error": f"Unknown template(s): {invalid}. Valid options: {VALID_TEMPLATES}"}), 400

    session = SESSIONS[session_id]
    rewrite_to_use = session["rewrite_result"] if (use_rewrite and session["rewrite_result"]) else None

    try:
        cv_data = build_template_input(
            cv_facts=session["cv_facts"],
            rewrite_result=rewrite_to_use,
            role_tagline=role_tagline
        )
        render_output = render_all_templates(cv_data, requested_templates)
    except Exception as e:
        return jsonify({"error": f"Template generation failed: {str(e)}"}), 500

    # Track generated file paths on the session so /api/download/<session_id>/<template>
    # can serve them safely (never expose raw server filesystem paths to the browser).
    session.setdefault("generated_template_paths", {})
    session["generated_template_paths"].update(render_output["generated"])

    download_urls = {
        name: f"/api/download/{session_id}/{name}"
        for name in render_output["generated"]
    }

    response = {
        "session_id": session_id,
        "used_rewrite": rewrite_to_use is not None,
        "download_urls": download_urls,
        "errors": render_output["errors"]
    }

    if render_output["errors"]:
        response["warning"] = f"{len(render_output['errors'])} template(s) failed to generate. See 'errors' for details."

    return jsonify(response)


@app.route("/api/download/<session_id>/<template_name>", methods=["GET"])
def download_template(session_id, template_name):
    """
    Serves a previously generated docx file for download. Looks up the actual
    server-side path from session state rather than trusting any path from the
    request, so the browser never needs (or is able) to reference raw filesystem paths.
    """
    if session_id not in SESSIONS:
        return jsonify({"error": "Invalid or expired session_id."}), 404

    session = SESSIONS[session_id]
    paths = session.get("generated_template_paths", {})

    if template_name not in paths:
        return jsonify({"error": f"No generated file found for template '{template_name}'. "
                                  f"Call /api/generate-templates first."}), 404

    filepath = paths[template_name]
    if not os.path.exists(filepath):
        return jsonify({"error": "Generated file no longer exists on the server. Regenerate it."}), 404

    contact_name = session["cv_facts"].get("contact", {}).get("name", "Resume").replace(" ", "_")
    download_filename = f"{contact_name}_{template_name}.docx"

    return send_file(
        filepath,
        as_attachment=True,
        download_name=download_filename,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id):
    """Debug/UI helper to retrieve full session state."""
    if session_id not in SESSIONS:
        return jsonify({"error": "Session not found."}), 404
    return jsonify(SESSIONS[session_id])


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "groq_configured": bool(GROQ_API_KEY)})


if __name__ == "__main__":
    app.run(debug=True, port=5000, use_reloader=False)
