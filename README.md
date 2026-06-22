# ATS Resume Optimizer

AI-powered CV optimizer: upload a CV, paste a target job description, and get:
1. A deterministic, explainable **ATS compatibility score** (formatting/parsability)
2. A **gap analysis** vs. the job description (present / transferable / missing skills)
3. A **JD-tailored rewrite** of your CV content — built with a fabrication guard so the
   AI can only reframe real experience, never invent new skills/tools/employers
4. **5 ATS-safe DOCX templates** (Modern, Minimal, Technical, Executive, Compact) generated
   from the tailored content, downloadable from the browser

### Why this exists

Most "AI resume builder" tools either give you a black-box score with no explanation,
or happily invent skills you don't have to pad your match rate. This project takes the
opposite approach on both counts: the ATS score is fully rule-based and explainable
(every point lost has a stated reason, grounded in how real ATS platforms like Workday,
Greenhouse, and iCIMS actually parse documents), and the AI rewrite layer is constrained
by a deterministic fact-checker that independently re-verifies every claim in the output
against the original CV — so it can reframe your real experience toward a new role, but
it can't fabricate new ones.

> **Note:** Running this yourself requires your own free Groq API key (see Setup
> below). Nobody's key is shared or bundled — that's intentional, both for security
> and so usage costs/limits are yours alone, not tied to mine.

## Project structure

```
backend/
  app.py                     Flask app, all API routes, CORS enabled
  requirements.txt
  parsers/
    cv_extractor.py          Extracts raw text from PDF/DOCX/pasted text
    fact_extractor.py        Structures CV text into verified facts (LLM, extraction-only)
    jd_extractor.py          Structures job description into requirements (LLM)
    gap_analyzer.py          Classifies JD skills as present/transferable/missing (LLM)
    rewriter.py              Generates JD-tailored CV content (LLM, fact-constrained)
    fact_checker.py          Deterministic fabrication guard - re-checks rewrite output
                             against the original CV's fact pool
  ats_engine/
    ats_rules.py             Deterministic ATS formatting/parsability scoring (no LLM)
  templates_engine/
    docx_helpers.js          Shared ATS-safe docx building blocks
    template_1_modern.js
    template_2_minimal.js
    template_3_technical.js
    template_4_executive.js
    template_5_compact.js
    render.js                CLI: node render.js <template> <input.json> <output.docx>
    template_renderer.py     Python bridge: session data -> template JSON -> Node render
    sample_data.json         Example CV data for testing templates
  test_routes.py             Structural route tests (no API key needed)
  test_e2e_mocked.py         Full pipeline test with mocked Groq responses
  test_ats_rules.py          ATS scoring test cases (clean/broken/edge-case resumes)
frontend/
  index.html                 Single-page UI (upload -> JD -> gap analysis -> rewrite -> download)
  app.js                     All client logic, talks to the Flask API via fetch()
```

## Setup

### 1. Get a free Groq API key

This project calls the Groq API to run the AI extraction/rewrite steps. You need
your own key — it's free and takes about a minute:

1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (no credit card required)
3. Go to **API Keys** → **Create API Key**
4. Copy the key (starts with `gsk_...`) — you won't be able to see it again later,
   so save it somewhere safe (a password manager, not a text file in this repo!)

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
npm install -g docx
```

### 3. Set your API key and run

The key is set as an environment variable for your terminal session — it never
goes in any file, so it's never at risk of being committed to git.

**macOS / Linux:**
```bash
export GROQ_API_KEY="your-key-here"
python3 app.py
```

**Windows (Command Prompt):**
```cmd
set GROQ_API_KEY=your-key-here
python3 app.py
```

**Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="your-key-here"
python3 app.py
```

The server runs on `http://127.0.0.1:5000`. Note that `export`/`set` only lasts
for that terminal session — you'll need to set it again each time you open a new
terminal, unless you persist it (`setx GROQ_API_KEY "..."` on Windows, or add the
`export` line to your shell profile on macOS/Linux).

**Important:** run with the auto-reloader disabled (already set in `app.py` via
`use_reloader=False`). The default Flask reloader watches your whole filesystem
and can get stuck restarting if other tools touch nearby files - keeping it off
avoids that.

In a separate terminal, serve the frontend as static files:

```bash
cd frontend
python3 -m http.server 5500
```

Then open **http://127.0.0.1:5500/index.html** in your browser. The frontend calls
the backend at `http://127.0.0.1:5000` (hardcoded as `API_BASE` in `app.js` - change
this if you deploy the backend elsewhere).

## Using the app

1. Paste your CV text or upload a PDF/DOCX/TXT file → see your ATS compatibility score
   with a full breakdown of what's costing you points and why
2. Paste the job description you're targeting → see how your CV stacks up: what's
   already there, what's transferable, what's genuinely missing
3. If a required skill is missing, you'll get a one-question check: do you actually
   have it (just unlisted)? Confirm with brief evidence, or skip it
4. Generate the tailored rewrite → see the new summary and a fact-check report
   confirming nothing was invented
5. Pick one or more of the 5 templates → download real `.docx` files

## API flow (if calling the backend directly)

1. `POST /api/upload-cv` — `{ cv_text: "..." }` or multipart file under `cv_file`
   → returns `session_id`, structured `cv_facts`, and `ats_score`
2. `POST /api/analyze-jd` — `{ session_id, jd_text }`
   → returns `jd_requirements`, `gap_result`, `confirmation_questions`
3. `POST /api/confirm-skills` — `{ session_id, confirmed_skills: [{skill, evidence}] }`
   (optional — only needed if you want to confirm skills missing from the original CV)
4. `POST /api/rewrite` — `{ session_id }`
   → returns `rewrite_result` and `fact_check` (flags anything unverifiable)
5. `POST /api/generate-templates` — `{ session_id, templates: [...], role_tagline: "..." }`
   → returns `download_urls` mapping template name -> `/api/download/<session_id>/<template>`
6. `GET /api/download/<session_id>/<template_name>` — streams the generated `.docx` file

## Running tests

```bash
cd backend
python3 test_routes.py        # routing/error-handling sanity checks
python3 test_e2e_mocked.py    # full pipeline, mocked LLM responses
python3 test_ats_rules.py     # ATS scoring calibration checks
```

## Design principles

- **Reframe, don't fabricate.** The rewrite engine only reorders/re-words real CV
  content. New skills can only enter via explicit user confirmation
  (`/api/confirm-skills`), never silently injected by the AI.
- **ATS scoring is deterministic, not AI-guessed.** `ats_rules.py` has zero LLM calls —
  every point lost has a plain-English, reproducible reason, grounded in how real
  ATS platforms (Workday, Greenhouse, iCIMS, Taleo) actually parse documents.
- **All 5 templates are ATS-safe by construction.** Single column, no tables-as-layout,
  no text boxes, real bullet-list markup (not typed unicode characters), standard
  section headers, web-safe fonts.
- **The frontend makes explainability visible.** Every score deduction and fact-check
  flag is shown with its reasoning inline ("evidence" blocks), not just a final number.

## Known limitations / not yet built

- Session storage is in-memory only - restarting the Flask server loses all sessions
- No authentication/multi-user support - this is a single-session demo tool
- The frontend's `API_BASE` is hardcoded to `localhost:5000` - update it before
  deploying the backend anywhere else

