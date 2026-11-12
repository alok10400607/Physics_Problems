# Handover: site revision (12 November 2026)

Read this first in a new session, together with `CLAUDE.md`.

## Where things stand

| Item | State |
|---|---|
| Bank | 534 problems, P000001–P000534, in 6 chapters (03, 04, 05, 07, 08, 17), on `main` |
| PR #5 | Energy in SHM (1715) pilot solutions and the `@claude` review-request rules. **Open.** Merge before #6. |
| PR #6 | Student view: chapters → subtopics → Practice / Custom test / Notes / Exemplars tabs. **Open.** |
| Live site | https://physics-problems.alok1040.workers.dev (Cloudflare builds from `main` automatically) |
| Review page (1715) | https://claude.ai/artifact/4ggmBak5o3DRwFVd9rw51B, built by `tools/review_workbench.js`, published with `capabilities: {"sample": {}}` |
| Automation | `inbox/` uploads and `@claude` comments work (secret `CLAUDE_CODE_OAUTH_TOKEN` is set) |
| Open decision | Cloudflare Access to make the site private. The site is currently public. |
| Known issue | Cloudflare preview builds of branches fail (production builds of `main` succeed); likely branch names with `/` and capitals |
| Source fixes owed by the owner | 03MSL Q84 (P000168) and 04MIP Q72 (P000252) lack their four option graphs; JeeProblems.csv needs an Answer column |

## The next task: separate problem and solution files

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

## How to start the new session

Attach the repository `alok10400607/Physics_Problems` (GitHub is already connected), then check out `next/solutions-importer`.
