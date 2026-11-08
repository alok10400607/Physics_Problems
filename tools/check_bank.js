// Checks the whole bank. Usage: node tools/check_bank.js [--quiet]
// Errors (exit 1) block a merge; warnings are listed for review.
const fs = require('fs'), path = require('path');
const Ajv = require('ajv/dist/2020'), addFormats = require('ajv-formats');
const katex = require('katex');
const macros = require('./katex-macros.json');

const ROOT = path.resolve(__dirname, '..'), BANK = path.join(ROOT, 'bank');
const quiet = process.argv.includes('--quiet');
const errors = [], warnings = [];
const err = (id, m) => errors.push(`${id}: ${m}`), warn = (id, m) => warnings.push(`${id}: ${m}`);
const readJSON = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const walk = d => fs.existsSync(d) ? fs.readdirSync(d, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]) : [];

const ajv = new Ajv({ allErrors: true, strict: false }); addFormats(ajv);
const vProblem = ajv.compile(readJSON(path.join(BANK, 'schema/problem.schema.json')));
const vSolution = ajv.compile(readJSON(path.join(BANK, 'schema/solution.schema.json')));
const vCollection = ajv.compile(readJSON(path.join(BANK, 'schema/collection.schema.json')));
const schemaErr = v => v.errors.map(e => `${e.instancePath || '(root)'} ${e.message}`).join('; ');

const topics = new Map(readJSON(path.join(BANK, 'topics.json')).map(t => [t.code, t]));
const concepts = new Set(readJSON(path.join(BANK, 'concepts.json')).map(c => c.slug));
const registry = readJSON(path.join(BANK, 'registry.json'));

