"""
ats_rules.py
Deterministic, explainable ATS compatibility scoring.

This is intentionally NOT an LLM call. Real ATS systems (Workday, iCIMS, Greenhouse,
Taleo, Lever) fail on structural/mechanical issues, not "vibes" - so this score
should be 100% reproducible and explainable: same input -> same output, every time,
with a clear reason for every point lost.

Rules sourced from cross-referencing current (2026) ATS parsing behavior across
multiple platforms - see citations in project README.

Score starts at 100 and deductions are applied per category. Categories:
  - File format & extractability     (up to -25)
  - Layout / structure                (up to -20)
  - Section headers                   (up to -25)
  - Date formatting consistency       (up to -10)
  - Fonts & special characters        (up to -10)
  - Contact info placement            (up to -10)
"""

import re


STANDARD_SECTION_HEADERS = {
    "experience", "work experience", "professional experience", "employment history",
    "education", "skills", "technical skills", "summary", "professional summary",
    "objective", "projects", "certifications", "certificates", "awards",
    "publications", "languages", "references", "contact"
}

NON_STANDARD_HEADER_PATTERNS = [
    r"my journey", r"the toolkit", r"where i've made impact", r"my story",
    r"what i bring", r"my superpowers"
]

DECORATIVE_BULLET_CHARS = ["★", "■", "➤", "✓", "♦", "▶", "❖", "✦"]
SAFE_BULLET_CHARS = ["•", "-", "*", "◦"]

ICON_PATTERN = re.compile(
    r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]"
)

