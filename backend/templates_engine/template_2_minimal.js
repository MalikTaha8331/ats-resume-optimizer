/**
 * template_2_minimal.js
 * "Minimal" template: zero color, no decorative borders, smallest visual footprint.
 * This is the MOST conservative option - recommended when applying through very
 * old/strict ATS portals (e.g. legacy Taleo instances) where even subtle styling
 * choices carry more (theoretical) risk. Visually plain by design, not by mistake.
 */

const { Document } = require("docx");
const {
  buildBulletNumbering, bulletParagraph, contactLine, sectionHeader,
  nameHeader, titleDateLine, bodyParagraph, skillsLine
} = require("./docx_helpers");

const CONTENT_WIDTH = 9360;

function buildDocument(data) {
  const children = [];

  children.push(nameHeader(data.contact.name, { color: "000000", size: 36 }));
  children.push(contactLine(data.contact, { color: "000000", alignment: "left" }));

  if (data.tagline) {
    children.push(bodyParagraph(data.tagline, { after: 160 }));
  }

  if (data.summary) {
    children.push(sectionHeader("Summary", { noBorder: true, headerColor: "000000" }));
    children.push(bodyParagraph(data.summary));
  }

  if (data.skills && data.skills.length) {
    children.push(sectionHeader("Skills", { noBorder: true, headerColor: "000000" }));
    children.push(skillsLine(data.skills, { separator: ", " }));
  }

  if (data.experience && data.experience.length) {
    children.push(sectionHeader("Experience", { noBorder: true, headerColor: "000000" }));
    data.experience.forEach(exp => {
      children.push(titleDateLine(exp.title, exp.organization, exp.dates, CONTENT_WIDTH));
      (exp.bullets || []).forEach(b => children.push(bulletParagraph(b)));
    });
  }

  if (data.projects && data.projects.length) {
    children.push(sectionHeader("Projects", { noBorder: true, headerColor: "000000" }));
    data.projects.forEach(proj => {
      children.push(titleDateLine(proj.name, null, proj.dates, CONTENT_WIDTH));
      if (proj.description) children.push(bodyParagraph(proj.description, { after: 60 }));
      (proj.bullets || []).forEach(b => children.push(bulletParagraph(b)));
    });
  }

  if (data.education && data.education.length) {
    children.push(sectionHeader("Education", { noBorder: true, headerColor: "000000" }));
    data.education.forEach(edu => {
      children.push(titleDateLine(edu.degree, edu.institution, edu.dates, CONTENT_WIDTH));
      if (edu.details) children.push(bodyParagraph(edu.details, { after: 60, size: 20 }));
    });
  }

  if (data.certifications && data.certifications.length) {
    children.push(sectionHeader("Certifications", { noBorder: true, headerColor: "000000" }));
    children.push(skillsLine(data.certifications, { separator: ", " }));
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