let formulas = 0;
function checkText(id, field, text) {
  if (!text) return;
  const stripped = text.replace(/!\[[^\]]*\]\([^)]*\)/g, '');
  if (((stripped.match(/(?<!\\)\$/g) || []).length) % 2) err(id, `${field}: unbalanced $`);
  for (const m of stripped.matchAll(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g)) {
    const tex = m[1] || m[2]; formulas++;
    try { katex.renderToString(tex, { displayMode: !!m[1], throwOnError: true, macros: { ...macros }, strict: c => c === 'unicodeTextInMathMode' ? 'ignore' : 'error' }); }
    catch (e) { err(id, `${field}: formula does not render: ${tex} (${e.message.split('\n')[0].replace(/^KaTeX parse error: /, '')})`); }
    if (/(?<![\\a-zA-Z])(sin|cos|tan|ln|log)(?=[\s({\\0-9])/.test(tex)) warn(id, `${field}: plain-letter function in ${tex}`);
    if (/[ρ√²³×−→≤≥≈∝°]/.test(tex)) warn(id, `${field}: Unicode symbol inside an equation: ${tex}`);
  }
  if (/\\\(|\\\[/.test(stripped)) err(id, `${field}: uses \\( or \\[ instead of $`);
}
const assetRefs = t => [...(t || '').matchAll(/\]\(asset:([^)\s]+)\)/g)].map(m => m[1]);

// ---- problems ----
const problems = new Map(), hashes = new Map();
for (const f of walk(path.join(BANK, 'problems')).filter(f => f.endsWith('.json'))) {
  const p = readJSON(f), id = p.id || path.basename(f);
  if (!vProblem(p)) { err(id, 'schema: ' + schemaErr(vProblem)); continue; }
  if (path.basename(f) !== `${p.id}.json` || path.basename(path.dirname(f)) !== p.id.slice(0, 4)) err(id, `stored at ${path.relative(BANK, f)}; expected problems/${p.id.slice(0, 4)}/${p.id}.json`);
  if (problems.has(p.id)) err(id, 'duplicate ID'); problems.set(p.id, p);
  if (+p.id.slice(1) >= registry.next_problem_id) err(id, 'ID is not below registry.next_problem_id');
  const t = topics.get(p.topic_code);
  if (!t) err(id, `topic code ${p.topic_code} not in topics.json`);
  else if (t.status === 'merged') err(id, `topic ${p.topic_code} was merged into ${t.merged_into}`);
  for (const c of p.concepts || []) if (!concepts.has(c)) err(id, `concept '${c}' is not in concepts.json`);
  if (p.options && p.answer.keys) for (const k of p.answer.keys) if (!(k in p.options)) err(id, `answer ${k} is not an option`);
  // text and figures
  checkText(id, 'stem', p.stem);
  for (const [k, v] of Object.entries(p.options || {})) checkText(id, `option ${k}`, v);
  if (p.answer.text) checkText(id, 'answer', p.answer.text);
  const refs = [p.stem, ...Object.values(p.options || {})].flatMap(assetRefs);
  const assets = new Map(p.assets.map(a => [a.id, a]));
  for (const r of refs) if (!assets.has(r)) err(id, `text refers to ${r}, which is not in assets`);
  for (const a of p.assets) {
    if (!a.id.startsWith(p.id + '-')) err(id, `asset ${a.id} does not belong to this problem`);
    if (!fs.existsSync(path.join(BANK, 'assets', a.file))) err(id, `asset file ${a.file} is missing`);
    if (a.role !== 'solution' && !refs.includes(a.id)) warn(id, `asset ${a.id} is not used in the text`);
    if (!a.alt.trim()) (p.status === 'published' ? err : warn)(id, `asset ${a.id} has no alt text`);
  }
  if (p.status !== 'retired') {
    if (hashes.has(p.content_hash)) warn(id, `same content as ${hashes.get(p.content_hash)}`);
    hashes.set(p.content_hash, p.id);
  }
}
for (const p of problems.values()) {
  for (const k of ['duplicate_of', 'variant_of']) if (p[k] && !problems.has(p[k])) err(p.id, `${k} points to missing ${p[k]}`);
}

// ---- solutions ----
let solCount = 0;
for (const f of walk(path.join(BANK, 'solutions')).filter(f => f.endsWith('.json'))) {
  const s = readJSON(f), id = s.id || path.basename(f); solCount++;
  if (!vSolution(s)) { err(id, 'solution schema: ' + schemaErr(vSolution)); continue; }
  const p = problems.get(s.id);
  if (!p) { err(id, 'solution has no problem'); continue; }
  if (s.problem_version < p.version) warn(id, `solutions were written for version ${s.problem_version}; problem is now version ${p.version}`);
  if (['reviewed', 'published'].includes(s.status) && (!s.worded || !s.conventional || !s.hints.length)) err(id, `solutions are ${s.status} but a level is missing`);
  s.hints.forEach((h, i) => checkText(id, `hint ${i + 1}`, h));
  for (const k of ['worded', 'conventional', 'extension']) checkText(id, k, s[k]);
  (s.mistakes || []).forEach((m, i) => checkText(id, `mistake ${i + 1}`, m));
  if (s.check && s.check.agrees_with_key === false) warn(id, 'solved answer disagrees with the key');
  const solAssets = assetRefs([s.worded, s.conventional, ...s.hints].join(' '));
  for (const r of solAssets) if (!p.assets.some(a => a.id === r)) err(id, `solution refers to ${r}, which is not in the problem's assets`);
}

// ---- collections ----
const collections = walk(path.join(BANK, 'collections')).filter(f => f.endsWith('.json'));
for (const f of collections) {
  const c = readJSON(f);
  if (!vCollection(c)) { err(c.id || f, 'collection schema: ' + schemaErr(vCollection)); continue; }
  const seen = new Set();
  for (const s of c.sections) for (const pid of s.problems) {
    if (!problems.has(pid)) err(c.id, `${pid} is not in the bank`);
    if (seen.has(pid)) err(c.id, `${pid} appears twice`); seen.add(pid);
  }
}

const statusCount = {}; for (const p of problems.values()) statusCount[p.status] = (statusCount[p.status] || 0) + 1;
console.log(`Bank: ${problems.size} problems ${JSON.stringify(statusCount)}, ${solCount} solution files, ${collections.length} collections, ${formulas} formulas rendered.`);
if (!quiet || errors.length) { console.log(errors.length ? `\nERRORS (${errors.length})\n  ` + errors.join('\n  ') : '\nNo errors.'); }
if (!quiet) console.log(warnings.length ? `\nWARNINGS (${warnings.length})\n  ` + warnings.slice(0, 60).join('\n  ') + (warnings.length > 60 ? `\n  … ${warnings.length - 60} more` : '') : '\nNo warnings.');
process.exit(errors.length ? 1 : 0);
