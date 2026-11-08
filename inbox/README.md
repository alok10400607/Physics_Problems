# Inbox

Upload a reviewed worksheet (`.docx`) or a question list (`.csv`) here, using GitHub's **Add file → Upload files**. Commit straight to `main`.

Within a few minutes:
- **If the file is clean:** a pull request appears with the imported problems, an import report and a preview. Check it and merge.
- **If something blocks the import:** an issue appears listing exactly what to fix. Fix the file and upload it again with the same name.

Questions that need your decision (a possible duplicate, a topic choice) appear as comments. Answer them with `@claude …`.

**Worksheets:** name the file `<chapter><code>_v<n>.docx`, e.g. `09ROT_v2.docx`. The first two digits pick the chapter. Rules: `docs/worksheet-contract.md`.

**CSV files:** they need the columns Question, Option A–D, Answer and Topic Code. Put figures in a folder named `<csv name>_figures/` next to the CSV. Rules: `docs/worksheet-contract.md`, CSV section.

Processed files are moved out of the inbox by the import's pull request.
