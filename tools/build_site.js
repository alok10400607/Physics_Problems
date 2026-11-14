// Builds the site's data from the bank. Usage: node tools/build_site.js
// Writes:
//   site/data/catalog.json     every chapter and subtopic in TopicCode_v2, with how many problems each has
//   site/data/ch/<CC>.json     the problems of one chapter, grouped by subtopic, with their solutions
//   site/data/figures/         figures, with a short content fingerprint in the name so browsers never show a stale copy
//   site/labs/<series>/        the interactive pages from bank/labs/, listed in catalog.json under "labs"
// Students browse chapter → subtopic → questions; the order inside a subtopic follows the worksheets.
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const ROOT = path.resolve(__dirname, '..'), BANK = path.join(ROOT, 'bank'), OUT = path.join(ROOT, 'site', 'data');
const readJSON = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const walk = d => fs.existsSync(d) ? fs.readdirSync(d, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]) : [];
const macros = readJSON(path.join(__dirname, 'katex-macros.json'));
const topics = readJSON(path.join(BANK, 'topics.json')).filter(t => t.status === 'active');

// Groups shown on the home page (chapter-code ranges); edit freely
const GROUPS = [
  { name: 'Mechanics', from: 1, to: 16 },
  { name: 'Oscillations & Waves', from: 17, to: 19 },
  { name: 'Heat & Thermodynamics', from: 20, to: 23 },
  { name: 'Electricity & Magnetism', from: 24, to: 33 },
  { name: 'Optics', from: 34, to: 36 },
  { name: 'Modern Physics', from: 37, to: 40 },
];

const problems = new Map(walk(path.join(BANK, 'problems')).filter(f => f.endsWith('.json')).map(f => { const p = readJSON(f); return [p.id, p]; }));
const solutions = new Map(walk(path.join(BANK, 'solutions')).filter(f => f.endsWith('.json')).map(f => { const s = readJSON(f); return [s.id, s]; }));

// order: the position of each problem in the collections (worksheets), then ID
const order = new Map(); let k = 0;
for (const f of walk(path.join(BANK, 'collections')).filter(f => f.endsWith('.json')).sort())
  for (const s of readJSON(f).sections) for (const pid of s.problems) if (!order.has(pid)) order.set(pid, k++);

fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(path.join(OUT, 'figures'), { recursive: true });
fs.mkdirSync(path.join(OUT, 'ch'), { recursive: true });

const published = new Map();
function assetUrl(p, aid) {
  if (published.has(aid)) return published.get(aid);
  const a = p.assets.find(x => x.id === aid);
  if (!a) return { url: '', alt: '' };
  const buf = fs.readFileSync(path.join(BANK, 'assets', a.file));
  const name = `${aid}.${crypto.createHash('sha256').update(buf).digest('hex').slice(0, 8)}.${a.format}`;
  fs.writeFileSync(path.join(OUT, 'figures', name), buf);
  const v = { url: `data/figures/${name}`, alt: a.alt || '' };
  published.set(aid, v); return v;
}
const resolve = (p, text) => text == null ? text : text.replace(/!\[([^\]]*)\]\(asset:([^)\s]+)\)/g, (_, alt, aid) => {
  const a = assetUrl(p, aid); return `![${(alt || a.alt).replace(/[\[\]]/g, '')}](${a.url})`;
});

function toQuestion(p) {
  const sol = solutions.get(p.id) || {};
  const d = p.difficulty || {};
  const exam = p.sources.find(x => x.kind === 'exam');
  const type = p.type.startsWith('mcq') || p.type === 'assertion_reason' ? 'mcq' : (p.type === 'integer' || p.type === 'numerical') ? 'numerical' : 'subjective';
  return {
    id: p.id, type, level: d.expert || d.ai || (d.worksheet ? +d.worksheet.slice(1) : null), status: p.status,
    source: exam ? exam.raw : null, exams: p.exams || [],
    question: resolve(p, p.stem),
    options: p.options ? Object.fromEntries(Object.entries(p.options).map(([k, v]) => [k, resolve(p, v)])) : undefined,
    answer: p.answer.keys ? p.answer.keys.join(',') : p.answer.value != null ? String(p.answer.value) : resolve(p, p.answer.text),
    unit: p.answer.unit || null, tolerance: p.answer.tolerance,
    hints: (sol.hints || []).map(h => resolve(p, h)), worded: resolve(p, sol.worded || null), conventional: resolve(p, sol.conventional || null),
    mistakes: (sol.mistakes || []).map(m => resolve(p, m)),
    distractors: sol.distractors && Object.keys(sol.distractors).length ? Object.fromEntries(Object.entries(sol.distractors).map(([k, v]) => [k, resolve(p, v)])) : undefined,
    extension: resolve(p, sol.extension || null), solution_status: sol.status || null
  };
}

