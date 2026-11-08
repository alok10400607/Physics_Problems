// Builds the site's data from the bank. Usage: node tools/build_site.js
// Writes site/data/index.json, site/data/<collection>.json and site/data/figures/.
// Figures get a short content fingerprint in their file name so browsers never show a stale copy.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..'), BANK = path.join(ROOT, 'bank'), OUT = path.join(ROOT, 'site', 'data');
const readJSON = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const walk = d => fs.existsSync(d) ? fs.readdirSync(d, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]) : [];
const macros = readJSON(path.join(__dirname, 'katex-macros.json'));
const topics = new Map(readJSON(path.join(BANK, 'topics.json')).map(t => [t.code, t]));

const problems = new Map(walk(path.join(BANK, 'problems')).filter(f => f.endsWith('.json')).map(f => { const p = readJSON(f); return [p.id, p]; }));
const solutions = new Map(walk(path.join(BANK, 'solutions')).filter(f => f.endsWith('.json')).map(f => { const s = readJSON(f); return [s.id, s]; }));

fs.rmSync(path.join(OUT, 'figures'), { recursive: true, force: true });
fs.mkdirSync(path.join(OUT, 'figures'), { recursive: true });
for (const f of fs.readdirSync(OUT)) if (f.endsWith('.json')) fs.rmSync(path.join(OUT, f));

const published = new Map(); // asset id -> {url, alt}
function assetUrl(p, aid) {
  if (published.has(aid)) return published.get(aid);
  const a = p.assets.find(x => x.id === aid);
  const src = path.join(BANK, 'assets', a.file), buf = fs.readFileSync(src);
  const name = `${aid}.${crypto.createHash('sha256').update(buf).digest('hex').slice(0, 8)}.${a.format}`;
  fs.writeFileSync(path.join(OUT, 'figures', name), buf);
  const v = { url: `data/figures/${name}`, alt: a.alt || '' };
  published.set(aid, v); return v;
}
const resolve = (p, text) => text == null ? text : text.replace(/!\[([^\]]*)\]\(asset:([^)\s]+)\)/g, (_, alt, aid) => {
  const a = assetUrl(p, aid); return `![${(alt || a.alt).replace(/[\[\]]/g, '')}](${a.url})`;
});

const index = [];
for (const f of walk(path.join(BANK, 'collections')).filter(f => f.endsWith('.json'))) {
  const c = readJSON(f);
  const questions = [];
  let n = 0;
  for (const s of c.sections) for (const pid of s.problems) {
    const p = problems.get(pid); n++;
    if (!p || p.status === 'retired') continue;
    const sol = solutions.get(pid) || {};
    const exam = p.sources.find(x => x.kind === 'exam');
    const d = p.difficulty || {};
    const level = d.expert || d.ai || (d.worksheet ? +d.worksheet.slice(1) : null);
    const type = p.type.startsWith('mcq') || p.type === 'assertion_reason' ? 'mcq' : (p.type === 'integer' || p.type === 'numerical') ? 'numerical' : 'subjective';
    const answer = p.answer.keys ? p.answer.keys.join(',') : p.answer.value != null ? String(p.answer.value) : resolve(p, p.answer.text);
    questions.push({
      id: p.id, number: n, subtopic: s.topic_code, type, level, status: p.status,
      source: exam ? exam.raw : null,
      question: resolve(p, p.stem),
      options: p.options ? Object.fromEntries(Object.entries(p.options).map(([k, v]) => [k, resolve(p, v)])) : undefined,
      answer, tolerance: p.answer.tolerance,
      hints: (sol.hints || []).map(h => resolve(p, h)),
      worded: resolve(p, sol.worded || null), conventional: resolve(p, sol.conventional || null),
      mistakes: sol.mistakes || [], extension: sol.extension || null, solution_status: sol.status || null
    });
  }
  const subtopics = c.sections.map(s => ({ code: s.topic_code, name: (topics.get(s.topic_code) || {}).name || s.title,
    provisional: (topics.get(s.topic_code) || {}).status === 'provisional', count: questions.filter(q => q.subtopic === s.topic_code).length }));
  fs.writeFileSync(path.join(OUT, `${c.id}.json`), JSON.stringify({ chapter: c.id, title: c.title, note: c.note, macros, subtopics, questions }));
  index.push({ id: c.id, title: c.title, count: questions.length });
}
fs.writeFileSync(path.join(OUT, 'index.json'), JSON.stringify(index));
console.log(`Built ${index.length} collection(s): ${index.map(i => `${i.id} (${i.count})`).join(', ')}; ${published.size} figures.`);
