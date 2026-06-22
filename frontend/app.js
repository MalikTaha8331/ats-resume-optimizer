/**
 * app.js
 * Drives the full flow: upload CV -> show ATS score -> JD input -> gap analysis
 * + confirmations -> rewrite + fact-check -> template selection -> download.
 *
 * No build step, no framework - plain DOM manipulation against the static
 * structure in index.html. Talks to the Flask backend via fetch().
 */

const API_BASE = "http://127.0.0.1:5000";

const state = {
  sessionId: null,
  atsScore: null,
  gapResult: null,
  confirmedSkills: [],   // [{ skill, evidence }]
  rewriteResult: null,
  selectedTemplates: new Set(["modern"]),
  downloadUrls: {}
};

const TEMPLATE_INFO = {
  modern: { name: "Modern", desc: "Clean, navy accents. Safe default." },
  minimal: { name: "Minimal", desc: "Pure black & white. Max compatibility." },
  technical: { name: "Technical", desc: "Skills-first. Built for IT/security roles." },
  executive: { name: "Executive", desc: "Formal serif, generous spacing." },
  compact: { name: "Compact", desc: "Tight spacing. Fits more on one page." }
};

// ---------- Utility ----------

function $(id) { return document.getElementById(id); }

function show(id) { $(id).classList.remove("hidden"); }
function hide(id) { $(id).classList.add("hidden"); }

function setStep(n) {
  document.querySelectorAll(".step").forEach(el => {
    const step = parseInt(el.dataset.step, 10);
    el.classList.remove("active", "done");
    if (step < n) el.classList.add("done");
    if (step === n) el.classList.add("active");
  });
}

function showError(message) {
  $("error-area").innerHTML = `<div class="error-banner">${escapeHtml(message)}</div>`;
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function clearError() {
  $("error-area").innerHTML = "";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function loadingLine(text) {
  return `<div class="loading-line"><span class="pulse-dot"></span>${escapeHtml(text)}</div>`;
}

async function apiCall(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  const body = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(body.error || `Request failed (${resp.status})`);
  }
  return body;
}

// ---------- Step 1: Upload ----------

let chosenFile = null;

function initDropzone() {
  const dz = $("dropzone");
  const input = $("file-input");

  dz.addEventListener("click", () => input.click());

  dz.addEventListener("dragover", (e) => {
    e.preventDefault();
    dz.classList.add("drag");
  });
  dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
  dz.addEventListener("drop", (e) => {
    e.preventDefault();
    dz.classList.remove("drag");
    if (e.dataTransfer.files.length) {
      setChosenFile(e.dataTransfer.files[0]);
    }
  });

  input.addEventListener("change", () => {
    if (input.files.length) setChosenFile(input.files[0]);
  });
}

function setChosenFile(file) {
  const allowed = ["pdf", "docx", "txt"];
  const ext = file.name.split(".").pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showError(`Unsupported file type ".${ext}". Use PDF, DOCX, or TXT.`);
    return;
  }
  chosenFile = file;
  $("file-chosen").textContent = `Selected: ${file.name}`;
  $("file-chosen").classList.remove("hidden");
  $("cv-text").value = ""; // file and pasted text are mutually exclusive in the UI
}

async function handleUpload() {
  clearError();
  const pastedText = $("cv-text").value.trim();

  if (!chosenFile && !pastedText) {
    showError("Upload a file or paste your CV text first.");
    return;
  }

  $("btn-upload").disabled = true;
  $("upload-loading").innerHTML = loadingLine("Extracting and verifying your CV...");

  try {
    let body;
    if (chosenFile) {
      const formData = new FormData();
      formData.append("cv_file", chosenFile);
      const resp = await fetch(`${API_BASE}/api/upload-cv`, { method: "POST", body: formData });
      body = await resp.json();
      if (!resp.ok) throw new Error(body.error || "Upload failed");
    } else {
      body = await apiCall("/api/upload-cv", {
        method: "POST",
        body: JSON.stringify({ cv_text: pastedText })
      });
    }

    state.sessionId = body.session_id;
    state.atsScore = body.ats_score;

    renderAtsScore(body.ats_score, body.extraction_warnings);
    show("panel-ats-score");
    show("panel-2");
    setStep(2);
    window.scrollTo({ top: document.getElementById("panel-ats-score").offsetTop - 20, behavior: "smooth" });

  } catch (err) {
    showError(err.message);
  } finally {
    $("btn-upload").disabled = false;
    $("upload-loading").innerHTML = "";
  }
}

