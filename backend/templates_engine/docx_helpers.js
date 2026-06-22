/**
 * docx_helpers.js
 * Shared building blocks for all CV templates. Centralizing these means every
 * template automatically inherits the same ATS-safety guarantees:
 *   - single column, no tables-as-layout, no text boxes
 *   - proper LevelFormat.BULLET numbering (never raw unicode bullets)
 *   - standard web-safe fonts
 *   - contact info as plain paragraph text (not header/footer, which some
 *     parsers skip entirely)
 *
 * Each template (template_1_modern.js, etc.) imports from here and only
 * varies color, font choice, and spacing - never the underlying ATS-safe structure.
 */

const {
  Paragraph, TextRun, AlignmentType, BorderStyle, LevelFormat, TabStopType, TabStopPosition
} = require("docx");

/**
 * Builds the numbering config block every template needs for bullets.
 * Using a single shared reference name "cvBullets" so all templates behave
 * identically here - ATS parsers don't care about bullet styling specifics,
 * just that it's real list markup, not typed unicode characters.
 */
function buildBulletNumbering() {
  return {
    config: [
      {
        reference: "cvBullets",
        levels: [
          {
            level: 0,
            format: LevelFormat.BULLET,
            text: "\u2022",
            alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 360, hanging: 270 } } }
          }
        ]
      }
    ]
  };
}

/** A single bullet paragraph using real list numbering (never raw "• text"). */
function bulletParagraph(text, opts = {}) {
  return new Paragraph({
    numbering: { reference: "cvBullets", level: 0 },
    spacing: { after: opts.after ?? 60 },
    children: [new TextRun({ text, size: opts.size ?? 21, font: opts.font ?? "Arial" })]
  });
}

/**
 * Contact info line as PLAIN BODY TEXT (not header/footer - many ATS parsers
 * skip header/footer content entirely, per 2026 parsing research). URLs are
 * written out in full, never as "Click Here" style hyperlink text, so the
 * parser can read them even if it strips hyperlink formatting.
 */
function contactLine(contact, opts = {}) {
  const parts = [];
  if (contact.email) parts.push(`Email: ${contact.email}`);
  if (contact.phone) parts.push(`Phone: ${contact.phone}`);
  if (contact.location) parts.push(contact.location);
  if (contact.linkedin) parts.push(`LinkedIn: ${contact.linkedin}`);
  if (contact.github) parts.push(`GitHub: ${contact.github}`);

  return new Paragraph({
    alignment: opts.alignment ?? AlignmentType.CENTER,
    spacing: { after: 200 },
    children: [
      new TextRun({
        text: parts.join("  |  "),
        size: opts.size ?? 19,
        font: opts.font ?? "Arial",
        color: opts.color ?? "404040"
      })
    ]
  });
}

/**
 * Section header using a STANDARD label (Experience, Education, Skills, etc.)
 * required verbatim - never a "creative" rename - since ATS categorization
 * logic keys off these exact standard terms.
 */
function sectionHeader(label, opts = {}) {
  return new Paragraph({
    spacing: { before: opts.before ?? 240, after: opts.after ?? 100 },
    border: opts.noBorder ? undefined : {
      bottom: { style: BorderStyle.SINGLE, size: 6, color: opts.accentColor ?? "2E5C8A", space: 2 }
    },
    children: [
      new TextRun({
        text: label.toUpperCase(),
        bold: true,
        size: opts.size ?? 24,
        font: opts.font ?? "Arial",
        color: opts.headerColor ?? opts.accentColor ?? "2E5C8A",
        characterSpacing: opts.letterSpacing ?? undefined
      })
    ]
  });
}

/** Candidate's name as the document title - plain text, no text box, no image. */
function nameHeader(name, opts = {}) {
  return new Paragraph({
    alignment: opts.alignment ?? AlignmentType.CENTER,
    spacing: { after: opts.after ?? 40 },
    children: [
      new TextRun({
        text: name,
        bold: true,
        size: opts.size ?? 40,
        font: opts.font ?? "Arial",
        color: opts.color ?? "1A1A1A"
      })
    ]
  });
}

/** Role title line under the name (e.g. "SOC Analyst | Cybersecurity Professional"). */
function roleTagline(tagline, opts = {}) {
  return new Paragraph({
    alignment: opts.alignment ?? AlignmentType.CENTER,
    spacing: { after: 160 },
    children: [
      new TextRun({
        text: tagline,
        size: opts.size ?? 22,
        font: opts.font ?? "Arial",
        color: opts.color ?? "2E5C8A",
        italics: opts.italics ?? false
      })
    ]
  });
}

/**
 * A job/project title line with a right-aligned date, using a TAB STOP
 * (not a table) - tables-as-layout are an ATS risk per the SKILL.md guidance,
 * tab stops achieve the same visual result safely.
 */
function titleDateLine(title, subtitle, dateRange, pageContentWidth, opts = {}) {
  return new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: pageContentWidth }],
    spacing: { before: opts.before ?? 160, after: 20 },
    children: [
      new TextRun({ text: title, bold: true, size: opts.size ?? 22, font: opts.font ?? "Arial" }),
      new TextRun({ text: subtitle ? `, ${subtitle}` : "", size: opts.size ?? 22, font: opts.font ?? "Arial" }),
      new TextRun({ text: "\t" + (dateRange || ""), size: opts.dateSize ?? 20, font: opts.font ?? "Arial", color: "595959" })
    ]
  });
}

/** Plain paragraph for summary text - body text only, never in a text box. */
function bodyParagraph(text, opts = {}) {
  return new Paragraph({
    spacing: { after: opts.after ?? 160 },
    children: [new TextRun({ text, size: opts.size ?? 21, font: opts.font ?? "Arial" })]
  });
}

/** Comma/pipe-separated skills line - explicitly NOT a table, per ATS guidance. */
function skillsLine(skills, opts = {}) {
  return new Paragraph({
    spacing: { after: 160 },
    children: [
      new TextRun({
        text: skills.join(opts.separator ?? "  •  "),
        size: opts.size ?? 21,
        font: opts.font ?? "Arial"
      })
    ]
  });
}

module.exports = {
  buildBulletNumbering,
  bulletParagraph,
  contactLine,
  sectionHeader,
  nameHeader,
  roleTagline,
  titleDateLine,
  bodyParagraph,
  skillsLine
};
