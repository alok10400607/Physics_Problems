// Builds the interactive review page ("workbench") for one subtopic: problems shown as students see them,
// "Revise with Claude" on the page, and "Request a change" / "Approve" as prefilled GitHub issues.
// Usage: node tools/review_workbench.js --topic 1715 --out <file.html> [--repo owner/name]
// Publish the file as an Artifact with capabilities {sample: {}}.
const fs = require('fs'), path = require('path');
const { fingerprint } = require('./solution_fingerprint');
const ROOT = path.resolve(__dirname, '..'), BANK = path.join(ROOT, 'bank');
const args = process.argv.slice(2), opt = k => { const i = args.indexOf(k); return i >= 0 ? args[i + 1] : null; };
const topic = opt('--topic'), out = opt('--out'), repo = opt('--repo') || 'alok10400607/Physics_Problems';
const readJSON = f => JSON.parse(fs.readFileSync(f, 'utf8'));
const walk = d => fs.readdirSync(d, { withFileTypes: true }).flatMap(e => e.isDirectory() ? walk(path.join(d, e.name)) : [path.join(d, e.name)]);
const topics = new Map(readJSON(path.join(BANK, 'topics.json')).map(t => [t.code, t]));
const t = topics.get(String(topic));
if (!t) { console.error(`Unknown topic ${topic}`); process.exit(1); }
const qno = new Map();
for (const f of walk(path.join(BANK, 'collections'))) { let n = 0; for (const s of readJSON(f).sections) for (const pid of s.problems) qno.set(pid, ++n); }
const problems = walk(path.join(BANK, 'problems')).filter(f => f.endsWith('.json')).map(readJSON)
  .filter(p => p.topic_code === String(topic) && p.status !== 'retired').sort((a, b) => a.id.localeCompare(b.id));
// the worksheet's own question number (03MSL Q4), shown so the reviewer can find it in the DOCX
const wsno = p => { const w = p.sources.find(x => x.kind === 'worksheet'); return w ? w.ref.replace(/_v\d+$/, '') + ' Q' + w.qno : null; };

const data = problems.map(p => {
  const sf = path.join(BANK, 'solutions', p.id.slice(0, 4), `${p.id}.json`);
  const s = fs.existsSync(sf) ? readJSON(sf) : null;
  const figs = {};
  for (const a of p.assets) {
    const b64 = fs.readFileSync(path.join(BANK, 'assets', a.file)).toString('base64');
    figs[a.id] = { src: `data:image/${a.format === 'jpg' ? 'jpeg' : a.format};base64,${b64}`, alt: a.alt };
  }
  return {
    id: p.id, qno: qno.get(p.id) || null, ws: wsno(p), version: p.version, status: p.status, type: p.type,
    source: p.sources.filter(x => x.kind === 'exam').map(x => x.raw).join('; ') || null,
    difficulty: p.difficulty, stem: p.stem, options: p.options || null, answer: p.answer, figs,
    sol: s ? { hints: s.hints || [], worded: s.worded || '', conventional: s.conventional || '', mistakes: s.mistakes || [],
               distractors: s.distractors || {}, status: s.status, issues: (s.check && s.check.issues) || [] } : null,
    base: s ? fingerprint(s) : 'none'
  };
});

const guide = fs.readFileSync(path.join(ROOT, 'docs', 'solution-writing-guide.md'), 'utf8');
const style = fs.readFileSync(path.join(ROOT, 'docs', 'maths-style.md'), 'utf8').split('## Macros')[0];
const macros = readJSON(path.join(__dirname, 'katex-macros.json'));
const kdir = path.join(__dirname, 'node_modules', 'katex', 'dist');
const kcss = fs.readFileSync(path.join(kdir, 'katex.min.css'), 'utf8')
  .replace(/src:url\(fonts\/([^)]+\.woff2)\) format\("woff2"\)[^;}]*/g, (_, f) => `src:url(data:font/woff2;base64,${fs.readFileSync(path.join(kdir, 'fonts', f)).toString('base64')}) format("woff2")`);
const payload = JSON.stringify({ topic: t.code, topicName: t.name, chapter: t.chapter, repo, guide, style, macros, problems: data })
  .replace(/</g, '\\u003c');

