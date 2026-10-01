# Review of 06a against the reveal.js notebook standard

**Date:** 2026-09-30
**Notebook:** `06a_intro_presentation.ipynb`
**Standard:** [`docs/agent_references/notebook_reveal_standard.md`](../agent_references/notebook_reveal_standard.md) (not modified)
**Purpose:** to record what was changed in 06a, what was left as is, and where the standard is silent or gives
guidance that did not work. It supports the discussion about updating the standard.

## Summary

| | Before | After |
|---|---|---|
| Slides | 26 | 49 |
| Slides taller than 800 px, as presented | **22** | **0** (tallest is 783 px) |
| Slides taller than 800 px, with the MathJax fix alone | 20 | — |
| Static figures shown scaled down (wider than the slide) | 17 | 0 |
| Findings from the rule checker | 19 | 1 (a deliberate exception, see B1) |
| Executes from a fresh kernel | **no**: the import and helper cells were missing | yes, in 44 s, with no errors or warnings |
| Notebook size | 9.1 MB | 8.4 MB |

All 57 printed result lines in the original appear verbatim after re-execution. No computation or number changed.

The deck overflowed for four reasons, in order of impact:

1. **Too much per slide.** Most sections put a full argument (derivation, table, bullets) and a figure into
   one `##` section, and nbconvert makes each section one slide.
2. **Figures wider than the slide.** They were authored 12.4–14 in wide, so the slide scaled them to 85–99%.
3. **A MathJax setting in nbconvert's template.** It breaks any table that contains math (C1). The standard
   does not know about it.
4. **A derived notebook with missing cells.** 06a was generated from 06 by `make_06a_slides.py`, which dropped
   the setup cells.

## Method

- **Build:** the deck was built with `make_slides.py`, unchanged.
- **Measurement:** each slide was measured in headless Chrome by moving through the deck with reveal's own
  navigation. This fires the MathJax re-render that arrow-key navigation triggers.
  - Loading a slide directly by URL (`#/N`) gives wrong heights. Math on a hidden slide is typeset at zero
    width, so it breaks at every operator.
  - Each slide's content height is compared with 800 px.
  - Every slide was also screenshotted and inspected.
- **Execution:** the notebook was re-executed from a fresh kernel after every change.
- **The changes** were applied by a script that turns the original 06a into the new one. That kept every
  change explicit and repeatable. The script, the measurement tool and the checker are in the session
  scratchpad, not in the repo. See D5.

---

## A. Changes made to 06a

**Structure.** Every change restructures cells, sizes figures or moves content between the slide and the
speaker notes. No prose was rewritten, except the headings listed in the appendix and two short deletions
noted below.

