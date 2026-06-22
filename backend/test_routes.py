"""
Quick structural test using Flask's built-in test client.
Verifies routes respond correctly without needing a live GROQ_API_KEY
(we expect a clean 500 error on the LLM call, not a crash).
"""
import sys
sys.path.insert(0, ".")

from app import app

client = app.test_client()

print("=== /api/health ===")
resp = client.get("/api/health")
print(resp.status_code, resp.get_json())

print("\n=== /api/upload-cv (no GROQ key set) ===")
resp = client.post("/api/upload-cv", json={"cv_text": "John Doe\nSkills: Python, Flask"})
print(resp.status_code, resp.get_json())

print("\n=== /api/upload-cv (no cv_text/file) ===")
resp = client.post("/api/upload-cv", json={})
print(resp.status_code, resp.get_json())

print("\n=== /api/analyze-jd (invalid session) ===")
resp = client.post("/api/analyze-jd", json={"session_id": "fake-id", "jd_text": "Need Python dev"})
print(resp.status_code, resp.get_json())

print("\n=== /api/session/<bad-id> ===")
resp = client.get("/api/session/does-not-exist")
print(resp.status_code, resp.get_json())
