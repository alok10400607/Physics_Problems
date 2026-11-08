// Builds a self-contained review page for a batch of problems.
// Usage: node tools/review_page.js --out <file.html> (--topic <code> | <P000001> ...) [--compare <git ref>] [--reviewed]
// Maths is rendered here with the site's KaTeX; figures and fonts are embedded, so the page needs nothing else.
const fs = require('fs'), path = require('path'), { execFileSync } = require('child_process');
const katex = require('katex');
const ROOT = path.resolve(__dirname, '..'), BANK = path.join(ROOT, 'bank');
const macros = require('./katex-macros.json');
const args = process.argv.slice(2);
const opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const out = opt('--out'), topic = opt('--topic'), compare = opt('--compare');
const ids = args.filter(a => /^P\d{6}$/.test(a));
const readJSON = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
const topics = new Map(readJSON(path.join(BANK, 'topics.json')).map(t => [t.code, t]));
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const pfile = id => path.join(BANK, 'problems', id.slice(0, 4), `${id}.json`);
const sfile = id => path.join(BANK, 'solutions', id.slice(0, 4), `${id}.json`);
let problems = walk(path.join(BANK, 'problems')).filter(f => f.endsWith('.json')).map(readJSON);
problems = ids.length ? ids.map(id => problems.find(p => p.id === id)).filter(Boolean)
  : problems.filter(p => String(p.topic_code) === String(topic)).sort((a, b) => a.id.localeCompare(b.id));
if (!problems.length) { console.error('No problems selected.'); process.exit(1); }

// collection position (Q number)
const qno = new Map();
for (const f of walk(path.join(BANK, 'collections'))) { let n = 0; for (const s of readJSON(f).sections) for (const pid of s.problems) qno.set(pid, ++n); }

const old = (file) => {
  if (!compare) return null;
  try { return JSON.parse(execFileSync('git', ['show', `${compare}:${path.relative(ROOT, file)}`], { cwd: ROOT, stdio: ['ignore', 'pipe', 'ignore'] }).toString()); }
  catch { return null; }
};

function figure(p, aid) {
  const a = p.assets.find(x => x.id === aid);
  if (!a) return `<span class="missing">[missing figure ${esc(aid)}]</span>`;
  const b64 = fs.readFileSync(path.join(BANK, 'assets', a.file)).toString('base64');
  const mime = a.format === 'svg' ? 'image/svg+xml' : `image/${a.format === 'jpg' ? 'jpeg' : a.format}`;
  return `<span class="fig"><img src="data:${mime};base64,${b64}" alt="${esc(a.alt)}"></span>`;
}
function md(p, s) {
  if (s == null || s === '') return '';
  const keep = [];
  const hold = h => { keep.push(h); return `\u0000${keep.length - 1}\u0000`; };
  s = s.replace(/!\[[^\]]*\]\(asset:([^)\s]+)\)/g, (_, aid) => hold(figure(p, aid)));
  s = s.replace(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g, (m, d, i) => {
    try { return hold(katex.renderToString(d || i, { displayMode: !!d, throwOnError: true, macros: { ...macros }, strict: 'ignore' })); }
    catch (e) { return hold(`<code class="bad">${esc(m)}</code>`); }
  });
  s = esc(s).replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.split(/\n\n+/).map(par => {
    const lines = par.trim().split('\n');
    return lines.every(l => /^- /.test(l)) ? `<ul>${lines.map(l => `<li>${l.slice(2)}</li>`).join('')}</ul>` : `<p>${par.trim()}</p>`;
  }).join('');
  return s.replace(/\u0000(\d+)\u0000/g, (_, n) => keep[n]);
}
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const before = (p, prev, cur) => prev !== undefined && !same(prev, cur)
  ? `<details class="before"><summary>Changed since last version: show before</summary><div class="was">${Array.isArray(prev) ? prev.map(x => md(p, x)).join('') : typeof prev === 'object' && prev ? Object.entries(prev).map(([k, v]) => `<p><b>${k}</b> ${md(p, v).replace(/^<p>|<\/p>$/g, '')}</p>`).join('') : md(p, prev)}</div></details>` : '';