| Where | Rules | Change |
|---|---|---|
| Top of notebook | R2.9, R8.4, R5.1 | Restored 06's import/rcParams cell and plotting-helper cell as `skip` cells, which made 06a executable. rcParams: `font.size` 11 → 12, titles unchanged at 12 (see C2), and `bbox_inches=None`. |
| Deck CSS cell | (kept, see B1) | Added a MathJax config block that turns off automatic line-breaking (C1). |
| 1.1 | R6.3, R2.11 | Removed the raw-HTML spacer `<div>`. Restored 06's "said aloud" cell and the two bullets that `make_06a_slides.py` had dropped, as speaker notes. |
| 1.2, 1.5, 1.8, 2.1 | R2.9 | Moved invariant and residual checks into their own `skip` cells. They still run and still show in the notebook. |
| 1.3, 1.8 | R4.5, R4.2 | Put the definitions and the annotated A/D/L and W/D/L matrix figures on separate slides, with the figures 12 × 3.9 in, so the numbers in the cells are legible (C3). |
| 1.3 | R2.2 | The `### L is a difference operator` block became its own `##` slide. |
| 1.4 | R4.5, R4.2 | Put the definition and the example on separate slides. The node-value labels got a white backing, because they crossed edges (C12). |
| 1.6 | R4.5, R2.7, R2.11 | Split the 12.4 × 8.2 in six-panel figure (814 px tall on its own) into a spectrum slide and a five-mode slide (a 2 × 3 grid). Moved "Worth saying out loud: …" into speaker notes. |
| 1.6, 1.7, 1.9 | R2.8, R2.3 | Replaced the three generated "(cont.)" titles with descriptive `##` headings. |
| 1.7 | R2.9 | The cell that builds W is now `skip`. Its output was checks plus an edge table whose numbers the next slide restates in prose (B6). |
| 1.9 | R4.5 | Figure 6.6 → 5.25 in tall. The printed numbers and the bullets that cite them moved to a second slide. |
| 1.10 | R4.5 | Put the operator table and the comparison figure on separate slides. |
| Part 2 and Part 3 | R2.2 | `# Part N` was in the same cell as `## N.1`. Each part now has its own divider slide. |
| 2.1 | R4.5 | The 1961 px slide became four: the derivation, the mapping table, the figure (14 × 7.8 → 12 × 5.8 in), and the bullets. |
| 2.2 | R2.7, R4.5 | The animation and the static traces came from one cell, under a table and four bullets. They became three slides: the animation, the column table, and the traces with the bullets. |
| 3.1–3.6 | R4.5, R4.2 | Each argument and its figure became two slides, and 3.4's text alone (791 px) became two. All figures 14 → 12 in wide. |
| 3.2, 3.4 | R5.3 | Map-panel titles broken onto three lines and the maps given more width. At 12 in the titles overlapped. |
| 3.2, 3.4, 3.5, 3.6 | R5.5 | Wrapped printed lines over ~95 characters, and one axis label that ran past the figure edge (C4, C5). |
| Part 3 conclusions | R4.5 | The limitations paragraph moved to its own slide. Its bold lead-in "**What this does not show.**" was removed, because the new heading says the same thing. |
| All figures | R4.2, R5.3 | Width ≤ 12 in. Explicit font sizes raised: 6.5 → 8, 8 → 10, 9 → 11, 10 → 11, 11 → 12. There are three exceptions (C2). |

The deck in the repo, `06a_intro_presentation.slides.html`, was rebuilt from the new notebook.

## B. Deviations left in place, and why

**B1. The deck CSS cell, now with a MathJax `<script>` as well (against R3.4, R6.3 and R7.3).**
The standard says deck styling belongs in the build. But `make_slides.py` does not carry these rules, and
removing them would make the presentation worse:

- tables with math become unreadable
- narrow figures are left-aligned
- printed output is set in a different size from the prose

I extended the one existing exception rather than add a second. **Fix:** move the CSS and the MathJax override
into `make_slides.py`, then delete the cell.

**B2. 06a is still a derived notebook (against the principle of "no derived copy").**
Re-running `make_06a_slides.py` will overwrite every change in this report and regenerate the original 06a
from 06. That also makes the original recoverable. I did not change 06 or the script. **Decision needed:** D1.

> **Resolved (2026-09-30):** `make_06a_slides.py` has been deleted. 06a is now its own presentation and is
> maintained directly, with no connection to 06.

**B3. The animation still uses a JavaScript player (`to_jshtml`), against R5.9's preference for native video.**
ffmpeg is installed, so `to_html5_video()` would work. I kept the player for three reasons:

- It gives the presenter frame-step and speed controls.
- It renders in VS Code notebooks. I believe VS Code's notebook view cannot play H.264 video, because its
  Electron build ships without that codec. I did not verify this here.
- It already worked.

The player has two costs. It is 5.6 MB of the notebook. And it loads its button icons from
`maxcdn.bootstrapcdn.com`, which breaks R8.7: offline, the buttons have no icons.

**B4. Some text is below R5.3's 12 pt minimum:**

- the two-decimal W/D/L matrix numbers on the 1.8 figure slide: 7 pt
- the W numbers on the 1.7 figure slide: 8 pt
- the five three-line mode titles in the 2.1 figure: 10 pt

Each collides with its neighbours at any larger size (C2, C3).

**B5. Text density.** Several Part 3 argument slides carry 600–715 px of prose. They fit, but they are heavy
for a meeting. Cutting prose is for the writing style guide, so I left it.

**B6. A skipped table.** The edge table under 1.7 (distance → weight for five edges) was removed from the
deck by making its cell `skip`. That is a content judgment: the kernel plot, the W matrix and the prose on the
next slide carry the same numbers.