function verdictClass(score) {
  if (score >= 80) return "verdict-good";
  if (score >= 60) return "verdict-mid";
  return "verdict-bad";
}

function renderAtsScore(ats, extractionWarnings) {
  let html = `
    <div class="score-block">
      <div class="score-number">${ats.ats_score}<span class="denom"> / ${ats.max_score}</span></div>
      <div class="score-meta">
        <span class="score-verdict ${verdictClass(ats.ats_score)}">${escapeHtml(ats.verdict)}</span>
      </div>
    </div>
  `;

  if (extractionWarnings && extractionWarnings.length) {
    extractionWarnings.forEach(w => {
      html += `<div class="evidence lose"><div class="ev-head">Extraction issue</div><div class="ev-detail">${escapeHtml(w)}</div></div>`;
    });
  }

  if (ats.top_issues && ats.top_issues.length) {
    ats.top_issues.forEach(issue => {
      html += `
        <div class="evidence lose">
          <div class="ev-head">
            <span>${escapeHtml(issue.issue)}</span>
            <span class="ev-points">-${issue.points_lost}</span>
          </div>
          <div class="ev-detail">${escapeHtml(issue.detail)}</div>
        </div>
      `;
    });
  } else {
    html += `<div class="evidence gain"><div class="ev-head">No formatting issues detected</div></div>`;
  }

  $("ats-score-content").innerHTML = html;
}

// ---------- Step 2: JD analysis ----------

async function handleAnalyzeJd() {
  clearError();
  const jdText = $("jd-text").value.trim();
  if (!jdText) {
    showError("Paste the job description first.");
    return;
  }

  $("btn-analyze-jd").disabled = true;
  $("jd-loading").innerHTML = loadingLine("Comparing your CV against this role...");

  try {
    const body = await apiCall("/api/analyze-jd", {
      method: "POST",
      body: JSON.stringify({ session_id: state.sessionId, jd_text: jdText })
    });

    state.gapResult = body.gap_result;
    renderGapAnalysis(body.gap_result, body.confirmation_questions);
    show("panel-3");
    setStep(3);
    window.scrollTo({ top: document.getElementById("panel-3").offsetTop - 20, behavior: "smooth" });

  } catch (err) {
    showError(err.message);
  } finally {
    $("btn-analyze-jd").disabled = false;
    $("jd-loading").innerHTML = "";
  }
}

function renderGapAnalysis(gap, confirmationQuestions) {
  $("gap-summary").textContent = `${gap.overall_match_percentage}% match — ${gap.summary}`;

  $("chips-present").innerHTML = (gap.matched_skills || []).map(s =>
    `<span class="chip present">${escapeHtml(s.skill)}</span>`
  ).join("") || `<span class="dz-sub">None matched directly.</span>`;

  $("chips-transferable").innerHTML = (gap.transferable_skills || []).map(s =>
    `<span class="chip transferable" title="${escapeHtml(s.connection_reasoning || "")}">${escapeHtml(s.skill)}</span>`
  ).join("") || `<span class="dz-sub">None identified.</span>`;

  $("chips-missing").innerHTML = (gap.missing_skills || []).map(s =>
    `<span class="chip missing">${escapeHtml(s.skill)}</span>`
  ).join("") || `<span class="dz-sub">No gaps found — strong match.</span>`;

  renderConfirmationQuestions(confirmationQuestions || []);
}

