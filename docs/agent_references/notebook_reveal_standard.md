# Notebook standard for reveal.js decks

How to format a Jupyter notebook so that it converts into a reveal.js slide deck with no hand edits,
no per-notebook conversion script, and no derived copy of the notebook. This covers cell structure, slide
metadata, sizing, outputs, markdown, reveal.js features and portability. It is **not** a writing style
guide: it says nothing about what the slides should say, only how the notebook is built so they render well.

Rules are numbered (**R2.3**) so a review can cite them.

## Goals

| | Goal | Rules that serve it most directly |
|---|---|---|
| G1 | The notebook is an accurate preview of the deck | §3, §4 |
| G2 | Minimal overhead: few markings, and no custom text | §2 |
| G3 | Use reveal.js's own features, and add custom ones only where unavoidable | §7 |
| G4 | Each slide combines prose and computed output into one coherent unit | §2, §5 |
| G5 | Portable across computers, operating systems, notebook frontends and browsers | §6, §8 |

## The principle

**The notebook is both the source and the preview.** A stock converter produces the deck from it. The
converter has settings, but no logic specific to any notebook. Every difference between the notebook and
the deck is one of two things:

- an unavoidable difference between the two media, listed in §3, or
- a defect, fixed by editing the notebook.

A defect is never fixed by adding conversion logic, CSS or scaling.

## Reference build

These rules assume the build that `make_slides.py` runs:

- nbconvert's `SlidesExporter` (`--to slides`), with reveal.js 4.0.x and MathJax 2 loaded by nbconvert's template
- slide size 1280 × 800 px, code hidden (`--no-input`), and per-slide scrolling enabled, but only as a safety net

The numbers in §4 were measured on this build in a browser. If the slide size, the theme or the reveal.js
version changes, re-measure §4. The other rules do not depend on the build.

---

## 1. How a notebook becomes a deck

nbconvert reads a single field per cell, `metadata.slideshow.slide_type`:

| `slide_type` | Effect in the deck | Typical cell |
|---|---|---|
| `slide` | starts a new horizontal slide | a markdown cell that opens with `#` or `##` |
| `subslide` | starts a vertical slide below the current one | optional depth, backup material |
| `fragment` | the cell appears on the next click | the takeaway after a figure |
| `-` or unset | joins whatever is open: the current slide, or the current fragment | most cells |
| `notes` | hidden on the slide and shown in the speaker view (`s`) | what the presenter says |
| `skip` | left out of the deck, but kept in the notebook | imports, helpers, checks |

Consequences that drive the rest of this standard:

- **The cell is the atomic unit.** A cell is never split across slides, and its outputs always travel with it.
- **`-` means "continue".** A `-` cell that follows a `fragment` becomes part of that fragment and appears on the same click.
- **Hidden code still prints.** `--no-input` removes the source of every code cell but keeps all of its
  outputs: printed text, warnings, reprs and figures.
- **The deck shows saved outputs.** Converting the notebook does not execute it.
- **Two sets of CSS style a slide.** Jupyter's CSS styles body text and outputs. The reveal.js theme styles headings.

## 2. Structure

**R2.1** Every slide starts with a markdown cell whose **first line is a heading**. That cell is marked `slide`, or `subslide`.

**R2.2** Heading levels have fixed roles:

| Level | Role |
|---|---|
| `#` | Title or part-divider slide. It is alone in its cell, apart from a subtitle or short agenda. |
| `##` | Content slide. One `##` heading equals one slide. |
| `###` to `######` | Organize content inside a slide, and never start a slide. A `subslide` cell may open with `###`. |

**R2.3** A cell that opens with `#` or `##` is always `slide`, and **no other cell is marked `slide`**. As a
result, the notebook's outline is the deck's outline, and the rule can be checked mechanically.

**R2.4** Mark only the cells whose type is not `-`. An unmarked new cell joins the slide above it, which is
usually right, so forgetting a marking is cheap.

**R2.5** A heading may appear only on the first line of its cell. Content meant for two slides goes in two
cells, because nbconvert cannot split one.

**R2.6** Use one pattern, **the slide unit**, for every content slide:

```
[markdown · slide]   ## 1.3  Degree and the Laplacian
                     one to three lines saying what to look at
[code     · -]       computes and draws ONE figure (its source is hidden in the deck)
[markdown · -]       two or three bullets: what the figure shows
[markdown · notes]   optional: what the presenter says
```

The lead-in sits directly above the output it introduces, and the takeaway sits directly below it, so the
deck reads in the same order as the notebook.

**R2.7** A slide has **at most one main output**. Related panels go into one figure (`plt.subplots`), not
into several stacked output cells.

