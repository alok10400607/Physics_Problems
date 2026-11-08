// Prints a short fingerprint of a problem's solution text, so a review request can tell whether the
// solution changed after the reviewer opened the review page.
// Usage: node tools/solution_fingerprint.js P000030      (also used by tools/review_workbench.js)
const fs = require('fs'), path = require('path'), crypto = require('crypto');
const BANK = path.resolve(__dirname, '..', 'bank');
function fingerprint(sol) {
  const pick = { hints: sol.hints || [], worded: sol.worded || null, conventional: sol.conventional || null, mistakes: sol.mistakes || [] };
  return crypto.createHash('sha256').update(JSON.stringify(pick)).digest('hex').slice(0, 12);
}
module.exports = { fingerprint };
if (require.main === module) {
  const id = process.argv[2];
  const f = path.join(BANK, 'solutions', id.slice(0, 4), `${id}.json`);
  console.log(fs.existsSync(f) ? fingerprint(JSON.parse(fs.readFileSync(f, 'utf8'))) : 'none');
}
