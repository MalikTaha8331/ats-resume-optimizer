/**
 * template_1_modern.js
 * "Modern" template: clean single-column layout, navy accent color, tagline under
 * name. Safe default choice - good balance of visual polish and ATS-safety.
 *
 * Input shape (passed in via stdin as JSON from the Python orchestrator):
 * {
 *   contact: { name, email, phone, location, linkedin, github },
 *   tagline: "SOC Analyst | Cybersecurity Professional",
 *   summary: "...",
 *   skills: ["Python", "Flask", ...],
 *   experience: [{ title, organization, dates, bullets: [...] }],
 *   projects: [{ name, description, bullets: [...] }],
 *   education: [{ degree, institution, dates, details }],
 *   certifications: ["..."]
 * }
 */

const { Document, Packer } = require("docx");
const {
  buildBulletNumbering, bulletParagraph, contactLine, sectionHeader,
  nameHeader, roleTagline, titleDateLine, bodyParagraph, skillsLine
} = require("./docx_helpers");

const ACCENT = "1F4E79"; // navy
const CONTENT_WIDTH = 9360; // US Letter, 1" margins

function buildDocument(data) {
  const children = [];

  children.push(nameHeader(data.contact.name, { color: "1A1A1A" }));
  if (data.tagline) children.push(roleTagline(data.tagline, { color: ACCENT }));
  children.push(contactLine(data.contact));

  if (data.summary) {
    children.push(sectionHeader("Professional Summary", { accentColor: ACCENT }));
    children.push(bodyParagraph(data.summary));
  }

  if (data.skills && data.skills.length) {
    children.push(sectionHeader("Skills", { accentColor: ACCENT }));
    children.push(skillsLine(data.skills));
  }

  if (data.experience && data.experience.length) {
    children.push(sectionHeader("Experience", { accentColor: ACCENT }));
    data.experience.forEach(exp => {
      children.push(titleDateLine(exp.title, exp.organization, exp.dates, CONTENT_WIDTH));
      (exp.bullets || []).forEach(b => children.push(bulletParagraph(b)));
    });
  }

  if (data.projects && data.projects.length) {
    children.push(sectionHeader("Projects", { accentColor: ACCENT }));
    data.projects.forEach(proj => {
      children.push(titleDateLine(proj.name, null, proj.dates, CONTENT_WIDTH));
      if (proj.description) children.push(bodyParagraph(proj.description, { after: 60 }));
      (proj.bullets || []).forEach(b => children.push(bulletParagraph(b)));
    });
  }

  if (data.education && data.education.length) {
    children.push(sectionHeader("Education", { accentColor: ACCENT }));
    data.education.forEach(edu => {
      children.push(titleDateLine(edu.degree, edu.institution, edu.dates, CONTENT_WIDTH));
      if (edu.details) children.push(bodyParagraph(edu.details, { after: 60, size: 20 }));
    });
  }

  if (data.certifications && data.certifications.length) {
    children.push(sectionHeader("Certifications", { accentColor: ACCENT }));
    children.push(skillsLine(data.certifications, { separator: "  •  " }));
  }

  return new Document({
    numbering: buildBulletNumbering(),
    styles: { default: { document: { run: { font: "Arial", size: 21 } } } },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1080, right: 1440, bottom: 1080, left: 1440 }
        }
      },
      children
    }]
  });
}

module.exports = { buildDocument };