**B7. Not evaluated.** Whether the VS Code preview settings in R3.2 give the promised fidelity. VS Code
could not be run here.

---

## C. Where the standard is silent or its guidance did not work

These are the proposals for discussion. Each item gives what happened in 06a, what the standard says, what I
did, and a proposed change.

### C1. nbconvert's MathJax configuration breaks tables that contain math

- **Seen:** tables with inline math collapsed into over-tall columns, with the math broken at every operator.
  This happened on 1.5, 1.10 and the Part 1 summary. Turning MathJax's automatic line-breaking off changed the
  slide heights as follows:
  - 1.5: 1136 → 677 px
  - Part 1 summary: 1065 → 579 px
  - 1.10: 1399 → 1051 px
- **Cause:** nbconvert's template sets `CommonHTML: {linebreaks: {automatic: true}}`. MathJax then breaks
  math to fit its container, and a table cell's width is not settled at that point.
  - This happens even with arrow-key navigation, which re-renders each slide.
  - It happens with or without 06a's CSS cell.
- **Standard:** says nothing about it, and R6.9 implies tables with math are fine.
- **Did:** turned line-breaking off in the kept CSS cell (B1).
- **Propose:**
  - Make it a build requirement: `make_slides.py` injects `MathJax.Hub.Config({CommonHTML: {linebreaks:
    {automatic: false}}})`.
  - Add a line to §3, listing it as a known difference between notebook and deck until the build carries
    the fix.
  - Note that every math-heavy slide measures taller until it is fixed.

### C2. R5.1's `font.size: 14` conflicts with R4.2's 12 in width

- **Seen:** at 14 pt, three-panel figures with two-line titles overlapped, clipped titles at the figure edge,
  and truncated axis labels. This happened on 3.2, 3.3, 3.4 and 3.6, and in the 2.1 and 2.2 panel titles.
- **Why the original "fit":** its 14 in figures were displayed at 85%. The *effective* sizes on the slide
  were already small:

  | Written size | Effective size on the slide |
  |---|---|
  | 11 pt | ~9.4 pt |
  | 9 pt labels | ~7.6 pt |
  | 6.5 pt matrix numbers | ~5.5 pt |

