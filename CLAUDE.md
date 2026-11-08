# Physics_Problems

A bank of JEE/NEET physics problems with three-level solutions, and the website built from it. The owner is a physics teacher; reviewers check the physics. Write for them in plain language.

## Rules

- **The bank is the master copy.** `bank/problems/`, `bank/solutions/` and `bank/collections/` hold everything. `site/data/` is generated: never edit it by hand.
- **Every change is a pull request.** Branch from `main`, and never merge or push to `main` yourself.
- **Problem IDs are permanent.** Only the importers assign them, from `bank/registry.json`. Never reuse, renumber or hand-assign an ID.
- **Never change an answer key silently.** If your solution disagrees with the key, flag it for the reviewer.
- **Topic codes** come only from `bank/topics.json`, as 4-digit text (e.g. "0211").
- **Maths** is Markdown with LaTeX, following `docs/maths-style.md`. Figures are referred to as `![](asset:<asset id>)`.
- Before every commit: `node tools/check_bank.js` must show no errors, then run `node tools/build_site.js`.

## Skills

- `bank-import`: import a DOCX worksheet or CSV question list (also runs unattended from `inbox/`).
- `solution-writer`: write hints, worded and full solutions for a subtopic.
- `solution-review`: a conversational review session that saves approved work.

## Requests in GitHub comments

When someone writes `@claude` with a request:
- **A small edit** ("in P000030 change option B to …"): edit the files and run the checks. On a pull request, commit to that pull request's branch; otherwise open a new pull request. Say in the reply what changed, and whether it was major (answer, options, data) or minor.
- **"write solutions for <topic>":** follow the solution-writer skill and open a pull request.
- **An answer to a question you asked in an import pull request** (a duplicate, a topic choice): apply it on that pull request's branch.

Keep replies short: what changed, what still needs the owner.

## Tools

| Command | Does |
|---|---|
| `python3 -I tools/import_docx.py <docx> <map> --check/--write` | Worksheet import |
| `python3 -I tools/make_map.py <docx>` | Draft a worksheet's topic map |
| `python3 -I tools/import_csv.py <csv> --collection <ID> --title "<t>" [--codes <json>] --check/--write` | CSV import |
| `python3 -I tools/set_alt.py <json>` | Set figure alt text |
| `python3 -I tools/trim_figures.py [IDs]` | Trim blank margins from figures |
| `node tools/check_bank.js` | Check the whole bank |
| `node tools/build_site.js` | Build the site's data |
| `node tools/review_page.js --out <html> --topic <code>` | Review page for a subtopic |
