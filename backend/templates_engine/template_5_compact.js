/**
 * template_5_compact.js
 * "Compact" template: tightest spacing of all 5 templates, designed to fit
 * entry-level CVs (limited work history, multiple projects, education) onto
 * a single page without looking sparse or cramped. Smaller margins, smaller
 * section gaps, slightly smaller font - all still within the 10-12pt body /
 * 10pt-minimum ATS-safe range per 2026 formatting guidance.
 */

const { Document } = require("docx");
const {
  buildBulletNumbering, bulletParagraph, contactLine, sectionHeader,
  nameHeader, titleDateLine, bodyParagraph, skillsLine
} = require("./docx_helpers");

const CONTENT_WIDTH = 9700;

function buildDocument(data) {
  const children = [];

  children.push(nameHeader(data.contact.name, { color: "1A1A1A", size: 32, after: 20 }));
  children.push(contactLine(data.contact, { size: 18 }));

  if (data.tagline) {
    children.push(bodyParagraph(data.tagline, { size: 19, after: 100 }));
  }

  if (data.summary) {
    children.push(sectionHeader("Summary", { headerColor: "1A1A1A", size: 20, before: 140, after: 60 }));
    children.push(bodyParagraph(data.summary, { size: 19, after: 100 }));
  }

  if (data.skills && data.skills.length) {
    children.push(sectionHeader("Skills", { headerColor: "1A1A1A", size: 20, before: 140, after: 60 }));
    children.push(skillsLine(data.skills, { separator: ", ", size: 19 }));
  }

  if (data.education && data.education.length) {
    children.push(sectionHeader("Education", { headerColor: "1A1A1A", size: 20, before: 140, after: 60 }));
    data.education.forEach(edu => {
      children.push(titleDateLine(edu.degree, edu.institution, edu.dates, CONTENT_WIDTH, { size: 19, before: 60 }));
      if (edu.details) children.push(bodyParagraph(edu.details, { after: 40, size: 18 }));
    });
  }

  if (data.projects && data.projects.length) {
    children.push(sectionHeader("Projects", { headerColor: "1A1A1A", size: 20, before: 140, after: 60 }));
    data.projects.forEach(proj => {
      children.push(titleDateLine(proj.name, null, proj.dates, CONTENT_WIDTH, { size: 19, before: 60 }));
      if (proj.description) children.push(bodyParagraph(proj.description, { after: 20, size: 18 }));
      (proj.bullets || []).forEach(b => children.push(bulletParagraph(b, { size: 18, after: 20 })));
    });
  }

  if (data.experience && data.experience.length) {
    children.push(sectionHeader("Experience", { headerColor: "1A1A1A", size: 20, before: 140, after: 60 }));
    data.experience.forEach(exp => {
      children.push(titleDateLine(exp.title, exp.organization, exp.dates, CONTENT_WIDTH, { size: 19, before: 60 }));
      (exp.bullets || []).forEach(b => children.push(bulletParagraph(b, { size: 18, after: 20 })));
    });
  }

  if (data.certifications && data.certifications.length) {
    children.push(sectionHeader("Certifications", { headerColor: "1A1A1A", size: 20, before: 140, after: 60 }));
    children.push(skillsLine(data.certifications, { separator: ", ", size: 19 }));
  }

  return new Document({
    numbering: buildBulletNumbering(),
    styles: { default: { document: { run: { font: "Calibri", size: 19 } } } },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 620, right: 900, bottom: 620, left: 900 }
        }
      },
      children
    }]
  });
}

module.exports = { buildDocument };