function renderConfirmationQuestions(questions) {
  const area = $("confirm-area");
  if (!questions.length) {
    area.innerHTML = "";
    return;
  }

  let html = `<div class="gap-section"><h4>Quick check before rewriting</h4>`;
  questions.forEach((q, idx) => {
    html += `
      <div class="confirm-card" id="confirm-card-${idx}">
        <div class="confirm-q">${escapeHtml(q.question)}</div>
        <div class="confirm-actions">
          <button class="btn secondary" data-action="yes" data-idx="${idx}">Yes, I have this</button>
          <button class="btn ghost" data-action="no" data-idx="${idx}">No / skip</button>
          <span class="confirm-status hidden" id="confirm-status-${idx}">Recorded</span>
        </div>
        <div class="confirm-evidence-input" id="confirm-evidence-${idx}">
          <input type="text" placeholder="Briefly, where from? (e.g. coursework, personal project)" id="confirm-evidence-input-${idx}">
          <div class="btn-row" style="margin-top:8px;">
            <button class="btn" style="padding:7px 14px;font-size:12.5px;" data-action="save-evidence" data-idx="${idx}" data-skill="${escapeHtml(q.skill)}">Save</button>
          </div>
        </div>
      </div>
    `;
  });
  html += `</div>`;
  area.innerHTML = html;

  area.querySelectorAll('[data-action="yes"]').forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = btn.dataset.idx;
      $(`confirm-evidence-${idx}`).classList.add("show");
    });
  });

  area.querySelectorAll('[data-action="no"]').forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = btn.dataset.idx;
      $(`confirm-evidence-${idx}`).classList.remove("show");
      const status = $(`confirm-status-${idx}`);
      status.textContent = "Skipped";
      status.classList.remove("hidden");
    });
  });

  area.querySelectorAll('[data-action="save-evidence"]').forEach(btn => {
    btn.addEventListener("click", () => {
      const idx = btn.dataset.idx;
      const skill = btn.dataset.skill;
      const evidence = $(`confirm-evidence-input-${idx}`).value.trim();
      if (!evidence) return;

      state.confirmedSkills.push({ skill, evidence });

      $(`confirm-evidence-${idx}`).classList.remove("show");
      const status = $(`confirm-status-${idx}`);
      status.textContent = "Confirmed";
      status.classList.remove("hidden");
    });
  });
}

async function handleGenerateRewrite() {
  clearError();

  $("btn-generate-rewrite").disabled = true;
  $("rewrite-loading").innerHTML = "";

  try {
    if (state.confirmedSkills.length) {
      await apiCall("/api/confirm-skills", {
        method: "POST",
        body: JSON.stringify({ session_id: state.sessionId, confirmed_skills: state.confirmedSkills })
      });
    }

    $("rewrite-loading").innerHTML = loadingLine("Rewriting your CV for this role...");

    const body = await apiCall("/api/rewrite", {
      method: "POST",
      body: JSON.stringify({ session_id: state.sessionId })
    });

    state.rewriteResult = body.rewrite_result;
    renderRewrite(body.rewrite_result);
    renderFactCheck(body.fact_check, body.warning);

    show("panel-4");
    show("panel-factcheck");
    renderTemplateGrid();
    show("panel-5");
    setStep(4);
    window.scrollTo({ top: document.getElementById("panel-4").offsetTop - 20, behavior: "smooth" });

  } catch (err) {
    showError(err.message);
  } finally {
    $("btn-generate-rewrite").disabled = false;
    $("rewrite-loading").innerHTML = "";
  }
}

function renderRewrite(rewrite) {
  $("rewrite-summary").textContent = rewrite.tailored_summary || "";
}

function renderFactCheck(factCheck, warning) {
  if (factCheck.is_clean) {
    $("factcheck-sub").textContent = "Every claim in the rewrite traces back to your original CV or a skill you confirmed.";
    $("factcheck-content").innerHTML = `<div class="evidence gain"><div class="ev-head">No unverifiable claims found</div></div>`;
    return;
  }

  $("factcheck-sub").textContent = warning || "Some terms in the rewrite need a second look before you use this CV.";
  $("factcheck-content").innerHTML = factCheck.flags.map(f => `
    <div class="evidence lose">
      <div class="ev-head"><span>${escapeHtml(f.flagged_term)}</span></div>
      <div class="ev-detail">${escapeHtml(f.reason)}</div>
      <div class="ev-detail" style="margin-top:4px;font-style:italic;">"…${escapeHtml(f.context)}…"</div>
    </div>
  `).join("");
}

