# Physics_Problems

Physics practice resources for JEE and NEET students. Everything is built from one problem bank.

## Layout

| Folder | What it holds |
|---|---|
| `bank/problems/P000/P000001.json` | One file per problem. The bank is the master copy. |
| `bank/solutions/P000/P000001.json` | Hints, worded and conventional solutions, kept apart from problems so they can sit behind a login later |
| `bank/assets/P000/` | Figures, named `<problem>-stem-<n>`, `<problem>-opt-<key>`, `<problem>-sol-<n>` |
| `bank/collections/` | Worksheets and sets: ordered lists of problem IDs |
| `bank/topics.json`, `bank/concepts.json` | Topic codes and the approved concept tags |
| `bank/registry.json` | The next free problem ID. IDs are never reused. |
| `bank/imports/` | A log of every import, plus the topic map for each worksheet (`maps/`) |
| `bank/schema/` | JSON Schemas every record must pass |
| `docs/` | Worksheet contract, maths style guide, solution-writing guide |
| `tools/` | Importer, checker, site builder |
| `site/` | The website; `site/data/` is generated, never edited by hand |
| `worksheets/` | Original DOCX files, kept for reference |

## Common tasks

```bash
cd tools && npm install && cd ..                       # once

# import a worksheet: check first, then write
python3 -I tools/import_docx.py worksheets/17SHM_v6.docx bank/imports/maps/17SHM.json --check
python3 -I tools/import_docx.py worksheets/17SHM_v6.docx bank/imports/maps/17SHM.json --write

node tools/check_bank.js      # must show "No errors" before any merge
node tools/build_site.js      # regenerates site/data from the bank
```

Every change to the bank arrives as a pull request. Cloudflare builds a private preview of each branch, and merging to `main` updates the review site.

Requirements: `pandoc`, Python 3 with Pillow, Node.js.