**R2.8** When content outgrows one slide, start another slide with its own descriptive heading, for example
`## 1.6  The spectrum` followed by `## 1.6  The modes on the graph`. Do not repeat a heading with "(cont.)",
and do not rely on the build to invent titles.

**R2.9** Anything the audience should not see goes in **its own `skip` cell**: imports, configuration,
helper definitions, data downloads, and invariant or residual checks. Never mix skipped material with slide
content in one cell. The notebook keeps these cells visible to readers, so they cost nothing.

**R2.10** Fragments:

- A fragment is always a whole cell.
- It continues until the next `fragment`, `subslide` or `slide`.
- Use at most two per slide, for a takeaway that should appear after the audience has looked at the output.
- The notebook shows every fragment at once, so size the slide for its final state.

**R2.11** Speaker notes:

- Use one `notes` cell per slide, placed **before the slide's first fragment**, or anywhere on a slide that has no fragments.
- The speaker view shows only the first notes on a slide.
- A `notes` cell placed directly after a fragment becomes the notes for that fragment.

**R2.12** Subslides (vertical slides) are for optional material that the presenter might skip, such as a
derivation, extra diagnostics or backup. The main line of the talk uses horizontal slides.

### Setting the metadata

In the `.ipynb` file, the marking is this:

```json
"metadata": { "slideshow": { "slide_type": "slide" } }
```

- **JupyterLab and Notebook 7:** right sidebar → Property Inspector → Slide Type.
- **VS Code:** Microsoft's *Jupyter Slide Show* extension adds a slide-type picker to each cell.
- **Agents** write the JSON directly, whenever they create or restructure cells.

## 3. Preview fidelity

The notebook cannot match the deck pixel for pixel. This table shows how far it can go:

| Element | Notebook shows | Deck shows |
|---|---|---|
| Body text, lists, tables | the frontend's default size | 20 px, in Jupyter's font |
| Printed output | the frontend's default size | 19 px monospace |
| `#` / `##` / `###` headings | the frontend's heading styles | the theme's font at about 3.8× / 2.1× / 1.55× body size |
| Figures | the saved pixel size, shrunk to fit the column | the saved pixel size, up to about 1200 px wide |
| Code source | visible | hidden |
| Fragments | all visible | appear on click |
| `notes` and `skip` cells | visible | hidden, or absent |

**R3.1** Treat the notebook view as the slide **in its final state**, with every fragment showing.

**R3.2** Make the preview accurate through **editor settings, not notebook content**:

- Set the notebook's rendered-markdown font to 20 px and its output font to about 19 px.
  - VS Code: `notebook.markup.fontSize` and `notebook.output.fontSize`.
  - JupyterLab: Settings → Theme overrides.
- Keep the notebook column at least about 1250 px wide.

With these settings, body text, output and figures appear at the same pixel sizes as on the slide.

**R3.3** Headings are the difference that remains: on the slide they are larger and in the theme's font.
R4.3 and R6.8 compensate for this.

**R3.4** Put **no deck-only styling in the notebook**. A CSS cell has no counterpart in the notebook view, so
every rule in it makes the preview less accurate (see R7.3).

## 4. The slide budget

A slide is a fixed 1280 × 800 px coordinate system, which reveal.js scales uniformly to fit any screen.
Nothing reflows, so a slide that fits on the author's screen fits on every projector.

**R4.1** Use `figure.dpi = 100`, so that **1 inch of figure is 100 slide pixels**.

**R4.2** Keep figure width at **12 in or less**. The slide shows at most about 1200 px across, and a wider
figure is scaled down, which shrinks its text too.

**R4.3** Keep each heading on one line:

- `##`: 60 characters or fewer
- `#`: 35 characters or fewer

The limits leave room for a fallback heading font (see R8.8).

**R4.4** The total height of a slide is 800 px. Measured costs:

| Element | Height |
|---|---|
| Slide padding, top and bottom | 40 px |
| Markdown cell containing only a `##` heading | 105 px |
| Each bullet line | about 36 px |
| Paragraph | about 26 px per line, plus about 40 px |
| Separate markdown cell with 3 bullets | about 115 px |
| Table row, markdown or DataFrame | about 38 px |
| Display equation, one line | about 45 px |
| Figure cell | figure height × 100 px, plus 66 px |
| Printed output | about 23 px per line, plus about 30 px |

This gives the following maximum figure heights (the `figsize` height, at dpi 100):

| Slide composition | Tallest figure |
|---|---|
| `##` heading + figure | 5.9 in |
| `##` heading + 3 bullets + figure | 4.8 in |
| `##` heading + figure + takeaway cell with 3 bullets | 4.7 in |
| `##` heading + 3 bullets + figure + takeaway cell with 3 bullets | 3.6 in |
| `##` heading + two stacked figures | 5.2 in combined |

