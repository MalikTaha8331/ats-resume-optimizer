"""
fact_checker.py
THE SAFETY LAYER. Validates that the rewritten CV doesn't contain claims absent
from the original CV's fact pool (plus any explicitly user-confirmed skills).

This does NOT trust the LLM's good behavior - it independently re-checks every
new piece of text using fuzzy matching against the verified fact pool.
Anything that looks new and unverified gets flagged for human review rather than
silently shipped. We fail safe: when in doubt, flag it, don't auto-pass it.
"""

from difflib import SequenceMatcher
import re


# Common resume filler words that will trivially "match" anything - excluded from
# new-claim detection so the checker focuses on substantive nouns (tools, skills, metrics)
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "as",
    "is", "are", "was", "were", "by", "at", "from", "this", "that", "using",
    "developed", "built", "designed", "implemented", "created", "managed", "led",
    "experienced", "skilled", "proficient", "knowledgeable", "strong", "solid",
    "responsible", "successfully", "effectively", "demonstrated", "passionate",
    "motivated", "dedicated", "i", "my"
}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).strip()


def fuzzy_in_pool(phrase: str, fact_pool: list, threshold: float = 0.55) -> bool:
    """
    Checks if `phrase` is reasonably supported by something in the fact pool,
    via substring match, token-level overlap, or whole-string fuzzy similarity.

    Token-level check matters for short tech terms like "RESTful" matching against
    a longer fact like "rest api design" - whole-string SequenceMatcher penalizes
    length differences too harshly for this case, so we also check if any single
    word in the fact pool entry is itself a strong match for the phrase.
    """
    norm_phrase = normalize(phrase)
    if not norm_phrase:
        return True  # empty string, nothing to check

    for fact in fact_pool:
        norm_fact = normalize(fact)
        if not norm_fact:
            continue

        if norm_phrase in norm_fact or norm_fact in norm_phrase:
            return True

        # Whole-string fuzzy similarity (catches close paraphrases of similar length)
        if SequenceMatcher(None, norm_phrase, norm_fact).ratio() >= threshold:
            return True

        # Token-level: does any individual word in the fact strongly match the phrase,
        # or share a long enough common root (handles "RESTful" vs "rest api design")
        for word in norm_fact.split():
            if len(word) < 3:
                continue
            if word in norm_phrase or norm_phrase in word:
                return True
            if SequenceMatcher(None, norm_phrase, word).ratio() >= 0.7:
                return True

    return False


def extract_candidate_keywords(text: str) -> list:
    """
    Pulls out likely 'claim-bearing' keywords from a rewritten bullet/sentence -
    capitalized tech terms, multi-word noun phrases - the things worth checking.
    This is intentionally simple/regex-based: precision over recall, since this
    is a safety net, not the primary extraction step.
    """
    candidates = re.findall(r"\b[A-Z][A-Za-z0-9+.#]*\b", text)
    return [c for c in candidates if c.lower() not in STOPWORDS and len(c) > 1]


def check_rewrite_for_fabrication(rewrite_result: dict, fact_pool: list,
                                    user_confirmed_skills: list) -> dict:
    """
    Main entry point. Scans every text field in the rewrite output and flags
    any keyword/phrase not traceable to fact_pool or user_confirmed_skills.

    Returns a report: { "is_clean": bool, "flags": [...] }
    Flags should be surfaced to the user/dev before the CV is finalized - this
    function does NOT silently delete content, because false positives are
    possible and a human (Malik, or the end user) should make the final call.
    """
    extended_pool = list(fact_pool) + [s.lower().strip() for s in user_confirmed_skills]
    flags = []

    def scan_field(label, text):
        if not text:
            return
        for keyword in extract_candidate_keywords(text):
            if not fuzzy_in_pool(keyword, extended_pool):
                flags.append({
                    "field": label,
                    "flagged_term": keyword,
                    "context": text,
                    "reason": "This term doesn't appear in the original CV or confirmed skills. "
                              "Verify it's a true elaboration, not a fabrication, before using."
                })

    scan_field("tailored_summary", rewrite_result.get("tailored_summary", ""))

    for skill in rewrite_result.get("reordered_skills", []):
        if not fuzzy_in_pool(skill, extended_pool):
            flags.append({
                "field": "reordered_skills",
                "flagged_term": skill,
                "context": skill,
                "reason": "This skill was not in the original CV's skill list or confirmed skills."
            })

    for exp in rewrite_result.get("rewritten_experience", []):
        for bullet in exp.get("bullets", []):
            scan_field("experience:" + exp.get("title", "unknown"), bullet)

    for proj in rewrite_result.get("rewritten_projects", []):
        for bullet in proj.get("bullets", []):
            scan_field("project:" + proj.get("name", "unknown"), bullet)

    seen = set()
    unique_flags = []
    for f in flags:
        key = f["flagged_term"].lower()
        if key not in seen:
            seen.add(key)
            unique_flags.append(f)

    return {
        "is_clean": len(unique_flags) == 0,
        "flag_count": len(unique_flags),
        "flags": unique_flags
    }


if __name__ == "__main__":
    fake_pool = ["python", "flask", "sqlite", "built async tcp scanner"]
    fake_rewrite = {
        "tailored_summary": "Experienced React and Kubernetes engineer skilled in Flask.",
        "reordered_skills": ["Python", "Flask", "React"],
        "rewritten_experience": [],
        "rewritten_projects": []
    }
    result = check_rewrite_for_fabrication(fake_rewrite, fake_pool, [])
    print("Clean:", result["is_clean"], "Flags:", result["flag_count"])
    for flag in result["flags"]:
        print(" -", flag["flagged_term"], ":", flag["reason"])
