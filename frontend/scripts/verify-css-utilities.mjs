import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(__dirname, "..");

// 1. Read dist assets
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

// 2. Check 4: Ensure built JS bundle does not contain development-only styleguide text
const jsFiles = fs.readdirSync(distDir).filter((f) => f.endsWith(".js"));
if (jsFiles.length === 0) {
  console.error("No JS files found in dist/assets.");
  process.exit(1);
}

for (const jsFile of jsFiles) {
  const jsContent = fs.readFileSync(path.join(distDir, jsFile), "utf-8");
  if (jsContent.includes("Development-only token reference")) {
    console.error(
      `\nFAILURE: Built JS bundle ${jsFile} contains "Development-only token reference"! Styleguide was not tree-shaken.`
    );
    process.exit(1);
  }
}

// 3. Derive tokens dynamically from src/index.css
const indexCssPath = path.join(rootDir, "src/index.css");
if (!fs.existsSync(indexCssPath)) {
  console.error("src/index.css does not exist.");
  process.exit(1);
}
const indexCssContent = fs.readFileSync(indexCssPath, "utf-8");
const tokenMatches = indexCssContent.matchAll(/--spacing-([a-z0-9-]+)\s*:/g);
const tokens = Array.from(tokenMatches, (m) => m[1]);

if (tokens.length === 0) {
  console.error("No spacing tokens found in src/index.css.");
  process.exit(1);
}

// 4. Collect all src files
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
  /\b((?:p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|gap-x|gap-y|h|w|min-h|max-h|min-w|max-w)-([a-z0-9-]+))\b/g,
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

// 5. Check 3: Fail if zero used utilities are found (non-vacuous guard)
if (usedUtils.size === 0) {
  console.error(
    "\nFAILURE: No used utilities found in src! Check scanning logic."
  );
  process.exit(1);
}

// 6. Ensure every defined spacing token in index.css is used in src (no dead tokens)
let allPassed = true;
for (const t of tokens) {
  let tokenUsed = false;
  for (const u of usedUtils) {
    if (u.endsWith("-" + t)) {
      tokenUsed = true;
      break;
    }
  }
  if (!tokenUsed) {
    console.error(
      `\nFAILURE: Token "${t}" defined in index.css is not used by any utility in src!`
    );
    allPassed = false;
  }
}

console.log(`Found ${usedUtils.size} used spacing/size utilities in src:`);
const sorted = Array.from(usedUtils).sort();

// 7. Check 2: Fail if any utility USED in src has zero selectors in the built CSS
for (const u of sorted) {
  const escaped = u.replace(/[-/\\^$*+?.()|[\]{}]/g, "\\$&");
  const selRegex = new RegExp("\\." + escaped + "(?=[^a-zA-Z0-9_-]|$)", "g");
  const matches = cssContent.match(selRegex) || [];
  const count = matches.length;
  console.log(`${u.padEnd(25)} : ${count}`);
  if (count === 0) allPassed = false;
}

if (!allPassed) {
  console.error(
    "\nFAILURE: Utility verification failed (dead token or 0 selectors in built CSS)!"
  );
  process.exit(1);
} else {
  console.log(
    "\nSUCCESS: All used utilities exist with >0 selectors in built CSS and JS bundle is clean."
  );
}