// ---------- Step 5: Templates ----------

function renderTemplateGrid() {
  const grid = $("template-grid");
  grid.innerHTML = Object.entries(TEMPLATE_INFO).map(([key, info]) => `
    <div class="template-card ${state.selectedTemplates.has(key) ? "selected" : ""}" data-template="${key}">
      <div class="t-name">${info.name}</div>
      <div class="t-desc">${info.desc}</div>
      <div class="t-check">✓ Selected</div>
    </div>
  `).join("");

  grid.querySelectorAll(".template-card").forEach(card => {
    card.addEventListener("click", () => {
      const key = card.dataset.template;
      if (state.selectedTemplates.has(key)) {
        state.selectedTemplates.delete(key);
        card.classList.remove("selected");
      } else {
        state.selectedTemplates.add(key);
        card.classList.add("selected");
      }
    });
  });
}

async function handleGenerateTemplates() {
  clearError();

  if (state.selectedTemplates.size === 0) {
    showError("Select at least one template.");
    return;
  }

  $("btn-generate-templates").disabled = true;
  $("template-loading").innerHTML = loadingLine("Generating your CV files...");

  try {
    const body = await apiCall("/api/generate-templates", {
      method: "POST",
      body: JSON.stringify({
        session_id: state.sessionId,
        templates: Array.from(state.selectedTemplates),
        role_tagline: $("role-tagline").value.trim()
      })
    });

    state.downloadUrls = body.download_urls;
    renderDownloads(body.download_urls, body.errors, body.used_rewrite);

    show("panel-downloads");
    setStep(5);
    window.scrollTo({ top: document.getElementById("panel-downloads").offsetTop - 20, behavior: "smooth" });

  } catch (err) {
    showError(err.message);
  } finally {
    $("btn-generate-templates").disabled = false;
    $("template-loading").innerHTML = "";
  }
}

function renderDownloads(downloadUrls, errors, usedRewrite) {
  let html = "";

  if (!usedRewrite) {
    html += `<div class="evidence neutral"><div class="ev-head">Heads up</div><div class="ev-detail">These files use your original CV content — no rewrite was applied.</div></div>`;
  }

  Object.entries(downloadUrls || {}).forEach(([name, url]) => {
    html += `
      <div class="download-row">
        <span class="d-name">${escapeHtml(TEMPLATE_INFO[name]?.name || name)}</span>
        <a class="d-link" href="${API_BASE}${url}" target="_blank">Download .docx</a>
      </div>
    `;
  });

  if (errors && Object.keys(errors).length) {
    Object.entries(errors).forEach(([name, msg]) => {
      html += `<div class="evidence lose"><div class="ev-head">${escapeHtml(name)} failed</div><div class="ev-detail">${escapeHtml(msg)}</div></div>`;
    });
  }

  $("downloads-content").innerHTML = html;
}

// ---------- Start over ----------

function handleStartOver() {
  // Keep the same CV/session - just reset the JD-dependent steps so the user
  // can retarget toward a different role without re-uploading their CV.
  state.gapResult = null;
  state.confirmedSkills = [];
  state.rewriteResult = null;
  state.downloadUrls = {};

  $("jd-text").value = "";
  $("role-tagline").value = "";
  $("confirm-area").innerHTML = "";

  hide("panel-4");
  hide("panel-factcheck");
  hide("panel-5");
  hide("panel-downloads");
  show("panel-2");
  setStep(2);
  clearError();
  window.scrollTo({ top: document.getElementById("panel-2").offsetTop - 20, behavior: "smooth" });
}

// ---------- Init ----------

document.addEventListener("DOMContentLoaded", () => {
  initDropzone();
  $("btn-upload").addEventListener("click", handleUpload);
  $("btn-analyze-jd").addEventListener("click", handleAnalyzeJd);
  $("btn-generate-rewrite").addEventListener("click", handleGenerateRewrite);
  $("btn-generate-templates").addEventListener("click", handleGenerateTemplates);
  $("btn-start-over").addEventListener("click", handleStartOver);
});
