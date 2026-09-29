import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");

// 1. Read dist CSS
const distDir = path.join(rootDir, "dist/assets");
if (!fs.existsSync(distDir)) {
  console.error("dist/assets does not exist. Run pnpm build first.");
  process.exit(1);
}

const cssFile = fs.readdirSync(distDir).find((f) => f.endsWith(".css"));
if (!cssFile) {
  console.error("No CSS file found in dist/assets.");
  process.exit(1);
}

const cssContent = fs.readFileSync(path.join(distDir, cssFile), "utf-8");

// List of semantic tokens from index.css
const tokens = [
  "button-x",
  "cell-x",
  "control-x",
  "inline",
  "dialog-pad",
  "stack",
  "toolbar",
  "header",
  "gutter",
  "section",
  "container-bottom",
  "tight",
  "popup-pad",
  "item-gap",
  "row-header",
  "row-body",
];

// Collect all src files
const srcDir = path.join(rootDir, "src");
function getFiles(dir) {
  let results = [];
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, f.name);
    if (f.isDirectory()) results.push(...getFiles(full));
    else if (/\.(tsx?|jsx?|html)$/.test(f.name)) results.push(full);
  }
  return results;
}

const srcFiles = getFiles(srcDir);
const usedUtils = new Set();

const regexes = [
  /\b((?:p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|gap-x|gap-y|h|w|min-h|max-h|min-w|max-w)-([a-z-]+))\b/g,
  /\b(w-dialog)\b/g,
];

for (const file of srcFiles) {
  const content = fs.readFileSync(file, "utf-8");
  for (const re of regexes) {
    let match;
    while ((match = re.exec(content)) !== null) {
      const util = match[1];
      for (const t of tokens) {
        if (util.endsWith("-" + t)) {
          usedUtils.add(util);
        }
      }
      if (util === "w-dialog") {
        usedUtils.add(util);
      }
    }
  }
}

console.log("Used spacing/size utilities in src:");
const sorted = Array.from(usedUtils).sort();

let allPassed = true;
for (const u of sorted) {
  const escaped = u.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
  const selRegex = new RegExp("\\." + escaped + "(?=[^a-zA-Z0-9_-]|$)", "g");
  const matches = cssContent.match(selRegex) || [];
  const count = matches.length;
  console.log(`${u.padEnd(25)} : ${count}`);
  if (count === 0) allPassed = false;
}

if (!allPassed) {
  console.error("\nFAILURE: Some utilities had 0 selectors in built CSS!");
  process.exit(1);
} else {
  console.log(
    "\nSUCCESS: All used utilities exist with >0 selectors in built CSS."
  );
}
