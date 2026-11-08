// Reads [[where, text], ...] as JSON on stdin; prints formulas that KaTeX cannot render.
// Uses the same KaTeX version and macros as the site. Exit 0 = all render, 1 = failures.
const katex = require('katex');
const macros = require('./katex-macros.json');
const items = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const bad = [];
for (const [where, text] of items) {
  if (!text) continue;
  const stripped = text.replace(/!\[[^\]]*\]\([^)]*\)/g, '');
  for (const m of stripped.matchAll(/\$\$([\s\S]+?)\$\$|\$([^$]+?)\$/g)) {
    const tex = m[1] || m[2];
    try { katex.renderToString(tex, { displayMode: !!m[1], throwOnError: true, strict: code => code === 'unicodeTextInMathMode' ? 'ignore' : 'error', macros: { ...macros } }); }
    catch (e) { bad.push({ where, tex, error: e.message.split('\n')[0].replace(/^KaTeX parse error: /, '') }); }
  }
  if (((stripped.match(/(?<!\\)\$/g) || []).length) % 2) bad.push({ where, tex: '(whole field)', error: 'unbalanced $' });
}
process.stdout.write(JSON.stringify(bad));
process.exit(bad.length ? 1 : 0);
