import { spawnSync } from "node:child_process";

const pptxPath = process.argv[2];
if (!pptxPath) {
  console.error("Usage: node extract_mid_text.mjs <pptx>");
  process.exit(1);
}

function run(cmd, args) {
  const result = spawnSync(cmd, args, { encoding: "utf8" });
  if (result.status !== 0) {
    throw new Error(result.stderr || `${cmd} failed`);
  }
  return result.stdout;
}

function decodeXml(s) {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'");
}

const files = run("unzip", ["-Z1", pptxPath])
  .split(/\r?\n/)
  .filter((name) => /^ppt\/slides\/slide\d+\.xml$/.test(name))
  .sort((a, b) => Number(a.match(/slide(\d+)/)[1]) - Number(b.match(/slide(\d+)/)[1]));

for (const file of files) {
  const xml = run("unzip", ["-p", pptxPath, file]);
  const slideNo = Number(file.match(/slide(\d+)/)[1]);
  const texts = [];
  const re = /<a:t>([\s\S]*?)<\/a:t>/g;
  let m;
  while ((m = re.exec(xml))) {
    const text = decodeXml(m[1]).trim();
    if (text) texts.push(text);
  }
  console.log(`\n--- SLIDE ${slideNo} ---`);
  console.log(texts.join("\n"));
}
