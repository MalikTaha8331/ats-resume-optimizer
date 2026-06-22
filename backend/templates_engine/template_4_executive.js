/**
 * template_4_executive.js
 * "Executive" template: more generous spacing, Georgia font for a formal,
 * traditional feel. Georgia is a websafe serif explicitly recommended in
 * 2026 ATS formatting guidance alongside Arial/Calibri, so this keeps the
 * ATS-safety of the other templates while reading as more senior/polished.
 */

const { Document } = require("docx");
const {
  buildBulletNumbering, bulletParagraph, contactLine, sectionHeader,
  nameHeader, roleTagline, titleDateLine, bodyParagraph, skillsLine
} = require("./docx_helpers");

const ACCENT = "4A2E2E"; // deep maroon/brown, formal
const FONT = "Georgia";
const CONTENT_WIDTH = 9360;

function buildDocument(data) {
  const children = [];

  children.push(nameHeader(data.contact.name, { color: "1A1A1A", size: 40, font: FONT }));
  if (data.tagline) children.push(roleTagline(data.tagline, { color: ACCENT, font: FONT, size: 22 }));
  children.push(contactLine(data.contact, { font: FONT, size: 19 }));

  if (data.summary) {
    children.push(sectionHeader("Executive Summary", { accentColor: ACCENT, font: FONT, before: 280 }));
    children.push(bodyParagraph(data.summary, { font: FONT, after: 200 }));
  }

  if (data.experience && data.experience.length) {
    children.push(sectionHeader("Professional Experience", { accentColor: ACCENT, font: FONT, before: 280 }));
    data.experience.forEach(exp => {
      children.push(titleDateLine(exp.title, exp.organization, exp.dates, CONTENT_WIDTH, { font: FONT, before: 200 }));
      (exp.bullets || []).forEach(b => children.push(bulletParagraph(b, { font: FONT, after: 90 })));
    });
  }

  if (data.projects && data.projects.length) {
    children.push(sectionHeader("Key Projects", { accentColor: ACCENT, font: FONT, before: 280 }));
    data.projects.forEach(proj => {
      children.push(titleDateLine(proj.name, null, proj.dates, CONTENT_WIDTH, { font: FONT, before: 200 }));
      if (proj.description) children.push(bodyParagraph(proj.description, { font: FONT, after: 80 }));
      (proj.bullets || []).forEach(b => children.push(bulletParagraph(b, { font: FONT, after: 90 })));
    });
  }

  if (data.skills && data.skills.length) {
    children.push(sectionHeader("Core Competencies", { accentColor: ACCENT, font: FONT, before: 280 }));
    children.push(skillsLine(data.skills, { font: FONT, separator: "   •   " }));
  }

  if (data.education && data.education.length) {
    children.push(sectionHeader("Education", { accentColor: ACCENT, font: FONT, before: 280 }));
    data.education.forEach(edu => {
      children.push(titleDateLine(edu.degree, edu.institution, edu.dates, CONTENT_WIDTH, { font: FONT, before: 200 }));
      if (edu.details) children.push(bodyParagraph(edu.details, { font: FONT, after: 80, size: 20 }));
    });
  }

  if (data.certifications && data.certifications.length) {
    children.push(sectionHeader("Certifications", { accentColor: ACCENT, font: FONT, before: 280 }));
    children.push(skillsLine(data.certifications, { font: FONT, separator: "   •   " }));
  }

  return new Document({
    numbering: buildBulletNumbering(),
    styles: { default: { document: { run: { font: FONT, size: 21 } } } },
    sections: [{
      properties: {
        page: {
          size: { width: 12240, height: 15840 },
          margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 }
        }
      },
      children
    }]
  });
}

module.exports = { buildDocument };
