# Worksheet contract

What a DOCX worksheet must contain to be imported into the bank. `tools/import_docx.py --check` tests every rule and reports before anything is written.

## Blocking: the import stops until these are fixed

1. **Sections.** Each subtopic starts with a Heading 2. Every heading must appear in the worksheet's topic map (`bank/imports/maps/<collection>.json`), which gives its TopicCode.
2. **Numbering.** Questions are numbered `1.`, `2.`, … with no gaps or repeats across the whole worksheet.
3. **Options.** MCQs have exactly four options written `(A) … (B) … (C) … (D) …`, on one line or several. An option may be a picture.
4. **Answer key.** A heading `Answer Key` followed by tables of `Q<n>  <answer>`. Every question has exactly one entry. MCQ answers are a single letter A–D (multi-correct: letters separated by commas).
5. **Equations.** Typed with Word's built-in equation editor. MathType objects and equations pasted as pictures cannot be read.
6. **Figures.** Every picture is inside the question, option or solution it belongs to, not floating elsewhere on the page.
7. **Formulas render.** Every equation converts to LaTeX that KaTeX can display.

## Warnings: the import continues, and these are flagged for review

- Questions with no source tag (`[JEE Main 2019, 10 Jan, Shift 2]`, `[AIEEE 2007]`). They are imported with rights `unverified`.
- Questions with no level tag (`[L2]`).
- Plain-letter `sin`, `cos`, `tan`, `ln`, `log` inside equations. These are repaired automatically and listed.
- Figures narrower than 600 pixels, which will look blurred on phones.
- Possible duplicates of problems already in the bank, or within the worksheet.

## Optional sections

- `Hints & Solutions`, with entries such as `**Q13** *Hint*` or `**Q13** *Think further*` followed by the text. These become draft solutions.

## Tags inside a question

At the start of a question, in square brackets, in any order:

- Level: `[L1]` to `[L6]`
- Source: `[JEE Main 2014, 12 Apr (Online)]`, `[JEE Main 2015 (Offline)]`, `[JEE Main 2019, 10 Jan, Shift 2]`, `[AIEEE 2007]`, `[IIT-JEE 2011]`, `[NEET 2023]`
- After the first import, the regenerated worksheet carries each question's ID: `[P000214]`. Re-importing uses it to update the right problem.

## A new version of a worksheet already in the bank

A file such as `03MSL_v3.docx`, when `03MSL` was imported from `03MSL_v2.docx`, updates the problems in place (`import_docx.py … --update`):
- Each question is matched to the problem imported from the same question number, or by its `[P000123]` tag if it has one. The question text must still agree (similarity 0.6 or more); otherwise the import stops and asks for an ID tag.
- Only problems that changed are rewritten, with their version raised by one. The stem, options, answer, question type and figures are compared; whitespace alone is not a change. Changed answers are reported as major.
- New question numbers become new problems. A problem missing from the new version stops the import until the owner decides whether to retire it.
- Hints & Solutions in the new version are ignored for problems already in the bank; solutions come from the solutions file.

## Solutions files

Solutions come in their own file, named `<collection>_Solutions_v<n>.docx` (e.g. `03MSL_Solutions_v8.docx`), written with the `jee-worksheet-solutions` skill and reviewed before upload. `tools/import_solutions.py --check` tests it.

The file is already reviewed, so there is no review session afterwards: a complete solution whose answer agrees with the key is saved as `reviewed` (and its problem too), with `reviewed_by` naming the file. A solution with a part missing is saved as `draft`; one whose answer disagrees with the key is saved as `ai_solved` and listed for the owner. `--unreviewed` saves everything as `ai_solved`, for a file that has not been reviewed.

    # <subtopic name>
    ## Q<n> · <short title>
    ID <id> · Code <topic code> · Worksheet <collection>_v<k> Q<n>
    ### Problem / Hint / Think it through / Another way: … / No-pen route / Why the other options are there / Worked solution / Answer / Watch out

| Section | Goes to |
|---|---|
| Problem | not stored; compared with the bank (a small difference is a warning, a large one stops the import) |
| Hint | `hints` |
| Think it through | `worded` |
| Another way: …, No-pen route | appended to `worded`, under their own title in bold |
| Why the other options are there | `distractors`, when each sentence names one option; otherwise appended to `worded` |
| Worked solution | `conventional`; its figures become `<problem>-sol-<n>` |
| Answer | checked against the answer key; a disagreement is flagged for the owner, never fixed by changing the key |
| Watch out | `mistakes`, one per bullet. The closing `Notes: Sec. …` line is reported, not stored |

**Blocking:** a question that matches no problem (or the wrong one), a formula that does not render, a missing figure, and a problem whose solutions are already reviewed or published (those are never overwritten), or written by Claude or an expert (overwritten only with `--replace`).

**Warnings:** problem text that differs from the bank, missing sections (saved as `draft`), answers that disagree with the key (saved as `ai_solved`, not reviewed), topic codes that differ, problems of the collection with no solution in the file.

Import the problems file first when both arrive together, so the solutions are matched against the latest problem text.

## CSV question lists

What a `.csv` must contain (checked by `tools/import_csv.py --check`).

**Blocking:**
1. **Columns.** Question, Option A, Option B, Option C, Option D, Answer and Topic Code are present (header names, any order).
2. **Answers.** Every row has an answer: a letter A–D, or several letters (AD) for multi-correct questions.
3. **Topic codes.** A TopicCode_v2 code (e.g. 0211), or an old code that maps to exactly one new code. Old codes that split into several new codes need a choice per question (`--codes`).
4. **Figures.** Every image named in Figure or in an option column exists next to the CSV or in `<csv name>_figures/` (or `figures/`).
5. **Distinct options.** No row has two identical options.

**Handled automatically:**
- A year typed at the end of the question, e.g. "(2017)", is moved into the source.
- Exact duplicate rows are merged, keeping the copy that has a figure.

**Warnings:** maths typed as plain text, small figures, and possible duplicates of problems already in the bank. Possible duplicates are not imported until you decide.

**Optional columns:** ID (the original row number), Exam (e.g. JEE Main), Year, Source (free text).
