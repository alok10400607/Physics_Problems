# Inbox

Upload a reviewed worksheet (`.docx`) or a question list (`.csv`) here, using GitHub's **Add file → Upload files**. Commit straight to `main`.

Within a few minutes:
- **If the file is clean:** a pull request appears with the imported problems, an import report and a preview. Check it and merge.
- **If something blocks the import:** an issue appears listing exactly what to fix. Fix the file and upload it again with the same name.

Questions that need your decision (a possible duplicate, a topic choice) appear as comments. Answer them with `@claude …`.

**Worksheets:** name the file `<chapter><code>_v<n>.docx`, e.g. `09ROT_v2.docx`. The first two digits pick the chapter. Rules: `docs/worksheet-contract.md`.

**A new version of a worksheet** already imported (e.g. `03MSL_v3.docx` after `03MSL_v2.docx`) updates the problems in place, keeping their IDs. The pull request lists every problem that changed.

**Solutions:** upload `<collection>_Solutions_v<n>.docx`, e.g. `03MSL_Solutions_v8.docx`, written with the jee-worksheet-solutions skill. Upload it together with the problems file (same commit) or on its own. Both files of a pair go into one pull request. Any answer in the solutions that disagrees with the answer key is listed for your decision; the key is never changed. Rules: `docs/worksheet-contract.md`, "Solutions files".

**CSV files:** they need the columns Question, Option A–D, Answer and Topic Code. Put figures in a folder named `<csv name>_figures/` next to the CSV. Rules: `docs/worksheet-contract.md`, CSV section.

Processed files are moved out of the inbox by the import's pull request.
