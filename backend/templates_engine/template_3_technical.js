/**
 * template_3_technical.js
 * "Technical" template: SKILLS section placed immediately after summary, before
 * experience - common convention in tech/security hiring where recruiters and
 * automated keyword scans often weight the skills block heavily up top.
 * Slate/teal accent color, slightly condensed spacing to fit more technical detail.
 */

const { Document } = require("docx");
const {
  buildBulletNumbering, bulletParagraph, contactLine, sectionHeader,
  nameHeader, roleTagline, titleDateLine, bodyParagraph, skillsLine
} = require("./docx_helpers");

const ACCENT = "0F5C5C"; // dark teal/slate
const CONTENT_WIDTH = 9360;

function buildDocument(data) {
  const children = [];

  children.push(nameHeader(data.contact.name, { color: "1A1A1A", size: 36 }));
  if (data.tagline) children.push(roleTagline(data.tagline, { color: ACCENT, size: 21 }));
  children.push(contactLine(data.contact, { size: 18 }));

  if (data.summary) {
    children.push(sectionHeader("Summary", { accentColor: ACCENT, size: 22 }));
    children.push(bodyParagraph(data.summary, { size: 20, after: 120 }));
  }

  // Skills placed early and prominently - this is the key structural difference
  // for this template, matching how technical recruiters and keyword scanners
  // tend to prioritize this section for IT/security/engineering roles.
  if (data.skills && data.skills.length) {
    children.push(sectionHeader("Technical Skills", { accentColor: ACCENT, size: 22 }));
    children.push(skillsLine(data.skills, { separator: "  |  ", size: 20 }));
  }

  if (data.certifications && data.certifications.length) {
    children.push(sectionHeader("Certifications", { accentColor: ACCENT, size: 22 }));
    children.push(skillsLine(data.certifications, { separator: "  |  ", size: 20 }));
  }

  if (data.projects && data.projects.length) {
    children.push(sectionHeader("Projects", { accentColor: ACCENT, size: 22 }));
    data.projects.forEach(proj => {
      children.push(titleDateLine(proj.name, null, proj.dates, CONTENT_WIDTH, { size: 21, before: 120 }));
      if (proj.description) children.push(bodyParagraph(proj.description, { after: 40, size: 20 }));
      (proj.bullets || []).forEach(b => children.push(bulletParagraph(b, { size: 20, after: 40 })));
    });
  }

  if (data.experience && data.experience.length) {
    children.push(sectionHeader("Experience", { accentColor: ACCENT, size: 22 }));
    data.experience.forEach(exp => {
      children.push(titleDateLine(exp.title, exp.organization, exp.dates, CONTENT_WIDTH, { size: 21, before: 120 }));
      (exp.bullets || []).forEach(b => children.push(bulletParagraph(b, { size: 20, after: 40 })));
    });
  }

  if (data.education && data.education.length) {
    children.push(sectionHeader("Education", { accentColor: ACCENT, size: 22 }));
    data.education.forEach(edu => {
      children.push(titleDateLine(edu.degree, edu.institution, edu.dates, CONTENT_WIDTH, { size: 21, before: 120 }));
      if (edu.details) children.push(bodyParagraph(edu.details, { after: 40, size: 19 }));
    });
  }

  return new Document({
    numbering: buildBulletNumbering(),
    styles: { default: { document: { run: { font: "Calibri", size: 20 } } } },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 900, right: 1260, bottom: 900, left: 1260 }
        }
      },
      children
    }]
  });
}

module.exports = { buildDocument };
