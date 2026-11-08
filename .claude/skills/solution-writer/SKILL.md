---
name: solution-writer
description: Write three-level solutions (hints, explanation in words, full solution) for problems in this repository's bank, a subtopic or a list of IDs at a time. Solves each problem before reading the key, tags difficulty, time, exams and concepts, cleans plain-text maths in the problem, checks everything and leaves the batch ready for a review session. Use when the user asks to solve, write solutions for, or prepare a topic code, collection or problem IDs for review.
---

# Write solutions for a batch

Read `docs/solution-writing-guide.md` and `docs/maths-style.md` in full first. Their **Standing rules from review** override anything here.

## 1. Pick the batch

- By topic code, collection section or IDs. Keep a batch to one subtopic (about 5 to 25 problems).
- Skip problems whose solutions are already `reviewed` or `published`, unless the user asks.
- Work on a branch: `git checkout main && git pull -q origin main && git checkout -b solutions/<topic>`.

## 2. Solve before reading the key

Print each problem's stem, options and figure alt text **without the answer**:

```bash
python3 -c "import json,sys; p=json.load(open(sys.argv[1])); print(p['stem']); [print(k, v) for k, v in p.get('options', {}).items()]; [print('fig:', a['alt']) for a in p['assets']]" bank/problems/P000/P000030.json
```

If a figure's alt text isn't enough to solve the problem, look at the figure itself. Write down your answer for every problem in the batch. Only then compare with `answer` in each file.

## 3. Write

For each problem, write `bank/solutions/<shard>/<id>.json` (schema `bank/schema/solution.schema.json`):
- `status: "ai_solved"`, `problem_version` = the problem's version after any cleanup
- `generated_by: {"author": "llm", "model": "<model id>", "prompt_version": "<guide version>", "date": "<today>"}`
- keep a worksheet `extension` (think further) if present

In the problem file:
- set `difficulty.ai`, `ai_scores`, `ai_reason`, `ai_confidence`, `time_estimate_s` and `exams`
- clean plain-text maths, as a minor change (version + 1, `updated` = today)
- set `status: "ai_solved"`

Propose new concept tags in `bank/proposals/concepts.json` as `{"slug", "name", "topic_code", "problems": [...]}`.

## 4. Check

```bash
node tools/check_bank.js     # no errors
node tools/build_site.js
```

Note any disagreement with the key, ambiguity or doubt in `check.issues`. These become the review page's flags.

## 5. Hand over

Commit to the branch with a message listing the problems and any flags. Don't open a pull request yet: the review session saves the final version and opens it. Tell the user the batch is ready, naming the problems that carry flags, and offer to start the review.