const html = String.raw`<!DOCTYPE html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>${t.name} Review</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@500&display=swap">
<style>${kcss}</style>
<style>
/* Layout: one reading column; each problem = student view of the problem and its solutions, then the reviewer's tools */
:root{--bg:#f5f7f8;--surface:#fff;--ink:#152232;--muted:#5b6876;--line:#dbe1e6;--accent:#0f6b78;--accent-soft:#e2f0f1;--accent-ink:#fff;--good:#1f7a3f;--good-soft:#e3f3e8;--warn:#9a5b00;--warn-soft:#fdf0d9;--bad:#b3261e;--bad-soft:#fbe7e5;--plate:#fff;--new:#3d4fb8;--new-soft:#e8ebfa;
--display:"Bricolage Grotesque",ui-sans-serif,system-ui,sans-serif;--body:"IBM Plex Sans",ui-sans-serif,system-ui,sans-serif;--mono:"IBM Plex Mono",ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0f161d;--surface:#17212b;--ink:#e4eaef;--muted:#97a4b0;--line:#2a3743;--accent:#4fb8c4;--accent-soft:#16343a;--accent-ink:#06191c;--good:#5cc983;--good-soft:#15301f;--warn:#e7b25a;--warn-soft:#352813;--bad:#f08a80;--bad-soft:#3a1c1a;--plate:#f3f5f6;--new:#9aa8f0;--new-soft:#1f2547;color-scheme:dark}}
:root[data-theme="dark"]{--bg:#0f161d;--surface:#17212b;--ink:#e4eaef;--muted:#97a4b0;--line:#2a3743;--accent:#4fb8c4;--accent-soft:#16343a;--accent-ink:#06191c;--good:#5cc983;--good-soft:#15301f;--warn:#e7b25a;--warn-soft:#352813;--bad:#f08a80;--bad-soft:#3a1c1a;--plate:#f3f5f6;--new:#9aa8f0;--new-soft:#1f2547;color-scheme:dark}
*{box-sizing:border-box}body{background:var(--bg);color:var(--ink);font:16px/1.6 var(--body)}
.wrap{max-width:820px;margin:0 auto;padding-block:28px 72px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px));display:flex;flex-direction:column;gap:22px}
h1{font:700 clamp(1.6rem,4vw,2.1rem)/1.15 var(--display);margin:0;text-wrap:balance}
.eyebrow{font:500 .75rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
.lede{color:var(--muted);margin:0}
.who{display:flex;flex-wrap:wrap;gap:8px;align-items:center;font-size:.92rem}
.who input{font:inherit;padding:7px 10px;border:1.5px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink);min-width:0;width:16rem;max-width:100%}
.notice{background:var(--warn-soft);border-radius:8px;padding:10px 14px;font-size:.92rem}
.jump{display:flex;flex-wrap:wrap;gap:6px}.jump a{font:500 .78rem var(--mono);color:var(--ink);text-decoration:none;border:1px solid var(--line);border-radius:4px;padding:3px 8px;background:var(--surface)}
.jump a.done{border-color:var(--good);color:var(--good)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:20px clamp(16px,4vw,28px);display:flex;flex-direction:column;gap:14px;scroll-margin-top:12px}
.idline{display:flex;flex-wrap:wrap;gap:6px;align-items:center}.qn{font:700 1.15rem var(--display);margin-right:4px}
.pid{font:500 .82rem var(--mono);border:1.5px solid var(--ink);border-radius:4px;padding:2px 7px}
.tag{font:500 .72rem var(--mono);border:1px dashed var(--line);border-radius:4px;padding:3px 7px;color:var(--muted)}
.meta{color:var(--muted);font-size:.85rem}
.flags{background:var(--warn-soft);border-radius:8px;padding:10px 14px;font-size:.92rem}.flags b{color:var(--warn)}.flags ul{margin:4px 0 0;padding-left:1.1em}
.qtext p{margin:0 0 .6em}.qtext p:last-child{margin:0}.qtext ul{margin:0 0 .6em;padding-left:1.2em}
.fig{display:block;background:var(--plate);border-radius:6px;padding:8px;width:fit-content;max-width:100%;margin:4px 0}.fig img{display:block;max-width:100%;max-height:230px;height:auto}
.opts{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.opts li{display:flex;gap:10px;border:1.5px solid var(--line);border-radius:8px;padding:9px 12px;min-width:0;background:var(--bg)}
.opts li.key{border-color:var(--good)}
.opts .k{flex:none;width:24px;height:24px;border-radius:50%;border:1.5px solid currentColor;display:grid;place-items:center;font:600 .78rem var(--mono);color:var(--muted)}.opts li.key .k{color:var(--good)}
.opts .v{min-width:0;overflow-x:auto}.opts .fig{padding:4px}.opts .fig img{max-height:120px}
.keynote{font-size:.85rem;color:var(--good);font-weight:600}
.student{border-top:1px solid var(--line);padding-top:14px;display:flex;flex-direction:column;gap:12px}
.student .lbl{font:500 .72rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}
.vers{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.vers button{font:500 .78rem var(--mono);border:1.5px solid var(--line);background:var(--bg);color:var(--ink);border-radius:999px;padding:4px 11px;cursor:pointer}
.vers button.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink)}
.vers label{font-size:.85rem;display:inline-flex;gap:6px;align-items:center;margin-left:4px}
.aside{border-left:3px solid var(--accent);padding:2px 0 2px 12px}
.aside .t{font:500 .72rem var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-bottom:2px}
.aside.hint{border-left-color:var(--warn)}.aside.hint .t{color:var(--warn)}
.aside.changed{background:var(--new-soft);border-left-color:var(--new);border-radius:0 6px 6px 0;padding:6px 10px 6px 12px}.aside.changed .t{color:var(--new)}
.was{margin-top:6px;border-left:3px dashed var(--line);padding:2px 0 2px 10px;color:var(--muted);font-size:.92rem}
.was .t{font:500 .7rem var(--mono);text-transform:uppercase;letter-spacing:.06em}
.revise{background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:8px}
.revise h4{margin:0;font:600 1rem var(--display)}
.revise textarea{font:inherit;width:100%;min-height:72px;padding:9px 11px;border:1.5px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink);resize:vertical}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
select{font:inherit;padding:6px 8px;border:1.5px solid var(--line);border-radius:6px;background:var(--surface);color:var(--ink)}
.btn{font:600 .92rem var(--body);border:0;border-radius:8px;padding:9px 16px;background:var(--accent);color:var(--accent-ink);cursor:pointer;text-decoration:none;display:inline-block}
.btn.ghost{background:transparent;border:1.5px solid var(--line);color:var(--ink)}
.btn.go{background:var(--good);color:var(--bg)}
.btn[disabled],.btn.off{opacity:.45;pointer-events:none}
.status{font-size:.88rem;color:var(--muted)}.status.err{color:var(--bad)}
.note{background:var(--new-soft);border-radius:6px;padding:8px 12px;font-size:.9rem}
.history{margin:0;padding-left:1.2em;font-size:.88rem;color:var(--muted)}
.send{border-top:1px solid var(--line);padding-top:12px;display:flex;flex-direction:column;gap:8px}
.katex-display{overflow-x:auto;overflow-y:hidden;margin:.4em 0}.katex{font-size:1.06em}
.badtex{color:var(--bad);font-family:var(--mono);font-size:.85em}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>
<main class="wrap" id="app">
  <header style="display:flex;flex-direction:column;gap:10px">
    <span class="eyebrow" id="eyebrow">Solution review</span>
    <h1 id="title">Review</h1>
    <p class="lede">Each problem appears as students will see it. Ask Claude for changes underneath, compare versions, and send the one you're happy with. Nothing is saved until you press <b>Request a change</b> or <b>Approve</b>; both open a GitHub issue that Claude turns into a pull request.</p>
    <div class="who"><label for="reviewer">Your name</label><input id="reviewer" placeholder="Shown as the reviewer in GitHub" autocomplete="name"></div>
    <div class="notice" id="claude-off" hidden>Revising with Claude isn't available in this view (open the page in Claude, signed in, and allow it when asked). You can still approve or request changes by hand.</div>
    <nav class="jump" id="jump" aria-label="Problems"></nav>
  </header>
  <div id="cards" style="display:flex;flex-direction:column;gap:22px"></div>
</main>
<script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.11/katex.min.js"></script>
<script>
const D = ${payload};
const S = {};                 // per problem: {versions:[{fields, note, instr}], sel, compare, busy, ctl, level, approve}
let sample = null, sampleChecked = false;
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const LEVELS = [["hints", "Hints"], ["worded", "Word solution"], ["conventional", "Conventional solution"], ["mistakes", "Watch out"]];

function texOk(s) {
  const bad = [];
  for (const m of String(s || "").replace(/!\[[^\]]*\]\([^)]*\)/g, "").matchAll(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g)) {
    try { katex.renderToString(m[1] || m[2], { displayMode: !!m[1], throwOnError: true, macros: { ...D.macros }, strict: "ignore" }); }
    catch (e) { bad.push(m[1] || m[2]); }
  }
  return bad;
}
function md(p, s) {
  if (!s) return "";
  const keep = [], hold = h => { keep.push(h); return "\u0000" + (keep.length - 1) + "\u0000"; };
  s = String(s).replace(/!\[[^\]]*\]\(asset:([^)\s]+)\)/g, (_, id) => { const f = p.figs[id]; return hold(f ? '<span class="fig"><img src="' + f.src + '" alt="' + esc(f.alt) + '"></span>' : '<span class="badtex">[missing figure ' + esc(id) + ']</span>'); });
  s = s.replace(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g, (m, d, i) => {
    try { return hold(katex.renderToString(d || i, { displayMode: !!d, throwOnError: true, macros: { ...D.macros }, strict: "ignore" })); }
    catch (e) { return hold('<span class="badtex" title="This formula does not display">' + esc(m) + '</span>'); }
  });
  s = esc(s).replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  s = s.split(/\n\n+/).map(par => { const L = par.trim().split("\n"); return L.every(l => /^- /.test(l)) ? "<ul>" + L.map(l => "<li>" + l.slice(2) + "</li>").join("") + "</ul>" : "<p>" + par.trim() + "</p>"; }).join("");
  return s.replace(/\u0000(\d+)\u0000/g, (_, n) => keep[n]);
}
const inline = (p, s) => md(p, s).replace(/^<p>|<\/p>$/g, "");
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const orig = p => ({ hints: p.sol.hints, worded: p.sol.worded, conventional: p.sol.conventional, mistakes: p.sol.mistakes });
const current = p => { const st = S[p.id]; return st.sel === 0 ? orig(p) : st.versions[st.sel - 1].fields; };
const reviewer = () => { const v = document.getElementById("reviewer").value.trim(); return v || "Reviewer"; };

function levelHTML(p, key, label, val, old, compare) {
  const changed = old !== undefined && !same(val, old);
  const body = key === "hints" ? val.map((h, i) => '<div class="aside hint' + (changed ? " changed" : "") + '"><div class="t">Hint ' + (val.length > 1 ? i + 1 : "") + '</div><div class="qtext">' + md(p, h) + '</div></div>').join("")
    : key === "mistakes" ? (val.length ? '<div class="aside' + (changed ? " changed" : "") + '"><div class="t">' + label + '</div><div class="qtext"><ul>' + val.map(m => "<li>" + inline(p, m) + "</li>").join("") + "</ul></div></div>" : "")
    : '<div class="aside' + (changed ? " changed" : "") + '"><div class="t">' + label + (changed ? " · changed" : "") + '</div><div class="qtext">' + md(p, val) + "</div></div>";
  const was = changed && compare ? '<div class="was"><div class="t">Before</div><div class="qtext">' + (Array.isArray(old) ? old.map(x => md(p, x)).join("") : md(p, old)) + "</div></div>" : "";
  return body + was;
}

function card(p) {
  const st = S[p.id], cur = p.sol ? current(p) : null, base = p.sol ? orig(p) : null;
  const d = p.difficulty || {};
  const keyKeys = p.answer.keys || [];
  const opts = p.options ? '<ol class="opts">' + Object.entries(p.options).map(([k, v]) => '<li class="' + (keyKeys.includes(k) ? "key" : "") + '"><span class="k">' + k + '</span><div class="v">' + inline(p, v) + "</div></li>").join("") + "</ol>" : "";
  const key = p.answer.keys ? "Answer key: " + p.answer.keys.join(", ") : "Answer: " + esc(p.answer.value ?? p.answer.text ?? "");
  const issues = (p.sol && p.sol.issues) || [];
  let sol = '<p class="status">No solutions yet. Ask for them to be written first.</p>';
  if (p.sol) {
    const vers = '<div class="vers" role="group" aria-label="Versions">' + ['Original'].concat(st.versions.map((_, i) => "Version " + (i + 1))).map((l, i) => '<button data-v="' + i + '" class="' + (i === st.sel ? "on" : "") + '">' + l + "</button>").join("") +
      (st.versions.length ? '<label><input type="checkbox" data-cmp ' + (st.compare ? "checked" : "") + "> Show what changed</label>" : "") + "</div>";
    const why = Object.entries(p.sol.distractors || {}).sort();
    const whyHTML = why.length ? '<div class="aside"><div class="t">Why not the other options (from the solutions file; not changed here)</div><div class="qtext">' + why.map(([k, v]) => "<p><b>(" + esc(k) + ")</b> " + inline(p, v) + "</p>").join("") + "</div></div>" : "";
    const lv = LEVELS.map(([k, l]) => levelHTML(p, k, l, cur[k], st.sel ? base[k] : undefined, st.compare) + (k === "conventional" ? whyHTML : "")).join("");
    const v = st.sel ? st.versions[st.sel - 1] : null;
    const note = v ? '<div class="note"><b>Claude:</b> ' + esc(v.note || "Revised.") + (v.check ? ' <span class="status">' + esc(v.check) + "</span>" : "") + (v.bad && v.bad.length ? '<br><span class="status err">Some formulas don\'t display. Ask Claude to fix them before sending.</span>' : "") + "</div>" : "";
    sol = vers + note + lv;
  }
  const hist = st.versions.length ? '<ol class="history">' + st.versions.map((v, i) => "<li>Version " + (i + 1) + ": " + esc(v.instr) + "</li>").join("") + "</ol>" : "";
  const revise = p.sol ? '<section class="revise" aria-label="Revise with Claude"><h4>Revise with Claude</h4>' +
    '<label class="status" for="ins-' + p.id + '">What should change? Claude edits the version shown above.</label>' +
    '<textarea id="ins-' + p.id + '" placeholder="e.g. Hint 2 gives away the answer; make it point to the phase only."></textarea>' +
    '<div class="row"><label class="status" for="lvl-' + p.id + '">Change</label><select id="lvl-' + p.id + '"><option value="all">any part, as needed</option><option value="hints">hints only</option><option value="worded">word solution only</option><option value="conventional">conventional solution only</option><option value="mistakes">watch out only</option></select>' +
    '<button class="btn" data-rev ' + (st.busy || sample === false ? "disabled" : "") + ">" + (st.busy ? "Revising…" : "Revise") + "</button>" + (st.busy ? '<button class="btn ghost" data-stop>Stop</button>' : "") +
    '</div><div class="status" id="msg-' + p.id + '" role="status">' + esc(st.msg || "") + "</div>" + hist + "</section>" : "";
  const levelSel = '<label class="status" for="xl-' + p.id + '">Difficulty</label><select id="xl-' + p.id + '">' + [1, 2, 3, 4, 5, 6].map(n => '<option ' + (n === (st.level || d.expert || d.ai) ? "selected" : "") + ">" + n + "</option>").join("") + "</select>";
  const changed = p.sol && st.sel > 0 && !same(current(p), orig(p));
  const send = p.sol ? '<section class="send"><div class="row">' + levelSel +
    '<label class="status"><input type="checkbox" data-appr ' + (st.approve !== false ? "checked" : "") + "> Mark as reviewed when applied</label></div>" +
    '<div class="row">' + (changed ? '<a class="btn go" data-send target="_blank" rel="noopener" href="#">Request a change</a>' : '<a class="btn go" data-send target="_blank" rel="noopener" href="#">Approve as is</a>') +
    '<button class="btn ghost" data-copy>Copy the text</button></div><div class="status" id="send-' + p.id + '"></div></section>' : "";
  return '<article class="card" id="' + p.id + '"><div class="idline"><span class="qn">Q' + (p.qno || "?") + '</span><span class="pid">' + p.id + '</span>' + (p.ws ? '<span class="tag">' + esc(p.ws) + '</span>' : '') + '<span class="tag">v' + p.version + '</span><span class="tag">' + esc((p.sol ? p.sol.status : p.status).replace("_", " ")) + "</span></div>" +
    '<div class="meta">' + esc(p.source || "No source tag") + (d.ai ? " · AI level " + d.ai + (d.ai_reason ? ": " + esc(d.ai_reason) : "") : "") + "</div>" +
    (issues.length ? '<div class="flags"><b>Needs your eye</b><ul>' + issues.map(i => "<li>" + esc(i) + "</li>").join("") + "</ul></div>" : "") +
    '<div class="qtext">' + md(p, p.stem) + "</div>" + opts + '<div class="keynote">' + key + "</div>" +
    '<div class="student"><span class="lbl">Solutions, as students see them</span>' + sol + "</div>" + revise + send + "</article>";
}

function render(id) {
  const ps = id ? D.problems.filter(p => p.id === id) : D.problems;
  for (const p of ps) {
    const el = document.getElementById(p.id), html = card(p);
    if (el) { const keepTxt = (document.getElementById("ins-" + p.id) || {}).value; const keepLvl = (document.getElementById("lvl-" + p.id) || {}).value; el.outerHTML = html; if (keepTxt) document.getElementById("ins-" + p.id).value = keepTxt; if (keepLvl) document.getElementById("lvl-" + p.id).value = keepLvl; }
    else document.getElementById("cards").insertAdjacentHTML("beforeend", html);
    wire(p);
  }
}

function wire(p) {
  const el = document.getElementById(p.id), st = S[p.id];
  el.querySelectorAll("[data-v]").forEach(b => b.onclick = () => { st.sel = +b.dataset.v; render(p.id); });
  const cmp = el.querySelector("[data-cmp]"); if (cmp) cmp.onchange = () => { st.compare = cmp.checked; render(p.id); };
  const rev = el.querySelector("[data-rev]"); if (rev) rev.onclick = () => revise(p);
  const stop = el.querySelector("[data-stop]"); if (stop) stop.onclick = () => st.ctl && st.ctl.abort();
  const xl = el.querySelector("#xl-" + p.id); if (xl) xl.onchange = () => { st.level = +xl.value; updateSend(p); };
  const ap = el.querySelector("[data-appr]"); if (ap) ap.onchange = () => { st.approve = ap.checked; updateSend(p); };
  const cp = el.querySelector("[data-copy]"); if (cp) cp.onclick = () => copyBody(p);
  updateSend(p);
}

function issueParts(p) {
  const st = S[p.id], cur = current(p), base = orig(p), d = p.difficulty || {};
  const fields = {};
  for (const [k] of LEVELS) if (!same(cur[k], base[k])) fields[k] = cur[k];
  const kind = Object.keys(fields).length ? "change" : "approve";
  const level = st.level || d.expert || d.ai || null;
  const approve = st.approve !== false;
  const instr = st.versions.slice(0, st.sel).map(v => v.instr);
  const json = { kind, id: p.id, base: p.base, reviewer: reviewer(), approve, expert_level: level, instructions: instr };
  if (kind === "change") json.fields = fields;
  const lines = ["@claude apply this review from the review page.", "",
    "**Problem:** " + p.id + " | Q" + (p.qno || "?") + " | " + D.topic + " " + D.topicName,
    "**Reviewer:** " + reviewer() + " | **Mark as reviewed:** " + (approve ? "yes" : "no") + " | **Difficulty:** " + (level || "not set")];
  if (instr.length) lines.push("", "**What the reviewer asked:**", ...instr.map((x, i) => (i + 1) + ". " + x));
  if (kind === "change") {
    for (const [k, l] of LEVELS) if (k in fields) {
      lines.push("", "### " + l);
      if (k === "hints") fields[k].forEach((h, i) => lines.push((i + 1) + ". " + h.replace(/\n+/g, " ")));
      else if (k === "mistakes") fields[k].forEach(m => lines.push("- " + m));
      else lines.push(fields[k]);
    }
  } else lines.push("", "No changes: approve the solutions as they are.");
  const title = "Review: " + p.id + (kind === "change" ? " (changes: " + Object.keys(fields).map(k => LEVELS.find(l => l[0] === k)[1].toLowerCase()).join(", ") + ")" : " (approve)");
  const body = lines.join("\n") + "\n\n<details><summary>Exact text for Claude</summary>\n\n\u0060\u0060\u0060json\n" + JSON.stringify(json, null, 1) + "\n\u0060\u0060\u0060\n\n</details>\n";
  return { title, body, kind };
}
function updateSend(p) {
  const a = document.querySelector("#" + p.id + " [data-send]"); if (!a) return;
  const { title, body } = issueParts(p);
  const url = "https://github.com/" + D.repo + "/issues/new?title=" + encodeURIComponent(title) + "&body=" + encodeURIComponent(body);
  const msg = document.getElementById("send-" + p.id);
  const bad = S[p.id].sel ? (S[p.id].versions[S[p.id].sel - 1].bad || []) : [];
  if (url.length > 7500) {
    a.href = "https://github.com/" + D.repo + "/issues/new?title=" + encodeURIComponent(title);
    msg.textContent = "This change is too long to send in one link. Press Copy the text first, then paste it into the issue that opens.";
  } else { a.href = url; msg.textContent = bad.length ? "Some formulas don't display; better to ask Claude to fix them first." : "Opens GitHub with everything filled in. Check it and press Submit."; }
  a.onclick = () => { setTimeout(() => { const j = document.querySelector('#jump a[href="#' + p.id + '"]'); if (j) j.classList.add("done"); }, 300); };
}
async function copyBody(p) {
  const { body } = issueParts(p), msg = document.getElementById("send-" + p.id);
  try { await navigator.clipboard.writeText(body); msg.textContent = "Copied. Now press the green button and paste into the issue's description."; }
  catch (e) {
    msg.innerHTML = 'Your browser blocked copying. Select all the text below, copy it, then press the green button.<textarea readonly style="width:100%;min-height:120px;margin-top:6px;font:12px var(--mono)">' + esc(body) + "</textarea>";
    const ta = msg.querySelector("textarea"); ta.focus(); ta.select();
  }
}

function prompt(p, instr, scope) {
  const cur = current(p);
  const figs = Object.entries(p.figs).map(([id, f]) => id + ": " + f.alt).join("\n") || "(none)";
  const ans = p.answer.keys ? p.answer.keys.join(", ") : (p.answer.value ?? p.answer.text);
  const earlier = S[p.id].versions.slice(0, S[p.id].sel).map((v, i) => (i + 1) + ". " + v.instr).join("\n") || "(none)";
  return "You are revising the solutions to one JEE/NEET physics problem for a physics teacher who is reviewing them.\n\n" +
    "Follow this house guide and maths style exactly:\n\n<guide>\n" + D.guide + "\n</guide>\n\n<maths_style>\n" + D.style + "\n</maths_style>\n\n" +
    "<problem id=\"" + p.id + "\">\nQuestion: " + p.stem + "\n" + (p.options ? "Options:\n" + Object.entries(p.options).map(([k, v]) => "(" + k + ") " + v).join("\n") + "\n" : "") +
    "Figures (descriptions): \n" + figs + "\nAnswer key: " + ans + "\n</problem>\n\n" +
    "<current_solutions>\n" + JSON.stringify(cur, null, 1) + "\n</current_solutions>\n\n" +
    "Earlier instructions from the reviewer, already applied: \n" + earlier + "\n\n" +
    "The reviewer now asks: \"" + instr + "\"\n" +
    (scope === "all" ? "Change whichever parts this needs, and nothing else." : "Change only \"" + scope + "\". Copy every other field exactly, character for character.") + "\n" +
    "Keep the three levels consistent with each other (same method, numbers and answer). Never change the answer key; if you think it is wrong, say so in the note and keep the solutions matching the key.\n\n" +
    'Reply with only a JSON object: {"hints": [string], "worded": string, "conventional": string, "mistakes": [string], "note": "one or two sentences on what you changed", "answer_check": "the answer your full solution reaches, e.g. B"}';
}
async function revise(p) {
  const st = S[p.id], box = document.getElementById("ins-" + p.id), scope = document.getElementById("lvl-" + p.id).value;
  const instr = box.value.trim();
  if (!instr) { st.msg = "Write what should change first."; render(p.id); return; }
  if (!sample) { st.msg = "Claude isn't available in this view."; render(p.id); return; }
  st.busy = true; st.msg = "Claude is thinking. This usually takes 20 to 60 seconds."; st.ctl = new AbortController(); render(p.id);
  try {
    const r = await sample.json(prompt(p, instr, scope), { modelTier: "complex", cache: false, signal: st.ctl.signal });
    const f = { hints: Array.isArray(r.hints) ? r.hints.map(String) : current(p).hints, worded: typeof r.worded === "string" ? r.worded : current(p).worded,
                conventional: typeof r.conventional === "string" ? r.conventional : current(p).conventional, mistakes: Array.isArray(r.mistakes) ? r.mistakes.map(String) : current(p).mistakes };
    const bad = [].concat(...f.hints.map(texOk), texOk(f.worded), texOk(f.conventional), ...f.mistakes.map(texOk));
    const keyStr = p.answer.keys ? p.answer.keys.join(",") : String(p.answer.value ?? "");
    const agrees = r.answer_check && keyStr ? String(r.answer_check).replace(/[^A-Za-z0-9.,-]/g, "").toUpperCase().includes(keyStr.toUpperCase()) : null;
    st.versions = st.versions.slice(0, st.sel);
    st.versions.push({ fields: f, note: String(r.note || ""), instr, bad, check: agrees === false ? "Its full solution reaches " + r.answer_check + ", not the key " + keyStr + ". Check before sending." : "" });
    st.sel = st.versions.length; st.compare = true; st.msg = "";
    const nb = document.getElementById("ins-" + p.id); if (nb) nb.value = "";
  } catch (e) {
    st.msg = e.code === "cancelled" ? "Stopped." : e.code === "not_granted" || e.code === "sampling_disabled" ? "Claude wasn't allowed for this page, so revising is off." :
      e.code === "rate_limited" ? "Claude is busy or your usage limit is reached. Try again in a while." : e.code === "invalid_json" ? "Claude's answer came back in the wrong shape. Press Revise again." :
      "Something went wrong reaching Claude. Press Revise to try again.";
    if (e.code === "not_granted" || e.code === "sampling_disabled") { sample = false; document.getElementById("claude-off").hidden = false; }
  } finally { st.busy = false; st.ctl = null; render(p.id); }
}

document.getElementById("eyebrow").textContent = "Solution review · " + D.chapter;
document.getElementById("title").textContent = D.topic + " · " + D.topicName;
try { const n = localStorage.getItem("reviewer"); if (n) document.getElementById("reviewer").value = n; } catch (e) {}
document.getElementById("reviewer").addEventListener("input", e => { try { localStorage.setItem("reviewer", e.target.value); } catch (_) {} D.problems.forEach(updateSend); });
document.getElementById("jump").innerHTML = D.problems.map(p => '<a href="#' + p.id + '">Q' + (p.qno || "?") + " " + p.id.slice(-3) + "</a>").join("");
D.problems.forEach(p => S[p.id] = { versions: [], sel: 0, compare: true, busy: false, approve: true });
render();
(async () => {
  try { sample = window.claude && window.claude.use ? await window.claude.use("sample") : null; } catch (e) { sample = null; }
  if (!sample) { sample = false; document.getElementById("claude-off").hidden = false; }
  render();
})();
</script>`;
fs.writeFileSync(out, html);
console.log(`Review workbench: ${t.code} ${t.name}, ${data.length} problems → ${out} (${Math.round(html.length / 1024)} KB)`);
