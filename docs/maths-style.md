# Maths style guide

Every text field in the bank (stems, options, answers, hints, solutions) is Markdown with LaTeX maths. The checker (`tools/check_bank.js`) renders every formula with KaTeX 0.16.11 in strict mode, the same version the site uses. A formula that passes the checker will display on the site.

## Rules

| Rule | Write | Not |
|---|---|---|
| Inline and display maths | `$...$`; display maths `$$...$$` on its own line | `\(...\)`, `\[...\]` |
| Functions | `\sin\theta`, `\cos\omega t`, `\ln x`, `\log`, `\exp` | `sin\theta`, `Asin(...)` |
| Units, upright and spaced | `5\,\text{m/s}` or `5\unit{m/s}` | `5 m/s` inside maths |
| Multi-letter subscripts | `v_{\text{max}}`, `t_P` | `v_max`, `tP` |
| Vectors and unit vectors | `\vec{F}`, `\hat{i}` (or `\ihat`) | bold letters, `F→` |
| Powers of ten | `3 \times 10^{8}` | `3x10^8`, `3e8` |
| Degrees | `30^\circ` | `30°` inside maths |
| Quantities with values | inside maths: `$m = 2\,\text{kg}$` | `m = 2 kg` as plain text |
| Long equations | `$$\begin{aligned} ... \\ ... \end{aligned}$$`, about 40 characters a line | one long line (overflows on phones) |
| Symbols | LaTeX commands: `\rho`, `\sqrt{}`, `^{2}`, `\times`, `-`, `\to` | Unicode `ρ √ ² × − →` inside maths |
| Currency in text | `₹` | `$` (starts maths) |

## Macros

Defined once in `tools/katex-macros.json`, used by the checker and the site. Changing a macro restyles the whole bank.

| Macro | Means | Example |
|---|---|---|
| `\unit{...}` | thin space + upright unit | `9.8\unit{m/s^2}` |
| `\dd` | upright d for derivatives | `\frac{\dd x}{\dd t}` |
| `\ihat`, `\jhat`, `\khat` | unit vectors | `3\ihat + 4\jhat` |

## Figures

Refer to a figure by its asset ID, never by a file path: `![](asset:P000214-stem-1)`. The figure appears exactly where the reference sits. Its alt text (what a screen reader speaks, and what a blind re-solve reads) lives once, in the asset record in the problem file; the site builder inserts it.
