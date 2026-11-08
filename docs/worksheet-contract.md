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
