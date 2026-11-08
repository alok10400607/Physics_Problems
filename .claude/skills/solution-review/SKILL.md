---
name: solution-review
description: Run a conversational review session on solutions in this repository's bank. Fetches a subtopic, collection or problem IDs, publishes a private review page showing problems and all three solution levels as students will see them, applies the reviewer's edits and standing rules, re-checks, and saves approved work as a pull request. Use when the user says "review 1703", "review P000214", "show solutions for …", approves or corrects solutions, or says "save" during a review.
---

# Review session

The reviewer reads on the review page and gives instructions in the conversation. Nothing is saved to `main` until the reviewer says **save**, and saving opens a pull request.

## 1. Fetch

- Read `docs/solution-writing-guide.md` (standing rules included).
- Use the branch holding the batch (`solutions/<topic>`). If none exists, branch from `main`.
- Select the problems: a topic code, a collection section or IDs. Load each problem and solution file. If a problem has no solutions yet, offer to run solution-writer first.
- Set each solution's `status` to `in_review` (an uncommitted working change) so other sessions leave it alone.

## 2. Show

The main review page is the **workbench**. Reviewers revise with Claude on the page, compare versions, and send "Request a change" or "Approve" as a prefilled GitHub issue, which `@claude` applies (see CLAUDE.md, "Review requests from the review page"):

```bash
node tools/review_workbench.js --topic 1715 --out <scratchpad>/review-1715.html
```

Publish it with the Artifact tool and `capabilities: {"sample": {}}`, and republish it whenever that subtopic's solutions change on `main`. The owner shares the page with reviewers from its Share menu.

For a conversational session in chat, the read-only page below is still available:

```bash
node tools/review_page.js --out <scratchpad>/review.html <ids or --topic 1703> [--compare <git ref>]
```

Publish the file with the Artifact tool, keeping the same path for the whole session so the URL stays the same. In the conversation:
- give a 2- to 4-line summary: the count, and the flagged problems with their reasons (from `check.issues`, key disagreements, low difficulty confidence)
- don't paste solutions into the chat; the page shows them

After every round of edits, rebuild the page with `--compare <the batch's last commit>` and republish. Changed fields then show before and after.

## 3. Apply instructions

| The reviewer says | You do |
|---|---|
| "Approve 30–33" / "approve all except 34" | Mark those approved (keep a list in the session) |
| A change to one problem ("in 31, hint 2 gives too much away") | Edit that solution; re-check that the other levels still agree |
| A correction to the key or the data | A major change: edit the problem (version + 1), re-solve, update all levels, flag it on the page |
| A difficulty level ("31 is a 2") | Set `difficulty.expert` |
| Something that sounds general ("hints should never name the formula") | Ask: "Make this a standing rule?" If yes, append it, dated, under **Standing rules from review** in the guide, and apply it to the whole batch |
| A question about the physics | Answer it in the chat; change nothing unless asked |

After each edit:
- `node tools/check_bank.js` must show no errors
- the three levels must be consistent (same method, same numbers, same answer)

## 4. Save

When the reviewer says **save**:
- For approved problems:
  - solutions get `status: "reviewed"` and `reviewed_by: {"name": <reviewer>, "date": <today>, "notes": <short summary of instructions given>}`
  - the problem gets `status: "reviewed"`, and `difficulty.expert` defaults to the AI level if the reviewer accepted it without comment
- Problems not approved go back to `ai_solved` and keep their edits.
- Run `node tools/check_bank.js` and `node tools/build_site.js`, then commit with one line per problem changed.
- Push and open a pull request through the REST API (`gh api repos/<owner>/<repo>/pulls -X POST ...`). The body lists: approved, edited (with the instruction), still open, any standing rules added, and the attribution lines from the session's instructions.
- Tell the user the pull request is ready. Merge only when asked.

## Limits

- One subtopic per session. Long sessions drift; start a new session for the next subtopic, since everything needed is in the repository.
- Never change a key silently, never approve on the reviewer's behalf, and never write `difficulty.expert` without the reviewer's say-so or acceptance.
