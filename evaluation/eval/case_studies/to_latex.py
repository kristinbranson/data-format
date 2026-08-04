#!/usr/bin/env python3
"""Convert the case-study markdown cells of examples.ipynb to LaTeX.

Each cell whose first line matches

    #### Example N: <Dataset> - <CATEGORY>

is wrapped in an ``agentexample`` environment, with the title
``<Dataset> --- \\texttt{<CATEGORY>}`` passed as the optional argument so
``amsthm`` auto-numbers it (we drop the ``Example N:`` prefix from the
markdown — LaTeX assigns the number).

Required preamble in your main .tex file:

    \\usepackage{amsthm}
    \\usepackage{booktabs}
    \\usepackage[table]{xcolor}   % for row-shading in trial-summary tables
    \\usepackage{minted}          % Overleaf has shell-escape on; swap for listings if needed
    \\theoremstyle{definition}
    \\newtheorem{agentexample}{Example}

Usage (from evaluation/eval/):
    python3 -m case_studies                     # rewrite examples.tex
    python3 -m case_studies --check             # is the committed .tex current?
    python3 -m case_studies --out path/to.tex   # write elsewhere
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
NB_PATH = HERE / "examples.ipynb"
TEX_PATH = HERE / "examples.tex"

EXAMPLE_HEADER_RE = re.compile(
    r"^####\s*Example\s+\d+\s*:\s*(?P<dataset>[^-]+?)\s*-\s*(?P<cat>\S+)\s*$"
)

# ---------------------------------------------------------------------------
# Inline-text rendering
# ---------------------------------------------------------------------------

def tex_escape(s: str) -> str:
    """Escape LaTeX special characters in plain prose (NOT inside code blocks)."""
    repl = [
        ("\\", r"\textbackslash{}"),
        ("&",  r"\&"),
        ("%",  r"\%"),
        ("$",  r"\$"),
        ("#",  r"\#"),
        ("_",  r"\_"),
        ("{",  r"\{"),
        ("}",  r"\}"),
        ("~",  r"\textasciitilde{}"),
        ("^",  r"\textasciicircum{}"),
    ]
    for a, b in repl:
        s = s.replace(a, b)
    # Unicode niceties
    s = s.replace("—", "---").replace("–", "--")
    s = (s.replace("≈", r"$\approx$")
          .replace("×", r"$\times$")
          .replace("≤", r"$\leq$").replace("≥", r"$\geq$")
          .replace("−", "-"))
    return s


def _texttt_escape(s: str) -> str:
    """Lighter escape used inside \\texttt{...} (keeps it close to verbatim)."""
    return (s.replace("\\", r"\textbackslash{}")
             .replace("{", r"\{").replace("}", r"\}")
             .replace("_", r"\_").replace("&", r"\&")
             .replace("%", r"\%").replace("#", r"\#")
             .replace("$", r"\$")
             .replace("^", r"\textasciicircum{}")
             .replace("~", r"\textasciitilde{}"))


INLINE_BACKTICK = re.compile(r"`([^`]+)`")
INLINE_BOLD     = re.compile(r"\*\*([^*]+)\*\*")
INLINE_ITALIC   = re.compile(r"(?<!\*)\*([^*]+)\*(?!\*)")


def render_inline(text: str) -> str:
    """Render bold / italic / backtick spans inside a plain-text fragment."""
    # Stash backtick spans first so their contents aren't double-escaped.
    backticks = []
    def stash(m):
        backticks.append(m.group(1))
        return f"\x00BTQ{len(backticks)-1}\x00"
    text = INLINE_BACKTICK.sub(stash, text)
    text = tex_escape(text)
    text = INLINE_BOLD.sub(lambda m: r"\textbf{" + m.group(1) + "}", text)
    text = INLINE_ITALIC.sub(lambda m: r"\emph{" + m.group(1) + "}", text)

    def unstash(m):
        return r"\texttt{" + _texttt_escape(backticks[int(m.group(1))]) + "}"
    return re.sub(r"\x00BTQ(\d+)\x00", unstash, text)


# ---------------------------------------------------------------------------
# Block-level parsing
# ---------------------------------------------------------------------------

TABLE_SEP_RE = re.compile(r"^\|[\s:\-|]+\|\s*$")


def _is_table_start(lines, i):
    return (i + 1 < len(lines)
            and lines[i].startswith("|")
            and TABLE_SEP_RE.match(lines[i + 1]))


def parse_blocks(src: str):
    """Yield (kind, payload) blocks from a markdown cell body.

    kind in {"text", "code", "table"}.
    """
    lines = src.splitlines()
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        # Fenced code block
        if line.lstrip().startswith("```"):
            lang = line.lstrip()[3:].strip() or "text"
            i += 1
            buf = []
            while i < n and not lines[i].lstrip().startswith("```"):
                buf.append(lines[i]); i += 1
            i += 1  # consume closing fence
            yield ("code", (lang, "\n".join(buf)))
            continue
        # GFM table
        if _is_table_start(lines, i):
            buf = [lines[i], lines[i + 1]]; i += 2
            while i < n and lines[i].startswith("|"):
                buf.append(lines[i]); i += 1
            yield ("table", buf)
            continue
        # Plain text paragraph
        buf = []
        while (i < n and lines[i].strip() != ""
               and not lines[i].lstrip().startswith("```")
               and not _is_table_start(lines, i)):
            buf.append(lines[i]); i += 1
        if buf:
            yield ("text", "\n".join(buf))
        while i < n and lines[i].strip() == "":
            i += 1


# ---------------------------------------------------------------------------
# Block renderers
# ---------------------------------------------------------------------------

def render_text(block: str) -> str:
    return render_inline(block) + "\n"


MINTED_OPTS = "bgcolor=codebg, fontsize=\\footnotesize, breaklines, frame=none, xleftmargin=0.5em"


def render_code(lang: str, code: str) -> str:
    return (f"\\begin{{minted}}[{MINTED_OPTS}]{{{lang}}}\n"
            f"{code}\n"
            f"\\end{{minted}}\n")


# Per-rating row shading. Keyed off the lowercased text of the last cell
# (which is the Rating column in our trial-summary tables).
ROW_COLORS = {
    "incorrect":  r"\rowcolor{red!20}",
    "concerning": r"\rowcolor{yellow!35}",
}


def render_table(rows):
    def split_row(r):
        return [c.strip() for c in r.strip().strip("|").split("|")]
    header = split_row(rows[0])
    body   = [split_row(r) for r in rows[2:]]
    spec   = "l" * len(header)   # left-align by default; tweak by hand if needed
    lines = [
        r"\begin{center}",
        r"\begin{tabular}{" + spec + "}",
        r"\toprule",
        " & ".join(render_inline(c) for c in header) + r" \\",
        r"\midrule",
    ]
    for row in body:
        rating = row[-1].lower().strip() if row else ""
        prefix = ROW_COLORS.get(rating, "")
        rendered = " & ".join(render_inline(c) for c in row) + r" \\"
        lines.append(prefix + " " + rendered if prefix else rendered)
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{center}"]
    return "\n".join(lines) + "\n"


def render_example(title: str, body: str) -> str:
    out = [f"\\begin{{agentexample}}[{title}]"]
    for kind, payload in parse_blocks(body):
        if kind == "text":
            out.append(render_text(payload))
        elif kind == "code":
            out.append(render_code(*payload))
        elif kind == "table":
            out.append(render_table(payload))
    out.append("\\end{agentexample}\n")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def convert(nb_path: Path = NB_PATH) -> tuple[str, int]:
    """Render the notebook's case-study cells to LaTeX. Returns (text, count).

    Reads nothing but the notebook's JSON — no kernel, no eval data, no
    imports from the rest of the tree. Every markdown cell whose first line
    is `#### Example N: <Dataset> - <CATEGORY>` becomes one `agentexample`
    environment; everything else in the notebook is ignored.
    """
    nb = json.loads(nb_path.read_text())
    chunks = [
        "% Auto-generated from examples.ipynb by `python3 -m case_studies`.",
        "% Do not edit by hand — edit the notebook and regenerate.",
        "% Required preamble:",
        "%   \\usepackage{amsthm,booktabs,minted}",
        "%   \\usepackage[table]{xcolor}     % for row shading in trial tables",
        "%   \\theoremstyle{definition}",
        "%   \\newtheorem{agentexample}{Example}",
        "",
        "% Light gray background for code blocks. Move \\definecolor to your",
        "% preamble if you want it shared with other minted blocks.",
        r"\providecolor{codebg}{gray}{0.95}",
        "",
    ]
    n_examples = 0
    for cell in nb["cells"]:
        if cell["cell_type"] != "markdown":
            continue
        src = cell["source"]
        if isinstance(src, list):
            src = "".join(src)
        first_line = src.lstrip().splitlines()[0] if src.strip() else ""
        m = EXAMPLE_HEADER_RE.match(first_line)
        if not m:
            continue
        dataset = m.group("dataset").strip()
        cat     = m.group("cat").strip()
        cat_tex = r"\texttt{" + cat.replace("_", r"\_") + "}"
        title   = f"{dataset}, {cat_tex}"
        body    = src.split("\n", 1)[1] if "\n" in src else ""
        chunks.append(render_example(title, body))
        n_examples += 1

    return "\n".join(chunks), n_examples