DATE_PATTERNS = {
    "month_year": re.compile(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b", re.IGNORECASE),
    "numeric_slash": re.compile(r"\b\d{1,2}/\d{4}\b"),
    "year_only": re.compile(r"(?<!\d)\b\d{4}\s*[-–—]\s*(\d{4}|present)\b", re.IGNORECASE),
    "apostrophe_year": re.compile(r"'\d{2}\b"),
    "season_year": re.compile(r"\b(Spring|Summer|Fall|Autumn|Winter)\s+\d{4}\b", re.IGNORECASE),
}


def check_file_format(source_type: str, extraction_warnings: list) -> dict:
    """
    Scores based on how the file was submitted and whether text extraction succeeded.
    A PDF that fails to extract text (image-based/scanned) is the single worst case -
    it means the real ATS would see nothing at all.
    """
    deductions = []
    score = 25  # max points for this category

    if extraction_warnings:
        deductions.append({
            "issue": "Text extraction failed or returned empty content",
            "detail": "Your file appears to be an image-based or non-text-layer PDF. "
                      "Real ATS systems will see a BLANK resume. This is the single most "
                      "severe issue possible - it must be fixed before anything else matters.",
            "points_lost": 25
        })
        return {"score": 0, "max_score": 25, "deductions": deductions}

    if source_type == "pdf":
        deductions.append({
            "issue": "Submitted as PDF",
            "detail": "DOCX outperformed PDF in the majority of recent ATS parsing tests "
                      "(Workday, Greenhouse, iCIMS) for clean text extraction, since design-heavy "
                      "PDFs can embed text as objects rather than readable strings. PDF is not "
                      "wrong, but DOCX is the safer default unless the employer requests PDF.",
            "points_lost": 5
        })
        score -= 5
    elif source_type == "pasted_text":
        deductions.append({
            "issue": "Raw text input - no file structure to evaluate",
            "detail": "Formatting-related checks (fonts, columns, text boxes) cannot be verified "
                      "from plain text. This score reflects content only; export to DOCX before submitting.",
            "points_lost": 3
        })
        score -= 3

    return {"score": max(score, 0), "max_score": 25, "deductions": deductions}


def check_section_headers(cv_text: str) -> dict:
    """
    Checks whether the CV uses standard, parser-recognized section headers.
    Non-standard/creative headers cause the parser to miscategorize or drop content entirely.
    """
    deductions = []
    score = 25
    text_lower = cv_text.lower()

    found_standard = sum(1 for header in STANDARD_SECTION_HEADERS if header in text_lower)

    if found_standard == 0:
        deductions.append({
            "issue": "No standard section headers detected",
            "detail": "ATS parsers categorize content by matching headers like 'Experience', "
                      "'Education', 'Skills'. With none detected, the parser likely cannot "
                      "categorize any of your content correctly.",
            "points_lost": 25
        })
        return {"score": 0, "max_score": 25, "deductions": deductions}

    for pattern in NON_STANDARD_HEADER_PATTERNS:
        if re.search(pattern, text_lower):
            deductions.append({
                "issue": f"Non-standard/creative section header detected",
                "detail": "Creative headers (e.g. 'My Journey' instead of 'Experience') are not "
                          "recognized by ATS categorization logic and may cause that section's "
                          "content to be dropped or misfiled.",
                "points_lost": 8
            })
            score -= 8
            break  # only penalize once for this category

    if found_standard < 3:
        deductions.append({
            "issue": "Few standard headers found",
            "detail": f"Only {found_standard} standard section header(s) detected. A typical "
                      "ATS-friendly resume clearly labels Experience, Education, and Skills sections.",
            "points_lost": 8
        })
        score -= 8

    return {"score": max(score, 0), "max_score": 25, "deductions": deductions}


def check_date_consistency(cv_text: str) -> dict:
    """
    Checks for consistent, parser-friendly date formats. Mixed formats or ambiguous
    formats (apostrophe years, season names, year-only ranges) cause ATS systems to
    miscalculate total experience - tested to cause real candidates to show fewer
    years of experience than they actually have.
    """
    deductions = []
    score = 10

    matches_by_type = {key: pattern.findall(cv_text) for key, pattern in DATE_PATTERNS.items()}

    if matches_by_type["apostrophe_year"]:
        deductions.append({
            "issue": "Apostrophe-style year format detected (e.g. '23)",
            "detail": "Some ATS parsers misread apostrophe years as typos or garbage characters, "
                      "leading to incorrect experience date calculation.",
            "points_lost": 4
        })
        score -= 4

    if matches_by_type["season_year"]:
        deductions.append({
            "issue": "Season-based date detected (e.g. 'Summer 2023')",
            "detail": "ATS parsers expect month names or numeric months. 'Summer' is not "
                      "recognized as a month and may cause that date to be dropped.",
            "points_lost": 3
        })
        score -= 3

    if matches_by_type["year_only"] and not (matches_by_type["month_year"] or matches_by_type["numeric_slash"]):
        deductions.append({
            "issue": "Year-only date ranges detected (e.g. 2022-2023) with no month precision",
            "detail": "Without month precision, ATS systems estimate tenure conservatively and "
                      "may credit you with far less experience than you actually have.",
            "points_lost": 3
        })
        score -= 3

    format_types_used = sum([
        bool(matches_by_type["month_year"]),
        bool(matches_by_type["numeric_slash"]),
    ])
    if format_types_used > 1:
        deductions.append({
            "issue": "Mixed date formats used across the document",
            "detail": "Using both 'Jan 2023' and '01/2023' style dates in the same document "
                      "can cause ATS systems to miscalculate total years of experience. "
                      "Pick ONE format ('Month YYYY' is the most reliably parsed) and use it everywhere.",
            "points_lost": 4
        })
        score -= 4

    return {"score": max(score, 0), "max_score": 10, "deductions": deductions}


def check_special_characters(cv_text: str) -> dict:
    """
    Checks for icons/emoji and decorative bullet characters that ATS parsers
    often render as garbage characters or skip entirely.
    """
    deductions = []
    score = 10

    icon_matches = ICON_PATTERN.findall(cv_text)
    if icon_matches:
        deductions.append({
            "issue": f"{len(icon_matches)} icon/emoji character(s) detected",
            "detail": "Icons (e.g. a phone or email symbol) are often read as garbage characters "
                      "or cause the entire line to be skipped by the parser. Use text labels instead "
                      "(e.g. 'Phone:', 'Email:').",
            "points_lost": min(6, len(icon_matches) * 2)
        })
        score -= min(6, len(icon_matches) * 2)

    decorative_found = [ch for ch in DECORATIVE_BULLET_CHARS if ch in cv_text]
    if decorative_found:
        deductions.append({
            "issue": f"Decorative bullet character(s) detected: {', '.join(decorative_found)}",
            "detail": "Non-standard bullet symbols may be ignored or misread by some parsers. "
                      "Stick to standard round bullets (•) or hyphens (-).",
            "points_lost": 4
        })
        score -= 4

    return {"score": max(score, 0), "max_score": 10, "deductions": deductions}


def check_contact_info_placement(cv_text: str) -> dict:
    """
    Checks that core contact info (email, phone pattern) appears in the plain text,
    near the top. If extraction returns the text at all (we already control for that
    upstream), the main remaining risk is contact info being absent from the
    extracted text entirely - a strong signal it was in a header/footer/text-box,
    which many parsers skip.
    """
    deductions = []
    score = 10

    email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    phone_pattern = re.compile(r"(\+?\d[\d\s\-\(\)]{8,}\d)")

    has_email = bool(email_pattern.search(cv_text))
    has_phone = bool(phone_pattern.search(cv_text))

    if not has_email:
        deductions.append({
            "issue": "No email address found in extracted text",
            "detail": "If your email exists visually but wasn't extracted, it's likely inside a "
                      "header, footer, or text box - many ATS parsers skip these entirely, meaning "
                      "recruiters may see a resume with no way to contact you.",
            "points_lost": 6
        })
        score -= 6

    if not has_phone:
        deductions.append({
            "issue": "No phone number found in extracted text",
            "detail": "Same risk as missing email - likely trapped in a header/footer/text box "
                      "that the parser skipped.",
            "points_lost": 4
        })
        score -= 4

    return {"score": max(score, 0), "max_score": 10, "deductions": deductions}


def check_structural_layout(cv_text: str, extraction_warnings: list) -> dict:
    """
    Approximates layout risk from the EXTRACTED text itself. True column/table
    detection requires the original file's layout structure (not just text), so
    this checks for the telltale SYMPTOM of column scrambling: short, disjointed
    lines where unrelated short fragments appear adjacent (a common signature of
    "word salad" from column merging), plus an excessively long max line length, which
    can indicate over-condensed multi-column content collapsed onto one row.
    """
    deductions = []
    score = 20

    lines = [l.strip() for l in cv_text.split("\n") if l.strip()]
    if not lines:
        return {"score": 0, "max_score": 20, "deductions": [{
            "issue": "No structured line content extracted",
            "detail": "The document produced no usable line structure - likely an extraction failure.",
            "points_lost": 20
        }]}

    very_short_lines = [
        l for l in lines
        if len(l.split()) <= 2
        and len(l) > 0
        and l.lower().strip(":") not in STANDARD_SECTION_HEADERS
        and not l.startswith(("•", "-", "*", "◦"))
    ]
    short_line_ratio = len(very_short_lines) / len(lines)

    if short_line_ratio > 0.65:
        deductions.append({
            "issue": "High proportion of very short, fragmented lines",
            "detail": "Over half of extracted lines are 1-2 words. This pattern often indicates "
                      "the original document used multi-column or table layouts that collapsed "
                      "into fragmented lines during extraction - a strong sign the live ATS would "
                      "see scrambled, out-of-order content.",
            "points_lost": 8
        })
        score -= 8

    avg_line_length = sum(len(l) for l in lines) / len(lines)
    if avg_line_length > 200:
        deductions.append({
            "issue": "Unusually long average line length",
            "detail": "Extremely long merged lines can indicate columns or table cells were "
                      "concatenated together during extraction, mixing unrelated content.",
            "points_lost": 6
        })
        score -= 6

    return {"score": max(score, 0), "max_score": 20, "deductions": deductions}


def calculate_ats_score(cv_text: str, source_type: str, extraction_warnings: list) -> dict:
    """
    Main entry point. Runs all deterministic checks and combines into a single
    explainable ATS Compatibility Score out of 100.
    """
    file_format = check_file_format(source_type, extraction_warnings)
    layout = check_structural_layout(cv_text, extraction_warnings)
    headers = check_section_headers(cv_text)
    dates = check_date_consistency(cv_text)
    special_chars = check_special_characters(cv_text)
    contact = check_contact_info_placement(cv_text)

    total_score = (
        file_format["score"] + layout["score"] + headers["score"]
        + dates["score"] + special_chars["score"] + contact["score"]
    )
    max_possible = (
        file_format["max_score"] + layout["max_score"] + headers["max_score"]
        + dates["max_score"] + special_chars["max_score"] + contact["max_score"]
    )

    all_deductions = (
        file_format["deductions"] + layout["deductions"] + headers["deductions"]
        + dates["deductions"] + special_chars["deductions"] + contact["deductions"]
    )
    # Sort worst issues first so the user sees the highest-impact fixes up top
    all_deductions.sort(key=lambda d: d["points_lost"], reverse=True)

    if total_score >= 80:
        verdict = "ATS-friendly"
    elif total_score >= 60:
        verdict = "Borderline - some fixes recommended"
    else:
        verdict = "High risk - significant formatting issues likely to cause parsing failures"

    return {
        "ats_score": total_score,
        "max_score": max_possible,
        "verdict": verdict,
        "category_breakdown": {
            "file_format": file_format,
            "layout_structure": layout,
            "section_headers": headers,
            "date_consistency": dates,
            "special_characters": special_chars,
            "contact_info": contact
        },
        "top_issues": all_deductions[:5],
        "all_issues": all_deductions
    }


if __name__ == "__main__":
    sample_good = """
    Malik Taha
    Email: malik@example.com
    Phone: +92 300 1234567

    SUMMARY
    Cybersecurity student.

    EXPERIENCE
    Security Intern, Internee.pk
    Jan 2026 - Present
    - Built Wazuh SIEM deployment

    SKILLS
    Python, Flask, SQLite

    EDUCATION
    BS Cybersecurity, Sir Syed CASE Institute
    """
    result = calculate_ats_score(sample_good, "docx", [])
    print("Score:", result["ats_score"], "/", result["max_score"])
    print("Verdict:", result["verdict"])
    for issue in result["top_issues"]:
        print(" -", issue["issue"], f"(-{issue['points_lost']})")