**R4.5** **Overflow is a defect.** A scroll bar on a slide means the content does not fit. Fix it by
shrinking the figure, cutting text or splitting the slide. Never fix it with CSS, zoom or automatic scaling.

## 5. Figures and code outputs

**R5.1** Put one setup cell near the top, marked `skip`:

```python
import matplotlib.pyplot as plt

plt.rcParams.update({
    "figure.dpi": 100,                      # 1 in = 100 slide px   (R4.1)
    "figure.constrained_layout.use": True,  # the layout fills the figure, not whitespace
    "font.size": 14,                        # ~19 px, which matches the slide's 20 px body text
})
# Save exactly figsize x dpi. The default 'tight' bbox crops by an unpredictable amount,
# which breaks the budget in §4.
%config InlineBackend.print_figure_kwargs = {"bbox_inches": None}
```

**R5.2** Each figure cell draws **one figure** and ends with `plt.show()`. A trailing expression, such as
`ax.plot(...)` or a bare `fig`, puts a repr like `[<matplotlib.lines.Line2D …>]` on the slide.

**R5.3** Keep figure text at 12 pt or larger. At dpi 100, 14 pt is about the size of the slide's body text.

**R5.4** Do not repeat the slide heading as the figure's title, because it costs height and says nothing new.
Panel titles are fine.

**R5.5** Printed output in a visible cell is slide content:

- Keep it short, and within the budget.
- Format numbers to the precision you will discuss.
- Use aligned monospace columns where they help.
- Output appears in call order: a `print` before `plt.show()` puts the text above the figure.

**R5.6** A visible cell must produce **no warnings, stderr or progress bars**. They render on the slide as
error-styled blocks. Fix the cause. If a warning is known to be harmless, filter that specific warning in
the setup cell.

**R5.7** A DataFrame on a slide has 10 rows or fewer, with values rounded. It renders as a table at body size.

**R5.8** To show code on a slide, use a fenced ` ```python ` block of 10 lines or fewer in the slide's
markdown cell, copied verbatim from the executable cell. The executable cell itself stays hidden. A deck
that shows all code (`make_slides.py --code`) is a different product, not a per-slide option.

**R5.9** Outputs are static by default. Static images render identically in every frontend, in untrusted
notebooks, in the deck and in PDF export.

- **No widgets.** A static deck has no kernel, so widgets appear dead.
- **Interactive plots and JavaScript animations** only where interaction or motion *is* the point.
  - Use one per slide, keep it self-contained, and keep it small.
  - It renders only in a trusted notebook, and it adds megabytes.
- **Motion:** prefer small multiples (several frames in one figure), then native video
  (`FuncAnimation.to_html5_video()`), then JavaScript players (`to_jshtml()`).

## 6. Markdown, math, tables and images

**R6.1** Write headings in ATX style (`## Title`). Never use setext style, where a line of text is
underlined with `---`.

**R6.2** Use **no horizontal rules**. Headings already separate sections in both media, and a rule draws a
line across the slide.

**R6.3** Use **no raw HTML for layout or styling**: no spacer `<div>` or `<br>`, and no `<style>` or
`<script>`. Frontends sanitize raw HTML differently, and markdown inside an HTML block is fragile. Leave
spacing to the renderer.

**R6.4** Use `-` for bullet lists, with at most one level of nesting.

**R6.5** Delimit math with `$…$` inline and `$$…$$` for display. Put display math on its own lines, with a
blank line before and after. Put environments (`aligned`, `cases`, `bmatrix`) inside `$$…$$`, never bare.

**R6.6** Use the **LaTeX subset that every renderer accepts**. The deck uses MathJax 2, JupyterLab uses
MathJax 3, and VS Code uses KaTeX.

| Avoid | Use instead |
|---|---|
| `\newcommand`, `\def` (their scope differs by renderer) | write the expression out |
| `\label`, `\eqref`, `\tag` (numbering is inconsistent) | refer to equations in words |
| `\DeclareMathOperator` | `\operatorname{…}` |
| `\bm` | `\boldsymbol` |
| top-level `align` | `aligned` inside `$$…$$` |
| `\require` | nothing: don't load extensions |

**R6.7** Inside a pipe table, write `\lvert x\rvert` rather than `|x|`, because a bare `|` ends the cell.
Write a literal dollar sign as `\$`.

**R6.8** Write symbols as math (`$\lambda_2$`), not Unicode (`λ₂`), especially in headings. Themes may change
a heading's case: one stock theme uppercases every heading, which turns `λ` into `Λ`. Glyph coverage also
varies by operating system. Never let an emoji carry meaning.

