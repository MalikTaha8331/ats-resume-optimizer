/**
 * render.js
 * CLI entry point: node render.js <template_name> <input_json_path> <output_docx_path>
 *
 * template_name: one of modern | minimal | technical | executive | compact
 */

const fs = require("fs");
const { Packer } = require("docx");

const TEMPLATES = {
  modern: require("./template_1_modern"),
  minimal: require("./template_2_minimal"),
  technical: require("./template_3_technical"),
  executive: require("./template_4_executive"),
  compact: require("./template_5_compact")
};

async function main() {
  const [templateName, inputPath, outputPath] = process.argv.slice(2);

  if (!templateName || !inputPath || !outputPath) {
    console.error("Usage: node render.js <template_name> <input_json_path> <output_docx_path>");
    console.error("template_name must be one of:", Object.keys(TEMPLATES).join(", "));
    process.exit(1);
  }

  const template = TEMPLATES[templateName];
  if (!template) {
    console.error(`Unknown template "${templateName}". Must be one of:`, Object.keys(TEMPLATES).join(", "));
    process.exit(1);
  }

  const data = JSON.parse(fs.readFileSync(inputPath, "utf-8"));
  const doc = template.buildDocument(data);
  const buffer = await Packer.toBuffer(doc);
  fs.writeFileSync(outputPath, buffer);
  console.log(`Rendered "${templateName}" -> ${outputPath}`);
}

main().catch(err => {
  console.error("Render failed:", err);
  process.exit(1);
});