let flagged = 0; const flaggedIds = new Set();
const cards = problems.map(p => {
  const s = fs.existsSync(sfile(p.id)) ? readJSON(sfile(p.id)) : null;
  const op = old(pfile(p.id)), os = old(sfile(p.id));
  const d = p.difficulty || {};
  const issues = [...((s && s.check && s.check.issues) || [])];
  if (s && s.check && s.check.agrees_with_key === false) issues.unshift(`Solved answer ${s.check.solved_answer} disagrees with the key.`);
  if (d.ai_confidence != null && d.ai_confidence < 0.6) issues.push(`Low confidence (${d.ai_confidence}) in the difficulty level.`);
  if (s && s.problem_version < p.version) issues.push(`Solutions were written for version ${s.problem_version}; the problem is now version ${p.version}.`);
  if (issues.length) { flagged++; flaggedIds.add(p.id); }
  const keys = (p.answer.keys || []);
  const exam = p.sources.filter(x => x.kind === 'exam').map(x => x.raw).join('; ');
  const opts = p.options ? `<ol class="opts">${Object.entries(p.options).map(([k, v]) => `<li class="${keys.includes(k) ? 'right' : ''}"><span class="k">${k}</span><div class="v">${md(p, v).replace(/^<p>|<\/p>$/g, '')}${!keys.includes(k) && s && s.distractors && s.distractors[k] ? `<div class="why">Wrong because: ${esc(s.distractors[k])}</div>` : ''}${keys.includes(k) ? '<div class="why ok">Key answer</div>' : ''}</div></li>`).join('')}</ol>` + before(p, op ? op.options : undefined, p.options)
    : `<div class="ans"><span class="lbl">Answer</span> ${p.answer.value != null ? esc(p.answer.value) : md(p, p.answer.text)}</div>`;
  const level = (label, field, html, prevVal, curVal) => `<section class="lvl"><h4>${label}</h4>${html || '<p class="none">Not written yet.</p>'}${before(p, prevVal, curVal)}</section>`;
  const sol = s ? [
    level(`Hints (${s.hints.length})`, 'hints', s.hints.length ? `<ol class="hints">${s.hints.map(h => `<li>${md(p, h)}</li>`).join('')}</ol>` : '', os ? os.hints : undefined, s.hints),
    level('Explained in words', 'worded', md(p, s.worded), os ? os.worded : undefined, s.worded),
    level('Full solution', 'conventional', md(p, s.conventional), os ? os.conventional : undefined, s.conventional),
    s.mistakes && s.mistakes.length ? level('Common mistakes', 'mistakes', `<ul>${s.mistakes.map(m => `<li>${md(p, m).replace(/^<p>|<\/p>$/g, '')}</li>`).join('')}</ul>`, os ? os.mistakes : undefined, s.mistakes) : '',
    s.extension ? level('Think further', 'extension', md(p, s.extension)) : ''
  ].join('') : '<p class="none">No solutions yet.</p>';
  const scores = d.ai_scores ? Object.entries(d.ai_scores).map(([k, v]) => `${k} ${v}`).join(' · ') : '';
  return `<article class="card" id="${p.id}">
    <header class="head">
      <div class="idline"><span class="qn">Q${qno.get(p.id) || '?'}</span><span class="pid">${p.id}</span><span class="tag">v${p.version}</span><span class="tag">${esc(p.status.replace('_', ' '))}</span>${s ? `<span class="tag">solutions ${esc(s.status.replace('_', ' '))}</span>` : ''}</div>
      <div class="meta">${exam ? `<span>${esc(exam)}</span>` : '<span>No source tag</span>'}${p.exams && p.exams.length ? `<span>${esc(p.exams.join(', '))}</span>` : ''}${p.time_estimate_s ? `<span>about ${Math.round(p.time_estimate_s / 15) * 15} s</span>` : ''}</div>
    </header>
    ${issues.length ? `<div class="flags"><b>Needs your eye</b><ul>${issues.map(i => `<li>${esc(i)}</li>`).join('')}</ul></div>` : ''}
    <div class="diff"><span class="lvlbadge">${d.ai ? `Level ${d.ai}` : 'No level'}</span><div><div>${d.ai_reason ? esc(d.ai_reason) : 'Difficulty not proposed yet.'}</div><div class="sub">${d.expert ? `Expert level: ${d.expert}` : 'AI proposal'}${d.ai_confidence != null ? ` · confidence ${d.ai_confidence}` : ''}${scores ? ` · ${esc(scores)}` : ''}${d.worksheet ? ` · worksheet tag ${esc(d.worksheet)}` : ''}</div></div></div>
    <div class="stem">${md(p, p.stem)}${before(p, op ? op.stem : undefined, p.stem)}</div>
    ${opts}
    <div class="sol">${sol}</div>
  </article>`;
}).join('\n');

