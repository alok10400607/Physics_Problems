# Solution-writing guide

Prompt version: **sw-v1**. Every solution records the version it was written under (`generated_by.prompt_version`). When this guide changes, increase the version.

## The three levels

| Level | Purpose | Form | Length |
|---|---|---|---|
| Hints | Get a stuck student moving without solving it for them | 1 to 3, each a step further than the last | Each at most 2 sentences |
| Explained in words (`worded`) | Show the physics reasoning: what applies, why, and what it implies | Prose; short relations allowed, no long algebra | About 60 to 150 words |
| Full solution (`conventional`) | The complete working a student would write in an exam | Steps with equations, substitution with units, result | As long as needed; one idea per paragraph |

### Hints
- Hint 1 points to the governing idea or the quantity to look at.
- Hint 2 sets up the key relation.
- A third hint is optional, for multi-step problems only.
- Never state the final value or the option letter, and never eliminate options by letter.

### Explained in words
- Start from the physical situation, not from a formula.
- Say why the principle applies, then what follows.
- Where it helps, give a sense of scale ("about 71% of the way to the extreme").
- End with the conclusion in words and `Answer: (C).`

### Full solution
- Paragraphs in this order: known quantities, principle, equations, substitution with units, result.
- Put key equations on their own line as `$$...$$`.
- End with `**Answer:** (C) <value>` for MCQs, or `**Answer:** <value with unit>`.
- For comparison problems (several options to test), use one line per option, written as a list (`- ...`).

### Common mistakes (`mistakes`)
- One or two specific errors, each tied to the option it produces where possible.
- Never invent a mistake to fill the field.

### Distractors (`distractors`)
- For each wrong option, the error that produces it, in a few words.
- Leave an option out if no plausible error produces it.

## Self-check (required)

1. Solve the problem from the stem, options and figure alt text **before reading the answer key**. Record the answer in `check.solved_answer`.
2. Compare with the key and set `check.agrees_with_key`.
3. On disagreement, do not change the key. Write the reason in `check.issues`, and present both answers at review.
4. Blind re-solve: when the user has allowed it, a separate agent solves from the stem alone, and its answer goes in `check.resolve_answer`. Otherwise leave it `null`.
5. If the key was seen before solving, say so in `check.issues`.

## Tagging, done with the solutions

- **Difficulty** (1 to 6): score four dimensions from 1 to 3 (concepts, steps, maths, insight), then propose a level against the rubric in the plan. Give a one-line reason and a confidence from 0 to 1. Fill `difficulty.ai`, `ai_scores`, `ai_reason`, `ai_confidence`. Never touch `difficulty.expert`.
- **Time estimate:** typical seconds for a prepared student.
- **Exams:** add NEET or JEE Main relevance where the topic is in that syllabus.
- **Concepts:** use only slugs from `bank/concepts.json`. Put new ones in `bank/proposals/concepts.json` for approval.

## Cleaning the problem text

When maths in a stem or option is typed as plain text, move it into equations following `docs/maths-style.md`:
- Change formatting only, never wording. This is a minor change: the problem version increases by 1.
- Where the plain text is ambiguous (e.g. `A/2√2`), choose the reading that matches the original exam and record it in `check.issues` for review.

## Style

- Plain, direct sentences, avoiding words like "clearly" and "obviously".
- Use the symbols the problem uses.
- SI units throughout. Use the collection's stated constants (e.g. $g = 10\,\text{m/s}^2$).
- Formatting: paragraphs, `**bold**`, lists with `- `, and maths. No tables or headings inside a solution.

## Standing rules from review

Rules the reviewer has made permanent. Each one is dated and applies to every solution written after that date.

_(none yet)_