- **Did:**
  - Set the base to 12 pt (R5.3's minimum), with titles at 12 pt.
  - Raised the explicit sizes by 1–2 pt.
  - Reverted the mode titles in 2.1 to 10 pt.
  - Broke the 3.2 and 3.4 titles onto more lines.

  With these changes nothing collides, but some figures needed layout work (width ratios, title breaks).
- **Propose:**
  - Make R5.1's example `font.size: 12`.
  - Keep R5.3's 12 pt minimum for tick labels, axis labels and legends.
  - Explicitly exempt dense annotations: matrix cell values, and multi-line panel titles above 3 or more
    panels.
  - Add a rule of thumb: with 3 panels per 12 in row, keep each title line to about 35 characters at 12 pt.

### C3. Annotated matrix heatmaps need their own space

- **Seen:** three 10 × 10 heatmaps side by side cap each panel at about 3.2 in, which is about 32 px per
  cell.
  - Two-decimal signed values ("-0.65") need about 31 px at 8 pt, so they collide.
  - The standard's slide-unit pattern (lead text, figure, takeaway) left these figures only 2.7–2.8 in of
    height, which is worse.
- **Standard:** does not address them.
- **Did:** gave each matrix figure its own slide (the numbers became legible on 1.3). On 1.8 I used 7 pt.
- **Propose:** a rule for annotated matrices:
  - at most 3 per 12 in row for integer values
  - at most 2 per row for values with two decimals
  - or annotate only what the talk refers to

### C4. `bbox_inches=None` (R5.1) clips anything outside the figure

- **Seen:** the RMSE axis label, "test RMSE at hidden stations [°C] (lower is better)", ran past the figure
  edge and was cut off.
  - Under the default `'tight'` setting, the saved image had silently grown to include it.
  - Constrained layout does not stop a long x-label from running past the figure edge.
- **Did:** wrapped the label onto two lines.
- **Propose:** add to R5.1: "With an exact bbox, any text past the figure edge is cut off. Check the edges,
  and wrap long labels."

### C5. The standard gives no width limit for printed output

- **Seen:** printed lines over about 95 characters wrap on the slide. The limit comes from 20 px monospace in
  a 1237 px column. It affected 3.4, 3.5 and 3.6.
- **Propose:** in R5.5, "keep printed lines to 90 characters or fewer".

### C6. The height budget (R4.4) is missing common elements

The per-element costs held up well. For example, "heading + figure ≤ 5.9 in" predicted 1.6, 1.9 and the
figure slides in Part 3 to within about 20 px. Rows to add:

- **JavaScript animation player:** its slider and buttons add about 140 px below the frame. The player also
  always draws its frames at **95%** of their width, so R4.2's 1:1 display cannot be met with `to_jshtml`.
- **A safety margin:** aim for 780 px or less. Several final slides land at 775–783 px, which is fine, but
  font fallback or a different browser could push them over.
- **Table rows that contain display-size math**, which are taller than 38 px. This depends on C1 being fixed.

### C7. The standard assumes one notebook serves both reading and presenting

- **Seen:** 06 is the reading notebook and 06a is its presentation copy.
  - Some content in 06 is deliberately reading-only. `make_06a_slides.py` removes it with `SKIP` and
    `DROP_LINES`.
  - The standard's answer is `skip` and `notes` cells, which worked here: the dropped material is now notes.
  - But the standard says nothing about migrating an existing notebook pair, or when two notebooks are
    justified.
- **Propose:** state the policy, one notebook or a documented pair (D1). Add a migration note: script-derived
  decks should be converted once, then maintained directly.
- **Resolved for 06a:** it was converted once, the script is gone, and 06a is maintained on its own. The
  general policy for the standard is still open.

### C8. The slide-unit pattern (R2.6) has no form for an argument followed by its evidence

- **Seen:** most Part 3 sections are a multi-paragraph argument followed by a figure. R2.6's lead-in of
  "one to three lines" does not describe them, so the budget forced a split in every case.
- **Propose:** add a second pattern, the **argument slide**. It is followed by an **evidence slide** with its
  own heading (the figure, plus any printed numbers). State that this doubling of the slide count is
  expected. It is the main reason 06a went from 26 to 49 slides.

### C9. Splitting slides requires writing headings, and the standard does not say who owns that

I wrote or changed 23 headings; they are listed in the appendix. R2.8 requires descriptive headings, but
choosing their words is arguably the writing guide's job.

- **Propose:** the formatting pass writes plain, descriptive headings, and the writing pass may revise them.
  Record that split.

### C10. R2.9 does not distinguish verification from demonstration

- **Seen:** some printed "checks" are teaching content. For example, "lambda_1 = 0 : True (one zero
  eigenvalue = one connected component)" is a check, but it teaches something, so I kept it on 1.5 and moved
  the residual and orthonormality checks to `skip`.
- **Propose:**
  - If the audience learns something from a check, it may stay.
  - Numerical-hygiene checks (residuals, symmetry, dtype) go to `skip`.

### C11. R5.9's preference order for animations may be wrong for this toolchain

- **The trade-off:**
  - Native video is smaller and self-contained, but may not play in VS Code notebooks, and it loses the
    player's step controls.
  - The JavaScript player works in VS Code but depends on an external icon CDN.
- **Propose:**
  1. Test `to_html5_video()` in the notebook frontends and browsers you use.
  2. Choose a default based on the result.
  3. Record it. If the JavaScript player stays, add "bundle or replace its icon stylesheet" to R8.7.

### C12. Nothing in the standard covers annotation legibility inside drawings

- **Seen:** on 1.4, the value labels under each node crossed edges and neighbouring nodes. They collided in
  the original too.
- **Did:** gave the labels a white backing.
- **Propose:** a general line under §5: "check that labels, annotations and legends are legible at slide
  size, and give labels over dense drawings a backing".

### C13. The verification step (§9) can't be done by eye at 49 slides, and one obvious automated shortcut gives wrong numbers

- **Seen:** loading a slide by URL measures math at zero width (see Method). A reliable check has to navigate
  the way a presenter does.
- **Propose:** add the measurement tool and the checker to the repo as build tooling, and have §9 point to
  them (D5).

