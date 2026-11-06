import { readFileSync, existsSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");

const manifest = JSON.parse(readFileSync(resolve(root, "manifest.json"), "utf-8"));

const allPaths = [
  manifest.layout.template,
  manifest.layout.schema,
  manifest.layout.settings,
  manifest.header.template,
  manifest.header.schema,
  manifest.footer.template,
  manifest.footer.schema,
  ...manifest.templates,
  ...manifest.sections,
  ...manifest.components,
  ...manifest.schemas
];

let missing = 0;
let valid = 0;

for (const filePath of allPaths) {
  const abs = resolve(root, filePath);
  if (!existsSync(abs)) {
    console.error(`MISSING: ${filePath}`);
    missing++;
  } else {
    valid++;
  }
}

console.log(`\nValidation complete: ${valid} files found, ${missing} missing`);

if (missing > 0) {
  process.exit(1);
}

console.log("All manifest entries are valid.");
