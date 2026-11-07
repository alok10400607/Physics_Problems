# Physics_Problems

Physics practice resources for JEE and NEET students: interactive subtopic tests built from reviewed worksheets.

## Layout

| Folder | What it holds |
|---|---|
| `worksheets/` | Reviewed worksheets (`.docx`). These are the master copies: edit these, never the generated data. |
| `site/` | The website. This is the folder the host publishes. |
| `site/data/` | One `<chapter>.json` per chapter plus its figures, generated from the worksheets. |
| `pipeline/` | The converter (`parse_worksheet.py`) and checker (`validate.js`). |

## Adding or updating a chapter

1. Put the reviewed worksheet in `worksheets/`, e.g. `worksheets/17SHM_v6.docx`.
2. Run:

   ```bash
   pipeline/build.sh worksheets/17SHM_v6.docx 17SHM "Oscillations: Simple Harmonic Motion"
   ```

3. The build stops with a list of problems if anything is wrong: a missing answer, an option missing, a formula that won't display, a missing figure.

Requirements: `pandoc`, Python 3 and Node.js.

## What the converter expects from a worksheet

- Each subtopic starts with a Heading 2; questions are numbered `1.`, `2.`, …
- Options are written `(A) … (B) … (C) … (D) …`, on one line or several; an option may be an image.
- Optional tags at the start of a question: `[L2]` / `[L3]` for level, `[JEE Main 2019, 9 Jan, Shift 1]` for source.
- An `Answer Key` heading with `Q1  A` style tables, then a `Hints & Solutions` heading with `**Q13** *Hint*` style entries.
- Equations typed with Word's built-in equation editor. Type `sin`, `cos` and `tan` as functions; the converter repairs the plain-letter cases but reports them.