### C14. Two-column slides (text left, figure right) are ruled out by the standard, but asked for

- **Seen:** at your request after the review, 1.3 and 1.4 each went back to a single slide. The definitions
  are in the left column and the figure is in the right, restacked vertically: the three heatmaps in 1.3,
  and the two graphs in 1.4. This removed the two separate figure slides, so the deck has 47 slides, not
  49.
- **Standard:** R7.2 says to build side-by-side layouts as subplots within one figure, and R3.4 and R7.3
  say to keep CSS out of the notebook. Neither allows text beside a figure, and no subplot arrangement can
  put markdown next to a plot.
- **Did:**
  - Marked each slide with `"data": {"layout": "two-column"}` in its `slideshow` metadata. This is native
    nbconvert behaviour, so no markup went into the slide text.
  - Added three float rules to the deck CSS cell. Markdown cells go in the left column (55%), and code
    output goes in the right (43%).
  - Floats rather than grid, because reveal sets `display` inline on every slide, and floats survive PDF
    export.
- **Constraints found:**
  - The heading has to share the left column. A float cannot rise above an earlier one, so a full-width
    heading pushes the figure down by its own height. For 1.3 that cost about 100 px, and the matrices
    shrank to about 135 px.
  - Figures must be authored for the column: at most about 5 in wide at dpi 100.
  - Text that refers to positions must follow the layout. In 1.4, "left/right one" became "top/bottom
    one".
  - The notebook cannot preview this layout, so the cells still read top to bottom.
  - In 1.3 each stacked matrix is about 160 px square. The L numbers are at the limit of projector
    legibility.
- **Propose:** allow one named layout, `two-column`, as a build feature:
  - The CSS lives in `make_slides.py`, and the only thing in the notebook is the metadata.
  - Document the constraints above in §4 (a column budget) and §7 (the metadata row).
- **Reverted (2026-09-30):** you preferred full-width horizontal figures. The two-column slide layout and its
  CSS were removed, and replaced by C15.

### C15. Side-by-side markdown, inside an otherwise single-column slide

- **Seen:** 1.3 and 1.4 each needed their definitions and figure on one slide. With the figure full width
  beneath them, the definitions had to get shorter.
- **Did:**
  - Each slide is: a heading-only cell (`slide`), then **two markdown cells tagged `side-by-side`**, which
    share one row at half the width each, then the full-width figure.
    - 1.3: the equations on the left, the property table on the right.
    - 1.4: the definition on the left, the examples on the right.
  - In 1.3 the math was also compacted. The sum is written inline-size (`\textstyle`), and the boxed
    $L = D - A$ now sits beside the $L_{ij}$ cases.
  - The 1.3 figure went back to 12 × 3.6 in, its most legible size so far. 1.4's figure is 12 × 2.4 in.
  - Slide heights: 1.3 is 775 px and 1.4 is 782 px. No other slide changed height.
- **Mechanism:**
  - nbconvert writes each cell tag as a class, `celltag_<tag>`, but on the cell's *inner*
    rendered-markdown div. So the CSS uses `:has()` to float the cell itself. `:has()` is supported in
    Chrome/Edge 105+, Safari 15.4+ and Firefox 121+.
  - A general rule clears the floats at the end of every slide.
  - Tags are standard nbformat metadata, editable in JupyterLab and in VS Code.
- **Why two cells, not one:** one cell set in two columns (CSS `column-count`) lets the browser choose the
  break point. Forcing it needs HTML or a marker such as a hidden `---` rule. Two cells make the split
  explicit, and the notebook shows it as a cell boundary.
- **Constraints:**
  - Each half is about 610 px wide, so display equations must fit that width.
  - A `notes` cell placed between the pair and the figure would stop the figure from clearing the floats.
  - The notebook shows the two cells stacked, not side by side.
- **Propose:** make `side-by-side` a supported tag:
  - The CSS lives in `make_slides.py`.
  - Add a row to §7 and a half-width budget (about 610 px, or about 60 characters of body text per line) to
    §4.
  - It serves R2.6's lead-in, and it is the likely fix wherever definitions push a figure off the slide.

---

## D. Decisions for the discussion