**R6.9** A table on a slide has 8 rows and 4 columns or fewer, and each cell holds a single line.

**R6.10** Markdown images:

- Use a **cell attachment**: paste or drag the image into the markdown cell.
- A relative path such as `![](figs/x.png)` is not embedded, so it breaks when the deck moves without that file.
- Never use a remote URL.
- Always write alt text.

**R6.11** Draw diagrams in code, with matplotlib or networkx, so that they render identically everywhere.
Avoid Mermaid, which not every frontend renders, and avoid HTML diagrams.

## 7. reveal.js features

**R7.1** Reach reveal.js only through `slide_type` and `slideshow.data`. Keys in `slideshow.data` become
`data-*` attributes on the slide's `<section>`, with underscores turned into hyphens.

| Feature | Metadata |
|---|---|
| Slides, vertical slides, fragments, notes, skip | `slide_type` (§1) |
| Background color for one slide | `"data": {"background_color": "#f4f6fa"}` |
| Transition for one slide | `"data": {"transition": "fade"}` |
| Backup slide left out of the slide count | `"data": {"visibility": "uncounted"}` |
| Slide hidden from the deck but kept in the file | `"data": {"visibility": "hidden"}` |

For example:

```json
"metadata": { "slideshow": { "slide_type": "slide", "data": { "visibility": "uncounted" } } }
```

The presenter gets these without any work in the notebook:

- speaker view (`s`)
- overview (`Esc`)
- fullscreen (`f`)
- slide numbers, a build setting
- PDF export: open the deck with `?print-pdf` in Chrome, then print

**R7.2** Do not use:

- reveal.js features newer than the version the build loads (4.0.x)
- reveal.js layout classes such as `r-stack` and `r-stretch`, which need HTML in markdown and do nothing in the notebook (they break G1 and G2)
- background images

Build side-by-side layouts as subplots within one figure.

**R7.3** Theme, slide size, numbering, default transition and any CSS are **build settings**. They live in
one place (`make_slides.py`) and apply to every deck. Keep CSS to the smallest amount that fixes something
the notebook cannot, and record why each rule exists.

## 8. Portability

### The notebook

**R8.1** The notebook is self-contained. It is saved with its outputs, its images are embedded (as outputs
or attachments), and it depends on nothing outside itself at view time.

**R8.2** Paths are relative to the notebook's folder, built with `pathlib`. Never use absolute paths or
user-specific paths. nbconvert, JupyterLab and VS Code all start the kernel in that folder by default.

**R8.3** Downloads happen in `skip` cells and are cached under `data/`, so that a rebuild works offline.

**R8.4** Before every build, execute the notebook top to bottom in a fresh kernel, either with
*Restart & Run All* or with `python -m nbconvert --to notebook --execute --inplace NB.ipynb`. The deck shows
exactly the saved outputs.

**R8.5** Cell ids are unique. When copying cells programmatically, create new cells rather than duplicating them.

**R8.6** Keep the notebook to about 10 MB or less. Large embedded animations are the usual cause of bloat.

### The deck

**R8.7** Add **no external resources**: no remote images, fonts, iframes or scripts. The figures in the deck
HTML are embedded, but the deck still loads the following at view time:

- reveal.js, from unpkg
- MathJax, jQuery and require.js, from cdnjs
- the theme's web fonts

To present offline, either vendor all of these through the build's URL settings, or present from a
PDF export.

**R8.8** Test the deck on the machine and browser that will present it:

- Check the speaker-view pop-up.
- Check how the theme's fonts fall back offline. For example, the `simple` theme's headings fall back to
  Impact when Google Fonts cannot be reached.
- The fixed coordinate system means that aspect ratio only adds letterboxing. The layout never changes.

## 9. Checklist before hand-off

1. Restart and run all, with no errors, warnings or stray output in visible cells (R5.2, R5.6, R8.4).
2. Every `#` and `##` cell is marked `slide`, and no other cell is (R2.3). Every `skip` cell holds only
   skipped material (R2.9).
3. There are no horizontal rules, no raw HTML or CSS, no unembedded images, and only portable math (§6).
4. Every figure is 12 in wide or less, and within the height budget for its slide (§4).
5. Build with `python make_slides.py NB.ipynb`. Then page through the whole deck with Space, which also
   visits vertical slides and fragments. Every slide has a title, and **no slide scrolls** (R4.5).
6. Press `s` to check the notes, and `Esc` to check the outline in the overview.
7. If the deck will be presented elsewhere, open it on that machine, or offline, before the talk (R8.8).
