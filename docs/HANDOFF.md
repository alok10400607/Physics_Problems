# Handover: site revision (12 November 2026)

Read this first in a new session, together with `CLAUDE.md`.

## Where things stand

| Item | State |
|---|---|
| Bank | 534 problems, P000001–P000534, in 6 chapters (03, 04, 05, 07, 08, 17) |
| PRs #5, #6 | Merged into `main` on 8 November |
| This branch | `next/solutions-importer`: 03MSL v3 applied, 03MSL solutions v8 imported, solution links on the student page. Open as a PR. |
| Live site | https://physics-problems.alok1040.workers.dev (Cloudflare builds from `main` automatically) |
| Review pages | 1715: https://claude.ai/artifact/4ggmBak5o3DRwFVd9rw51B · 0305 (03MSL Q1–Q10): https://claude.ai/artifact/NBp75iWxkb4DfeDKGdnaua. Both built by `tools/review_workbench.js`, with `capabilities: {"sample": {}}` |
| Automation | `inbox/` uploads (now including problems + solutions pairs) and `@claude` comments work |
| Open decision | Cloudflare Access to make the site private. The site is currently public. |
| Known issue | Cloudflare preview builds of branches fail (production builds of `main` succeed); likely branch names with `/` and capitals |
| Source fixes owed by the owner | 04MIP Q72 (P000252) lacks its four option graphs; 03MSL Q82 (P000166) still has four unlabelled pictures instead of (A)–(D) options; JeeProblems.csv needs an Answer column. (03MSL Q84 was fixed in v3.) |
| Older debt | 46 problems still have maths typed with `<sup>` tags (e.g. P000113's options); fix during solution writing or review |
| Not stored | The solutions file's "Notes: Sec. …" lines (links to the revision notes). If the owner wants them on the site, add a `notes_ref` field to the solution schema and re-import |

## Done on 12 November: separate problem and solution files

From now on, each topic comes as two files:
- **Problems:** e.g. `worksheets/03MSL_v3.docx` (a new version of the already-imported 03MSL_v2, P000085–P000180)
- **Solutions:** e.g. `worksheets/03MSL_Solutions_v8.docx`, written with the owner's `jee-worksheet-solutions` skill

Both sample files are on this branch (`next/solutions-importer`, which is based on PR #6).

### Layout of the solutions file (03MSL_Solutions_v8)

- `#` heading: subtopic name (matches TopicCode_v2 names)
- `##` heading: `Q<n> · <short title>`, numbered as in the problems file
- `###` sections in each question, mapped to the bank's solution fields:

| Section | Solution field |
|---|---|
| Problem | not stored; use it to match against the bank and flag differences |
| Hint | `hints` |
| Think it through | `worded` |
| Another way: … | optional; append to `worded` as a second paragraph headed with its title, or ask the owner |
| Worked solution | `conventional` |
| Answer | check against the answer key; flag any disagreement, never change the key |
| Watch out | `mistakes` |

- 129 figures. Solution figures become assets named `<problem>-sol-<n>`, referenced in the solution text.

### To build

1. **`tools/import_solutions.py`:** reads a solutions DOCX and matches each question to its problem.
   - Match first by `[P000123]` tag if present.
   - Otherwise match by collection (03MSL) and question number, after checking the problem text agrees.
   - Write `bank/solutions/...` with author `worksheet` and status `ai_solved` or `draft`.
   - Give the same pre-flight report as the worksheet importer: missing parts, unmatched questions, answers that disagree with the key, formulas that don't render.
2. **Problems file v3 vs v2:** 03MSL_v2 is already imported. Compare v3 against the bank. Update only changed problems, as an edit route that keeps the IDs, and report new or removed questions.
3. **Problem page (student view):** show three links under each problem: **Hint · Word Solution · Conventional Solution**.
   - The owner's choice: **Hint is always available; the two solutions unlock after an attempt** (answering, or "I give up").
   - "Watch out" shows with the conventional solution.
4. Extend the `bank-import` skill and `inbox/` workflow to accept a problems + solutions pair.
5. Rebuild the review page for a 03MSL subtopic so the owner can review the imported solutions.

### What was built

1. `tools/import_solutions.py` (`--check`, `--write`, `--only`, `--replace`, `--report`). "No-pen route" sections are treated like "Another way". "Why the other options are there" goes to `distractors` when each sentence names one option. Word's equations are brought to the maths style (`\unit{}`, `\vec`, `\ihat`, `\mkern`, `\text{}`). 03MSL: 96 solutions, all answers agree with the key, all `ai_solved`, 94 solution figures with alt text.
2. `tools/import_docx.py --update`: matches by question number after a text check, rewrites only changed problems (type, stem, options, answer, figures), keeps IDs and alt text. 03MSL v3 changed 10 problems; see the PR.
3. Student page: Hint · Word solution · Conventional solution under each question. Hint is open from the start; the solutions unlock after an answer, "I give up", or "Show answer" on written questions. Watch out and "Why not the other options" come with the conventional solution. Nothing shows during a timed test until it is submitted.
4. `bank-import` skill, `inbox/README.md`, the Actions prompt and `docs/worksheet-contract.md` describe pairs and new versions.
5. Review page for 0305 (link above); the workbench now shows "Why not the other options" and uses the new level names.

### Next

- The owner reviews 0305, then the other 03MSL subtopics: `node tools/review_workbench.js --topic <code> --out <file>`.
- The review JSON cannot yet change `distractors`; add it to the workbench and `solution_fingerprint.js` if reviewers want to edit them.

## How to start the new session

Attach the repository `alok10400607/Physics_Problems` (GitHub is already connected), then check out `next/solutions-importer`.
