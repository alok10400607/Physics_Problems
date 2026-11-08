# Batch 1 import notes (03MSL, 04MIP, 05NLM, 07CM1, 08WPE)

## Needs fixing in the source

| Problem | Worksheet | Issue |
|---|---|---|
| P000168 | 03MSL Q84 | The question asks students to pick the incorrect graph out of (A)–(D), but the worksheet contains only one graph. The four option graphs are missing. |
| P000252 | 04MIP Q72 | The question asks which graph (A)–(D) shows the relative position, but the worksheet contains only one graph. The four option graphs are missing. |

Both are imported with options reading "Graph (A) in the figure" and so on. They should not be published until the four graphs are added (one picture per option).

## Repaired automatically during import

- Option labels without a space or without "(" (e.g. "(B)$\sqrt{3/2}$", "B) 1.41 s")
- Answer letters typed inside equations ("$A$")
- Unicode symbols inside equations (µ, ¼, ¾, π, θ, ×, −, °) converted to LaTeX
- Four figures with large blank margins trimmed (P000164, P000252, P000329, P000369)
- Five EMF drawings converted to PNG

## Left for solution writing

Maths typed as plain text in 133 questions, missing source tags (339) and level tags (384), and small figures marked `needs_redraw`.