const t = topics.get(String(topic)) || {};
const heading = topic ? `${topic} · ${t.name || ''}` : problems.map(p => p.id).join(', ');
// KaTeX CSS with fonts embedded
const kdir = path.join(__dirname, 'node_modules', 'katex', 'dist');
const kcss = fs.readFileSync(path.join(kdir, 'katex.min.css'), 'utf8')
  .replace(/src:url\(fonts\/([^)]+\.woff2)\) format\("woff2"\)[^;}]*/g, (_, f) => `src:url(data:font/woff2;base64,${fs.readFileSync(path.join(kdir, 'fonts', f)).toString('base64')}) format("woff2")`);

const html = `<title>${esc(t.name ? `${t.name} Review` : 'Solution Review')}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap">
<style>${kcss}</style>
<style>
/* Layout: one reading column of problem cards; each card = header, flags, difficulty, problem, then the three solution levels */
:root{--bg:#f5f7f8;--surface:#fff;--ink:#152232;--muted:#5b6876;--line:#dbe1e6;--accent:#0f6b78;--accent-soft:#e2f0f1;--good:#1f7a3f;--good-soft:#e3f3e8;--warn:#9a5b00;--warn-soft:#fdf0d9;--bad:#b3261e;--plate:#fff;
--display:"Bricolage Grotesque",ui-sans-serif,system-ui,sans-serif;--body:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f161d;--surface:#17212b;--ink:#e4eaef;--muted:#97a4b0;--line:#2a3743;--accent:#4fb8c4;--accent-soft:#16343a;--good:#5cc983;--good-soft:#15301f;--warn:#e7b25a;--warn-soft:#352813;--bad:#f08a80;--plate:#f3f5f6;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f161d;--surface:#17212b;--ink:#e4eaef;--muted:#97a4b0;--line:#2a3743;--accent:#4fb8c4;--accent-soft:#16343a;--good:#5cc983;--good-soft:#15301f;--warn:#e7b25a;--warn-soft:#352813;--bad:#f08a80;--plate:#f3f5f6;color-scheme:dark}
*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font:16px/1.6 var(--body)}
.wrap{max-width:820px;margin:0 auto;padding-block:28px 64px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:22px}
h1{font:700 clamp(1.6rem,4vw,2.1rem)/1.15 var(--display);margin:0;text-wrap:balance}
.eyebrow{font:500 .75rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.summary{display:flex;flex-wrap:wrap;gap:8px 20px;color:var(--muted);font-size:.95rem}.summary b{color:var(--ink);font-variant-numeric:tabular-nums}
.jump{display:flex;flex-wrap:wrap;gap:6px}.jump a{font:500 .78rem var(--mono);color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:4px;padding:3px 7px;background:var(--surface)}.jump a.fl{border-color:var(--warn);color:var(--warn)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px clamp(16px,4vw,28px);display:flex;flex-direction:column;gap:14px;scroll-margin-top:12px}
.idline{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.qn{font:700 1.15rem var(--display);margin-right:4px}
.pid{font:500 .82rem var(--mono);border:1.5px solid var(--ink);border-radius:4px;padding:2px 7px}
.tag{font:500 .72rem var(--mono);border:1px dashed var(--line);border-radius:4px;padding:3px 7px;color:var(--muted)}
.meta{display:flex;flex-wrap:wrap;gap:4px 14px;color:var(--muted);font-size:.85rem;margin-top:6px}
.flags{background:var(--warn-soft);border-radius:8px;padding:10px 14px;font-size:.93rem}.flags b{color:var(--warn);font-family:var(--display)}.flags ul{margin:4px 0 0;padding-left:1.1em}
.diff{display:flex;gap:12px;align-items:flex-start;font-size:.92rem}.diff .sub{color:var(--muted);font-size:.82rem}
.lvlbadge{flex:none;font:600 .8rem var(--mono);background:var(--accent-soft);color:var(--accent);border-radius:4px;padding:4px 8px}
.stem p{margin:0 0 .6em}.stem p:last-child{margin:0}
.fig{display:block;background:var(--plate);border-radius:6px;padding:8px;width:fit-content;max-width:100%;margin:4px 0}.fig img{display:block;max-width:100%;max-height:230px;height:auto}
.opts{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.opts li{display:flex;gap:10px;border:1.5px solid var(--line);border-radius:8px;padding:9px 12px;min-width:0}.opts li.right{border-color:var(--good);background:var(--good-soft)}
.opts .k{flex:none;width:24px;height:24px;border-radius:50%;border:1.5px solid currentColor;display:grid;place-items:center;font:600 .78rem var(--mono);color:var(--muted)}.opts li.right .k{color:var(--good)}
.opts .v{min-width:0;overflow-x:auto}.why{font-size:.82rem;color:var(--muted);margin-top:2px}.why.ok{color:var(--good);font-weight:600}
.ans{font-size:.95rem}.lbl{font:500 .72rem var(--mono);text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.sol{display:flex;flex-direction:column;gap:12px;border-top:1px solid var(--line);padding-top:14px}
.lvl h4{margin:0 0 4px;font:500 .74rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lvl p{margin:0 0 .55em}.lvl p:last-child{margin:0}.lvl ul,.lvl ol{margin:0;padding-left:1.2em;display:flex;flex-direction:column;gap:4px}.hints li p{margin:0}
.none{color:var(--muted);font-style:italic}
.katex-display{overflow-x:auto;overflow-y:hidden;margin:.4em 0}.katex{font-size:1.06em}
.before{margin-top:6px;font-size:.88rem}.before summary{cursor:pointer;color:var(--warn);font-weight:500}.was{border-left:3px solid var(--warn);padding:4px 0 4px 10px;margin-top:4px;color:var(--muted)}
code.bad{color:var(--bad)}.missing{color:var(--bad)}
a:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
</style>
<main class="wrap">
  <header style="display:flex;flex-direction:column;gap:10px">
    <span class="eyebrow">Solution review${compare ? ` · changes since ${esc(compare)}` : ''}</span>
    <h1>${esc(heading)}</h1>
    <div class="summary"><span><b>${problems.length}</b> problems</span><span><b>${flagged}</b> need your eye</span><span>Reply in the chat: "approve all", "approve 30–33", or describe a change.</span></div>
    <nav class="jump" aria-label="Problems">${problems.map(p => `<a href="#${p.id}" class="${flaggedIds.has(p.id) ? 'fl' : ''}">Q${qno.get(p.id) || '?'} ${p.id.slice(-3)}</a>`).join('')}</nav>
  </header>
  ${cards}
</main>`;
fs.writeFileSync(out, html);
console.log(`Review page: ${problems.length} problems, ${flagged} flagged → ${out} (${Math.round(html.length / 1024)} KB)`);
