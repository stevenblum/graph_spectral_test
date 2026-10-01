"""Turn a lesson notebook into a reveal.js slide deck.

    python make_slides.py 01_intro_presentation.ipynb            # write <name>.slides.html
    python make_slides.py 01_intro_presentation.ipynb --serve    # ... and serve it in a browser
    python make_slides.py 01_intro_presentation.ipynb --code     # keep the code cells visible

This is the command from the nbconvert docs with the settings that make a long teaching
notebook behave on a projector:

    --no-input          slides show prose, figures and printed output, not source
    reveal_width/height 1280x800 instead of the 960x700 default, so wide figures fit
    reveal_scroll       a slide that still overflows can be scrolled rather than clipped
    reveal_theme        'simple' -- dark text on white, which survives bad projectors

The deck is one self-contained HTML file (figures are embedded), except for reveal.js
itself, which loads from a CDN. For an offline talk, fetch reveal.js next to the notebook
and add:  --reveal-prefix reveal.js

Which cells become slides is controlled by each cell's `slideshow.slide_type` metadata,
not by this script. In Jupyter: View > Right Sidebar > Notebook Tools > Slide Type (lab),
or View > Cell Toolbar > Slideshow (classic). The values are:

    slide     start a new slide (left/right arrow)
    subslide  a vertical continuation of the current slide (down arrow)
    fragment  appears on the current slide on the next click
    notes     speaker notes -- hidden on the slide, shown in the speaker view (press 's')
    skip      left out of the deck entirely (imports, helper definitions)
    -         (or unset) merged into the previous cell's slide
"""
import argparse
import pathlib
import subprocess
import sys

# 16:10. Wider than 4:3, so a slide gives up some height -- the scarcer direction in these
# notebooks -- in exchange for filling a widescreen display. If this changes, the figure
# sizes in the notebooks have to change with it: they are authored in slide coordinates
# (1 in = 100 px at dpi 100), against the budget in docs/agent_references/notebook_reveal_standard.md.
REVEAL = {
    "reveal_width": "1280",
    "reveal_height": "800",
    "reveal_theme": "simple",
    "reveal_transition": "none",
    # the simplest numbering that needs no edits to the content: reveal prints
    # "current / total" in the corner of every slide
    "reveal_number": "c/t",
}

# Reveal reserves this fraction of the window around the slide. Its default is 0.04, which
# is a visible band on all four sides; 0.01 keeps the slide off the bezel and little else.
REVEAL_MARGIN = 0.01

# Overflowing slides scroll. nbconvert implements this by injecting jQuery that gives an
# over-tall slide height:calc(95vh) with overflow-y:scroll and a 20px top margin -- so the
# scroll box is sized against the browser viewport while the slide is a scaled coordinate
# system, and the two do not line up exactly. That is the trade for never having a slide
# silently resized: what does not fit scrolls, and the fix is to edit the content.


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notebook", help="the .ipynb to convert")
    ap.add_argument("--serve", action="store_true",
                    help="serve the deck and open it in a browser (Ctrl-C to stop)")
    ap.add_argument("--code", action="store_true", help="keep code cells visible")
    ap.add_argument("--no-scroll", action="store_true",
                    help="clip an overflowing slide instead of letting it scroll")
    ap.add_argument("--margin", type=float, default=REVEAL_MARGIN,
                    help=f"fraction of the window reserved around the slide "
                         f"(reveal's own default is 0.04; here {REVEAL_MARGIN})")
    ap.add_argument("--theme", default=REVEAL["reveal_theme"],
                    help="reveal.js theme: simple, white, league, beige, night, ... "
                         f"(default: {REVEAL['reveal_theme']})")
    ap.add_argument("--reveal-prefix", default=None,
                    help="path to a local reveal.js copy, for presenting offline")
    args, extra = ap.parse_known_args()

    nb = pathlib.Path(args.notebook)
    if not nb.exists():
        sys.exit(f"no such notebook: {nb}")

    cmd = [sys.executable, "-m", "nbconvert", str(nb), "--to", "slides"]
    if not args.code:
        cmd.append("--no-input")
    for key, val in REVEAL.items():
        cmd.append(f"--SlidesExporter.{key}={args.theme if key == 'reveal_theme' else val}")
    if not args.no_scroll:
        cmd.append("--SlidesExporter.reveal_scroll=True")
    if args.reveal_prefix:
        cmd += ["--reveal-prefix", args.reveal_prefix]
    if args.serve:
        cmd.append("--post")
        cmd.append("serve")
    cmd += extra

    print(" ".join(cmd), "\n")
    rc = subprocess.call(cmd)
    if rc == 0 and not args.serve:
        set_margin(nb.with_suffix("").as_posix() + ".slides.html", args.margin)
    raise SystemExit(rc)


def set_margin(path, margin):
    """Add reveal's `margin` to the generated deck.

    nbconvert's template writes only width and height into Reveal.initialize, and reveal's
    own default margin is 0.04 -- a band of dead space on all four sides. There is no
    exporter trait for it, so it is inserted here. Nothing else in the file is touched.
    """
    html = pathlib.Path(path)
    if not html.exists():
        print(f"note: {path} not found; reveal margin left at its 0.04 default")
        return
    text = html.read_text(encoding="utf-8")
    start = text.find("Reveal.initialize({")
    end = text.find("});", start)
    if start < 0 or end < 0:
        print("note: Reveal.initialize not found; margin left at its 0.04 default")
        return
    if "margin:" in text[start:end]:
        return
    html.write_text(text[:end] + f"            margin: {margin},\n" + text[end:],
                    encoding="utf-8")
    print(f"set reveal margin to {margin}  ({path})")


if __name__ == "__main__":
    main()