1. ~~**06 / 06a:** retire `make_06a_slides.py` and treat 06a as the maintained deck, or merge 06a's structure
   back into 06 and keep one notebook? (C7, B2)~~ **Decided:** the script is retired, and 06a is an
   independent presentation.
2. **Build changes:** move the CSS and the MathJax override into `make_slides.py` (C1, B1)? That also means
   choosing which of the CSS rules to keep: figure centering, printed-output size, the MathJax preview fix,
   and the slide outline.
3. **Font policy:** accept a 12 pt base, with the exemptions for dense annotations (C2, C3)?
4. **Animation default:** test native video in VS Code before choosing (C11, B3).
5. **Tooling:** add `measure_deck.py` (per-slide height measurement and screenshots) and `check_deck.py` (the
   rule checker) to the repo?
6. **The skipped edge table in 1.7:** acceptable, or restore it to the deck (B6)?
7. ~~**Two-column layout** (C14)~~ **Decided:** not wanted, and reverted.
   **Side-by-side markdown** (C15): make the `side-by-side` tag a supported build feature? If so, should
   1.8 (text, then the weighted W/D/L figure, on separate slides) be joined the same way?

---

## Appendix: headings written or changed during the split

| Slide heading | Origin |
|---|---|
| 1.3 $A$, $D$ and $L$ for the running example | new: the figure slide |
| 1.3 $L$ is a difference operator | was `###` |
| 1.4 Same ten values, two arrangements | new: the figure slide |
| 1.6 The spectrum of $L$ | was "1.6 The spectrum, and the modes drawn on the graph" |
| 1.6 The modes, drawn on the graph | new |
| 1.6 A higher eigenvalue means more sign changes | replaced "(cont.)" |
| 1.6 The vocabulary, side by side | was `###` |
| 1.7 Weights from distance: a Gaussian kernel | replaced "(cont.)" |
| 1.8 $W$, $D$ and $L$ with weights | new: the figure slide |
| 1.9 What the weights changed, in numbers | new |
| 1.9 The two spectra, each on its own scale | replaced "(cont.)" |
| 1.10 $L$ and $L_{\mathrm{sym}}$ on the same graph | new: the figure slide |
| # Part 2 — Springs and masses | split from 2.1's cell |
| 2.1 Masses and springs, read as a graph | new: the table slide |
| 2.1 The column, its graph, and its five modes | new: the figure slide |
| 2.1 What carries over from Part 1 | new: the bullets slide |
| 2.2 What each column shows | new: the table slide |
| 2.2 The same motions, read off the top mass | new: the traces slide |
| # Part 3 — Temperature sensors | split from 3.1's cell |
| 3.1 85 stations, one day, three years | new: the figure slide |
| 3.2 The geographic graph at work | new: the figure slide |
| 3.3 The dominant pattern is the instrument | new: the figure slide |
| 3.4 What the learned graph discovered | new: split from 3.4's text |
| 3.4 The learned graph, and what it is worth | new: the figure slide |
| 3.5 PCA against the learned graph, day by day | new: the figure slide |
| 3.6 Shared subspace, and a mode the signal cannot use | new: the figure slide |
| Part 3 — what this does not show | new: split from the conclusions |

The two `# Part` headings keep their original text.

### Slide heights before (as presented)

Before the changes, 22 of 26 slides were taller than 800 px:

| Slide | Height |
|---|---|
| Part 2 + 2.1 | 1961 px |
| Part 3 + 3.1 | 1420 px |
| 1.10 | 1399 px |
| 3.4 | 1380 px |
| 2.2 | 1364 px |
| 1.3 | 1288 px |
| 3.3 | 1279 px |
| 1.9 | 1247 px |
| 3.6 | 1212 px |
| 1.6 | 1209 px |
| 1.5 | 1136 px |
| Part 1 summary | 1065 px |
| 3.2 | 1057 px |
| 3.5 | 1047 px |
| 1.4 | 901 px |
| 1.7 | 894 px |
| 1.8 | 894 px |
| 1.2 | 881 px |
| 1.6 (cont.) | 870 px |
| 1.1 | 851 px |
| conclusions | 827 px |
| 3.7 | 811 px |

After the changes, the tallest of the 49 slides is 783 px.
