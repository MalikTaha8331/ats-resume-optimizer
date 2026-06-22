"""
Test suite for ats_rules.py - verifies the deterministic scoring catches real
issues without false-positiving on clean resumes.
"""
import sys
sys.path.insert(0, ".")
from ats_engine.ats_rules import calculate_ats_score

print("=" * 60)
print("TEST 1: Clean, well-formatted resume (expect high score)")
print("=" * 60)
clean = """
Malik Taha
Email: malik@example.com
Phone: +92 300 1234567
LinkedIn: linkedin.com/in/malik-taha-cyber-expert

PROFESSIONAL SUMMARY
Cybersecurity student specializing in AI-powered security tools.

EXPERIENCE
Security Intern, Internee.pk
Jan 2026 - Present
- Built Wazuh SIEM deployment with Kali Linux manager and Windows endpoint
- Configured log monitoring and alert rules

PROJECTS
NetSentinel AI
- Built async TCP scanner with banner grabbing using Python and Flask
- Designed REST API architecture with bcrypt authentication
- Trained Random Forest model achieving 99.58% accuracy on NSL-KDD dataset

SKILLS
Python, Flask, SQLite, Async Programming, Machine Learning, Wazuh, Kali Linux

EDUCATION
BS Cybersecurity, Sir Syed CASE Institute of Technology
Aug 2022 - Present
"""
result = calculate_ats_score(clean, "docx", [])
print(f"Score: {result['ats_score']}/{result['max_score']} - {result['verdict']}")
for issue in result["top_issues"]:
    print(f"  - {issue['issue']} (-{issue['points_lost']})")

print()
print("=" * 60)
print("TEST 2: Broken resume - icons, apostrophe dates, creative headers")
print("=" * 60)
broken = """
Malik Taha
📞 0300-1234567  📧 malik@example.com

★ MY JOURNEY ★
Cybersecurity enthusiast.

THE TOOLKIT
Python ★ Flask ★ SQL

Security Intern - Internee.pk
'23 - Present
➤ Built SIEM deployment
"""
result = calculate_ats_score(broken, "pdf", [])
print(f"Score: {result['ats_score']}/{result['max_score']} - {result['verdict']}")
for issue in result["top_issues"]:
    print(f"  - {issue['issue']} (-{issue['points_lost']})")

print()
print("=" * 60)
print("TEST 3: Image-based PDF (extraction failed completely)")
print("=" * 60)
result = calculate_ats_score("", "pdf", ["No extractable text found in PDF."])
print(f"Score: {result['ats_score']}/{result['max_score']} - {result['verdict']}")
for issue in result["top_issues"]:
    print(f"  - {issue['issue']} (-{issue['points_lost']})")

print()
print("=" * 60)
print("TEST 4: Mixed date formats")
print("=" * 60)
mixed_dates = """
EXPERIENCE
Job One
Jan 2022 - Mar 2023
- Did things

EDUCATION
Some University
01/2020 - 12/2024

SKILLS
Python, SQL
"""
result = calculate_ats_score(mixed_dates, "docx", [])
print(f"Score: {result['ats_score']}/{result['max_score']} - {result['verdict']}")
for issue in result["top_issues"]:
    print(f"  - {issue['issue']} (-{issue['points_lost']})")
