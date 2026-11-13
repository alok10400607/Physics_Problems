# Physics_Problems

A bank of JEE/NEET physics problems with three-level solutions, and the website built from it. The owner is a physics teacher; reviewers check the physics. Write for them in plain language.

## Rules

- **The bank is the master copy.** `bank/problems/`, `bank/solutions/` and `bank/collections/` hold everything. `site/data/` is generated: never edit it by hand.
- **Every change is a pull request.** Branch from `main`, and never merge or push to `main` yourself.
- **Problem IDs are permanent.** Only the importers assign them, from `bank/registry.json`. Never reuse, renumber or hand-assign an ID.
- **Never change an answer key silently.** If your solution disagrees with the key, flag it for the reviewer.
- **Topic codes** come only from `bank/topics.json`, as 4-digit text (e.g. "0211").
- **Interactive pages** (the "Exemplars & animations" tab) live in `bank/labs/<series>/`, listed in `bank/labs/index.json` with the subtopics each page belongs to (the first is its home). Add a page by copying the HTML there and adding a line to the index; the build copies it to `site/labs/`. Never edit `site/labs/`.
- **Maths** is Markdown with LaTeX, following `docs/maths-style.md`. Figures are referred to as `![](asset:<asset id>)`.
- Before every commit: `node tools/check_bank.js` must show no errors, then run `node tools/build_site.js`.

## Skills

- `bank-import`: import a DOCX worksheet, a new version of one, its solutions file, or a CSV question list (also runs unattended from `inbox/`).
- `solution-writer`: write hints, worded and full solutions for a subtopic.
- `solution-review`: a conversational review session that saves approved work.

## Requests in GitHub comments

When someone writes `@claude` with a request:
- **A small edit** ("in P000030 change option B to …"): edit the files and run the checks. On a pull request, commit to that pull request's branch; otherwise open a new pull request. Say in the reply what changed, and whether it was major (answer, options, data) or minor.
- **"write solutions for <topic>":** follow the solution-writer skill and open a pull request.
- **An answer to a question you asked in an import pull request** (a duplicate, a topic choice): apply it on that pull request's branch.

Keep replies short: what changed, what still needs the owner.

## Review requests from the review page

Issues titled `Review: P000123 …` come from the review page. Their body ends with a JSON block, which is the exact agreed result:

```json
{"kind": "change" | "approve", "id": "P000123", "base": "<fingerprint>", "reviewer": "<name>",
 "approve": true, "expert_level": 3, "instructions": ["…"], "fields": {"hints": [...], "worded": "...", "conventional": "...", "mistakes": [...]}}
```

To apply one:
1. **Branch.** `git checkout main && git pull`, then `git checkout -b review/<id>-<issue number>`.
2. **Check the base.** Run `node tools/solution_fingerprint.js <id>`. If the result differs from `base`, the solution changed after the reviewer opened the page: change nothing, and reply on the issue asking them to reopen the latest review page.
3. **Apply the text exactly.** Write each key in `fields` into the solution file as given, without rewording. A missing key means "keep as is". `kind: "approve"` has no fields.
4. **Check before saving.**
   - `node tools/check_bank.js` must pass.
   - The answer in the full solution must agree with the key. If it doesn't, still open the PR, but say so at the top; never change the key.
   - If the three levels no longer agree with each other, say which in the PR. Don't fix it.
5. **Approve if asked.** If `approve` is true:
   - The solution gets `status: "reviewed"` and `reviewed_by: {"name": <reviewer>, "date": <today>, "notes": <instructions joined>}`.
   - The problem gets `status: "reviewed"`, and `difficulty.expert` = `expert_level` (or `difficulty.ai` if absent).
   Otherwise set the solution's status to `ai_solved`.
6. **Open the PR.** Run `node tools/build_site.js`, commit, push, and open a PR titled `Review <id>: <short summary>` whose body says `Closes #<issue>`. Reply on the issue with the PR link.

## Tools

| Command | Does |
|---|---|
| `python3 -I tools/import_docx.py <docx> <map> --check/--write` | Worksheet import |
| `python3 -I tools/import_docx.py <docx> <map> --update --check/--write` | New version of a worksheet already in the bank (keeps IDs) |
| `python3 -I tools/import_solutions.py <docx> --check/--write [--only 0305]` | Solutions file (`<collection>_Solutions_v<n>.docx`) |
| `python3 -I tools/make_map.py <docx>` | Draft a worksheet's topic map |
| `python3 -I tools/import_csv.py <csv> --collection <ID> --title "<t>" [--codes <json>] --check/--write` | CSV import |
| `python3 -I tools/set_alt.py <json>` | Set figure alt text |
| `python3 -I tools/trim_figures.py [IDs]` | Trim blank margins from figures |
| `node tools/check_bank.js` | Check the whole bank |
| `node tools/build_site.js` | Build the site's data |
| `node tools/review_workbench.js --topic <code> --out <html>` | Interactive review page (publish with `sample`) |
| `node tools/review_page.js --out <html> --topic <code>` | Read-only review page for a subtopic |
| `node tools/solution_fingerprint.js <id>` | Fingerprint of a problem's solutions |
