// Usage: node validate.js <chapter.json>
const fs = require('fs'), path = require('path'), katex = require('katex');
const file = process.argv[2], dir = path.dirname(file);
const d = JSON.parse(fs.readFileSync(file, 'utf8'));
const errors = [], notes = [];
const fields = q => [['question', q.question], ['answer', q.answer], ['hint', q.hint], ['think_further', q.think_further],
  ...Object.entries(q.options || {}).map(([k, v]) => ['option ' + k, typeof v === 'string' ? v : ''])];
let mathCount = 0;
d.questions.forEach((q, i) => {
  const id = `Q${q.number}`;
  if (q.number !== i + 1) errors.push(`${id}: numbering gap (expected Q${i + 1})`);
  if (!q.question || q.question.length < 15) errors.push(`${id}: question text missing or too short`);
  if (q.answer == null) errors.push(`${id}: no answer in Answer Key`);
  if (q.type === 'mcq') {
    const ks = Object.keys(q.options).join('');
    if (ks !== 'ABCD') errors.push(`${id}: options are "${ks}", expected ABCD`);
    if (!/^[A-D]$/.test(q.answer || '')) errors.push(`${id}: MCQ answer "${q.answer}" is not a single letter A–D`);
    Object.entries(q.options).forEach(([k, v]) => { if (typeof v === 'string' && !v.trim()) errors.push(`${id}: option ${k} empty`); });
  }
  [...q.figures, ...Object.values(q.options || {}).filter(v => v.image).map(v => v.image)]
    .forEach(f => { if (!fs.existsSync(path.join(dir, f))) errors.push(`${id}: missing image ${f}`); });
  for (const [name, s] of fields(q)) {
    if (!s) continue;
    for (const m of s.matchAll(/\$([^$]+)\$/g)) {
      mathCount++;
      try { katex.renderToString(m[1], { throwOnError: true, strict: 'ignore' }); }
      catch (e) { errors.push(`${id} ${name}: formula does not render: ${m[1]} — ${e.message.split('\n')[0]}`); }
    }
    if ((s.match(/\$/g) || []).length % 2) errors.push(`${id} ${name}: unbalanced $ delimiter`);
    if (/\\\(|\\\[|\{width=/.test(s)) errors.push(`${id} ${name}: leftover conversion markup`);
  }
});
const byType = d.questions.reduce((a, q) => (a[q.type] = (a[q.type] || 0) + 1, a), {});
console.log(`Questions: ${d.questions.length}  types: ${JSON.stringify(byType)}  formulas checked: ${mathCount}`);
d.subtopics.forEach(s => console.log(`  ${s.code}  ${s.name}  (${s.count})`));
console.log(errors.length ? `\nERRORS (${errors.length}):\n  ` + errors.join('\n  ') : '\nNo errors.');
process.exit(errors.length ? 1 : 0);
