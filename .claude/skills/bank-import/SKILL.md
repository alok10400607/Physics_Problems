---
name: bank-import
description: Import a reviewed DOCX physics worksheet, its separate solutions file, or a CSV question list into the problem bank of this repository. Runs the pre-flight checks, assigns permanent problem IDs, updates a new version of a worksheet in place, imports hints and worded and conventional solutions, extracts and names figures, writes alt text, checks the whole bank and delivers the result as a pull request with a preview. Use when the user attaches a worksheet, a solutions file (e.g. 03MSL_Solutions_v8.docx) or a CSV and asks to import, add or load it, when files arrive in inbox/ (unattended mode), or when a new version or an edited worksheet with [P000123] ID tags is re-imported.
---

# Import a worksheet into the bank

Nothing enters the bank without the user's approval: the result is always a pull request.

## 1. Get the inputs

- The DOCX: an attachment, or a file in `worksheets/`. Copy attachments into `worksheets/` (keep the user's file name).
- The topic map `bank/imports/maps/<collection>.json`: the collection ID (e.g. `17SHM`), title, chapter code, and every Heading 2 section title mapped to its topic code. If it doesn't exist, list the worksheet's Heading 2 titles (`pandoc <file> -t markdown | grep '^## '`), propose codes from `bank/topics.json`, and confirm them with the user before continuing. Never invent a topic code that isn't in `bank/topics.json`.
- `cd tools && npm install` once per session if `tools/node_modules` is missing.

## 2. Pre-flight check (writes nothing)

```bash
python3 -I tools/import_docx.py worksheets/<file>.docx bank/imports/maps/<collection>.json --check
```

Report to the user in plain words:
- **Blocking** items: the import cannot continue. Say exactly what to fix in the DOCX (question number, what is wrong). Stop and wait for a corrected file.
- **Warnings**: summarise by kind with counts (no source tag, no level tag, maths typed as plain text, small figures, provisional topic codes). List possible duplicates individually, showing both texts briefly, and ask whether each is a true duplicate.
- **Auto-fixes**: the count, plus two examples.

## 3. Import

Only when there are no blocking items:

```bash
git checkout main && git pull -q origin main
git checkout -b import/<collection>
python3 -I tools/import_docx.py worksheets/<file>.docx bank/imports/maps/<collection>.json --write
```

Confirmed duplicates: set `duplicate_of` on the new problem, change its status to `retired`, and add its sources to the surviving problem.

## 4. Alt text for every figure

Alt text is required before publishing. Build contact sheets of the new figures (label each with its asset ID; about 10 per sheet), look at each sheet, and write one or two plain sentences per figure:
- describe what is drawn: objects, labels, values, axes, curve shapes
- never state or hint at the answer, and never judge which option is right
- use the units and symbols shown in the figure

Write `{"<asset id>": "<alt>", ...}` to a scratch file and apply it with `python3 -I tools/set_alt.py <file>`.

## 5. Check and build

```bash
node tools/check_bank.js        # must end with "No errors"
node tools/build_site.js
```

Fix any error before going further. Then look at two or three imported questions on the built site (a figure question, an option-image question) at phone width.

## 6. Pull request

Commit everything (bank files, site data, the map, the worksheet). Push the branch, and open the PR through the REST API (`gh pr create` uses GraphQL, which is blocked in these sessions):

```bash
gh api repos/<owner>/<repo>/pulls -X POST -f title="Import <collection> (<first id>–<last id>)" \
  -f head="import/<collection>" -f base="main" -F body=@<body.md> --jq '.number, .html_url'
```

The PR body holds:
- counts: problems created (ID range), by type and by topic
- blocking items fixed before import, warnings, auto-fixes, duplicates and how they were handled
- figures marked `needs_redraw`
- a line telling the user that Cloudflare posts a preview link on the PR, and that merging publishes to the review site

End the PR body with the attribution lines from the session's instructions.

Tell the user in a few lines: what was imported, what needs their attention, and that the PR is ready to check and merge. Do not merge unless they ask.

## Re-importing an edited worksheet

A worksheet whose questions carry `[P000123]` tags updates those problems instead of creating new ones. The importer compares field by field, bumps the version of changed problems, and sends problems with major changes (answer, options, numbers in the stem) back for re-solving. Report every changed problem and whether the change was major or minor.

## A new version of a worksheet (e.g. 03MSL_v3 after 03MSL_v2)

If the collection is already in the bank, never import it as new. Use the update route, which keeps every ID:

```bash
python3 -I tools/import_docx.py worksheets/03MSL_v3.docx bank/imports/maps/03MSL.json --update --check
python3 -I tools/import_docx.py worksheets/03MSL_v3.docx bank/imports/maps/03MSL.json --update --write
```

The check lists under **EDITS** the problems that will change and how (type, stem, options, answer, figures); the write also compares the pictures themselves and may find a redrawn figure. Report every edited problem and say which answers changed: an answer change in the owner's new version is the owner's decision, so apply it, but name it in the PR. New option figures need alt text (step 4); figures that were replaced keep their old alt text, so look at them and correct it if the picture now shows something else. A problem missing from the new version blocks: ask the owner (or open an issue) whether to retire it.

## Solutions files (`<collection>_Solutions_v<n>.docx`)

These carry hints, the worded solution, the conventional solution and "Watch out" for each question of a worksheet already in the bank. The layout and mapping are in `docs/worksheet-contract.md`, "Solutions files".

1. **Order.** If the problems file arrived too, import it first (new, or `--update`), on the same branch, and make one PR for the pair: `import/<collection>-<problems version>`.
2. **Pre-flight:** `python3 -I tools/import_solutions.py worksheets/<file>.docx --check --report /tmp/sol-report.json`. Report:
   - **Blocking** items, as for worksheets. Reviewed or published solutions are never overwritten; solutions written by Claude or an expert need the owner's yes, then `--replace`.
   - **Answers that disagree with the key**, each with both answers. Never change the key: list them under **Needs your decision**.
   - **Written answers to compare** (`answers_to_compare` in the report): read each one against the key yourself and say whether it agrees.
   - **Problem text differs**: a short list; the reviewer decides whether the bank's wording or the solutions file's is better.
   - Counts: saved as `ai_solved` / `draft`, figures, formulas tidied.
3. **Import:** the same command with `--write`. Part of a file: `--only 0305` (a topic) or `--only 1-10` (question numbers).
4. **Alt text** for every new `-sol-<n>` figure, as in step 4 above. Solution figures may show the working and the answer; describe what is drawn.
5. **Check, build, look** as in step 5: open a question with a solution figure, answer it, and open the Hint, Word solution and Conventional solution links at phone width.
6. **PR body:** what was imported, the edits from a new problems version, answers to decide, problem-text differences, and that solutions are `ai_solved` until reviewed with the `solution-review` skill.

## CSV question lists

Use `tools/import_csv.py` instead of the DOCX importer. The collection ID is the file name without extension (e.g. `JeeProblems`), and the title says where the list came from.
- If old topic codes map to several new ones, choose the new code for each affected question from the `name` and `covers` fields in `bank/topics.json`. Write the choices to a JSON file `{"<ID>": "<code>"}` and pass it with `--codes`. List every choice in the PR body so the owner can correct it.
- If the Answer column is missing, the file cannot be imported. Say so (in an issue when unattended), and suggest adding the column.
- Alt text, checks, build and the pull request work as for worksheets.

## Unattended mode (GitHub Actions)

Used when the prompt says "Unattended mode": nobody is there to answer questions during the run, so:

1. **One collection at a time, one branch and one PR per collection.** A problems file and its solutions file (`03MSL_v3.docx` and `03MSL_Solutions_v8.docx`) belong together: problems first, then solutions, one PR. Before each collection: `git checkout main && git pull`, then `git checkout -b import/<collection>`, so problem IDs follow on from what is already merged. A solutions file alone is imported against the problems already on `main`; if its collection is not in the bank yet, open an issue asking for the problems file.
2. **New version or new worksheet?** If `bank/collections/<collection>.json` exists, use `--update` and the existing map. Otherwise, **topic map (DOCX):** run `python3 -I tools/make_map.py inbox/<file>.docx`. If any heading needs a decision, don't guess: open an issue (below) listing the headings and the chapter's codes, and skip the file.
3. **Pre-flight.** If anything is blocking, open an issue titled `Import blocked: <file>` listing every blocking item in plain words (question number and what to fix), then skip the file. The file stays in `inbox/`; uploading a fixed copy re-runs the import.
   ```bash
   gh issue create --title "Import blocked: <file>" --body-file <report.md>
   ```
4. **Import, alt text, check and build** exactly as above. Possible duplicates are not merged: list them in the PR body under **Needs your decision**, with both problem texts. The owner answers with an `@claude` comment.
   Answers in a solutions file that disagree with the key go under **Needs your decision** too.
5. **Move the processed files** out of the inbox in the same branch: `git mv inbox/<file>.docx worksheets/`. For a CSV, move it and its figures folder to `bank/sources/csv/`.
6. **Open the PR** with `gh pr create --base main --head import/<collection> --title "..." --body-file <body.md>`. `gh` is authenticated in Actions. In interactive sessions use the REST call above instead.
7. **Never merge**, and never push to `main`.