const live = [...problems.values()].filter(p => p.status !== 'retired' && !p.duplicate_of);
const byTopic = new Map();
for (const p of live) { if (!byTopic.has(p.topic_code)) byTopic.set(p.topic_code, []); byTopic.get(p.topic_code).push(p); }
for (const list of byTopic.values()) list.sort((a, b) => (order.get(a.id) ?? 1e9) - (order.get(b.id) ?? 1e9) || a.id.localeCompare(b.id));

const chapters = [];
for (const t of topics) {
  let ch = chapters.find(c => c.code === t.chapter_code);
  if (!ch) { ch = { code: t.chapter_code, name: t.chapter, count: 0, subtopics: [] }; chapters.push(ch); }
  const ps = byTopic.get(t.code) || [];
  const levels = [0, 0, 0, 0, 0, 0];
  for (const p of ps) { const q = toQuestion(p); if (q.level) levels[q.level - 1]++; }
  ch.subtopics.push({ code: t.code, name: t.name, covers: t.covers || '', count: ps.length, solved: ps.filter(p => solutions.get(p.id)?.conventional).length, levels });
  ch.count += ps.length;
}
for (const ch of chapters) {
  if (!ch.count) continue;
  const data = { code: ch.code, name: ch.name, macros, subtopics: {} };
  for (const s of ch.subtopics) data.subtopics[s.code] = (byTopic.get(s.code) || []).map(toQuestion);
  fs.writeFileSync(path.join(OUT, 'ch', `${ch.code}.json`), JSON.stringify(data));
}
const groups = GROUPS.map(g => ({ name: g.name, chapters: chapters.filter(c => +c.code >= g.from && +c.code <= g.to).map(c => c.code) }));
// Exemplars & animations: bank/labs/<series>/*.html copied to site/labs/, listed in the catalog by subtopic
const LABS_OUT = path.join(ROOT, 'site', 'labs');
fs.rmSync(LABS_OUT, { recursive: true, force: true });
const labsIndex = path.join(BANK, 'labs', 'index.json');
const labs = [];
if (fs.existsSync(labsIndex)) {
  for (const se of readJSON(labsIndex).series) {
    fs.mkdirSync(path.join(LABS_OUT, se.id), { recursive: true });
    for (const pg of se.pages) {
      const buf = fs.readFileSync(path.join(BANK, 'labs', se.id, pg.file));
      const name = pg.file.replace(/\.html$/, '') + '-' + crypto.createHash('sha256').update(buf).digest('hex').slice(0, 8) + '.html';
      fs.writeFileSync(path.join(LABS_OUT, se.id, name), buf);
      labs.push({ id: `${se.id}-${pg.key}`, series: se.id, seriesTitle: se.title, seriesSummary: se.summary || '', key: pg.key, kind: pg.kind, goal: pg.goal, topics: pg.topics, url: `labs/${se.id}/${name}` });
    }
  }
}
for (const ch of chapters) for (const s of ch.subtopics) s.labs = labs.filter(l => l.topics.includes(s.code)).length;
fs.writeFileSync(path.join(OUT, 'catalog.json'), JSON.stringify({ built: new Date().toISOString().slice(0, 10), groups, chapters, labs }));
const withProblems = chapters.filter(c => c.count);
console.log(`Built ${chapters.length} chapters (${withProblems.length} with problems: ${withProblems.map(c => `${c.code} (${c.count})`).join(', ')}); ${published.size} figures; ${labs.length} interactive pages.`);
