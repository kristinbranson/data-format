"""Presentation of the result tables — column names, rater labels, LaTeX.

The analysis modules use the short internal names (`LZ`, `kappa`, `pred`); this
turns them into what belongs in a figure or a paper, in one place, so the
notebook cells stay one line each and the printed and LaTeX versions of a table
can never drift apart.
"""

from __future__ import annotations

import pandas as pd

# Internal rater name -> how it should read in a table.
RATER_LABELS = {
    "LZ": "Human #1",
    "KB": "Human #2",
    "claude": "Claude",
    "codex": "Codex",
    "combined": "Combined",
    "claude_unsup": "Claude Unsup",
    "codex_unsup": "Codex Unsup",
    "LZ_null": "Human Null",
}

# Kappa gets a real kappa. The printed table uses the Unicode letter, which
# renders anywhere; the LaTeX table uses math mode.
AGREEMENT_COLUMNS = {
    "rater_a": "Rater A",
    "rater_b": "Rater B",
    "pearson": "Pearson r",
    "kappa": "Cohen's κ",
}
AGREEMENT_COLUMNS_LATEX = dict(AGREEMENT_COLUMNS, kappa=r"Cohen's $\kappa$")

BINARY_COLUMNS = {
    "pred": "Rater",
    "balanced_acc": "Balanced Acc",
    "recall": "Recall",
    "precision": "Precision",
    "f1": "F1",
    "TP": "TP", "FP": "FP", "FN": "FN", "TN": "TN",
}

# Raw accuracy sits first when asked for, next to the balanced version it should
# be read against: mistakes are ~12% of the rows, so a rater that flags nothing
# scores ~0.88 on it. Useful to see, misleading alone.
BINARY_COLUMNS_ACC = {"pred": "Rater", "accuracy": "Accuracy",
                      **{k: v for k, v in BINARY_COLUMNS.items() if k != "pred"}}

FLOAT_FMT = "%.3f"

# Metrics shown to three decimals; everything else (the counts) stays integer.
FLOAT_KEYS = {"pearson", "kappa", "spearman", "exact", "accuracy",
              "balanced_acc", "recall", "precision", "f1", "d_prime"}

RATER_COLS = ("rater_a", "rater_b", "pred", "truth")

# Columns a caller may have grouped by; they stay in front because they are what
# the rows are keyed by. Anything else not asked for (n, d_prime, n_mistakes,
# specificity, ...) is dropped rather than trailing along.
GROUP_COLS = ("dataset", "category", "subtype", "agent", "prompt", "condition",
              "trial", "qid")


def _prepare(df: pd.DataFrame, columns: dict[str, str]) -> pd.DataFrame:
    """Relabel raters, then keep and rename `columns`, in their given order."""
    out = df.copy()
    for col in RATER_COLS:
        if col in out.columns:
            out[col] = out[col].map(lambda v: RATER_LABELS.get(v, v))
    lead = [c for c in GROUP_COLS if c in out.columns]
    keep = [c for c in columns if c in out.columns]
    return out[lead + keep].rename(columns=columns)


# `escape=False` is needed so the kappa header stays math, which means the cell
# text has to be escaped by hand — "Human #1" would otherwise comment out the
# rest of the line.
_LATEX_ESCAPES = {"#": r"\#", "&": r"\&", "%": r"\%", "_": r"\_"}


def _escape_cells(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(
                lambda v: "".join(_LATEX_ESCAPES.get(ch, ch) for ch in str(v))
                if isinstance(v, str) else v)
    return out


def _float_labels(df: pd.DataFrame, columns: dict[str, str]) -> list[str]:
    """The renamed columns that should print to three decimals."""
    return [label for key, label in columns.items()
            if key in FLOAT_KEYS and label in df.columns]


def _styled(df: pd.DataFrame, columns: dict[str, str]):
    prepared = _prepare(df, columns)
    floats = _float_labels(prepared, columns)
    return prepared.style.hide(axis="index").format({c: "{:.3f}" for c in floats})


def agreement(df: pd.DataFrame):
    """Agreement table, ready to display: no index, no `n`."""
    return _styled(df, AGREEMENT_COLUMNS)


def binary(df: pd.DataFrame, *, accuracy: bool = False):
    """Binary-accuracy table, ready to display: no index, no `n`.

    Raw accuracy is left out by default: mistakes are rare, so a rater that
    flags nothing scores ~0.9 on it — `balanced_acc` and the null row are the
    honest comparisons. `accuracy=True` adds it back, first, for a table where
    both are wanted side by side.
    """
    return _styled(df, BINARY_COLUMNS_ACC if accuracy else BINARY_COLUMNS)


def agreement_latex(df: pd.DataFrame, **kwargs) -> str:
    return _to_latex(_escape_cells(_prepare(df, AGREEMENT_COLUMNS_LATEX)), **kwargs)


def binary_latex(df: pd.DataFrame, **kwargs) -> str:
    return _to_latex(_escape_cells(_prepare(df, BINARY_COLUMNS)), **kwargs)


def _to_latex(df: pd.DataFrame, *, caption: str | None = None,
              label: str | None = None) -> str:
    return df.to_latex(index=False, escape=False, float_format=FLOAT_FMT,
                       caption=caption, label=label)


# ---- the paper's judge table -------------------------------------------------
#
# Rows are grouped by what the rater had in front of it, which is the comparison
# the table exists to make: the same judge with and without the reference
# solution, read against a second human doing the same task from the same
# material. `Supervised` / `Unsupervised` here are the *judge run*, not a group
# of datasets — every row covers all 8.

JUDGE_SETUP = {
    "claude": ("Supervised", "Claude"),
    "codex": ("Supervised", "Codex"),
    "combined": ("Supervised", "Combined"),
    "claude_unsup": ("Unsupervised", "Claude"),
    "codex_unsup": ("Unsupervised", "Codex"),
    "KB": ("Human", "Second evaluator"),
}
# The human row leads: it is the ceiling the judge rows are read against.
SETUP_ORDER = ("Human", "Supervised", "Unsupervised")

# (header, key, decimals) in column order, grouped as the header spans them,
# with the column alignment the group's numbers want. Read left to right: what
# the rater actually did, then how well it caught mistakes, then how well it
# told the two classes apart at all.
COUNT_COLS = [("TP", "TP", 0), ("FP", "FP", 0), ("FN", "FN", 0), ("TN", "TN", 0)]
CATCH_COLS = [("F1", "f1", 3), ("Recall", "recall", 3), ("Prec.", "precision", 3)]
DISC_COLS = [(r"Bal.\ Acc.", "balanced_acc", 3), (r"$d'$", "d_prime", 3)]

# Both paper tables carry the same measures; only the row labels differ. Counts
# are right-aligned because they run 2 to 4 digits; every rate is a fixed-width
# 0.xxx, so centering those columns costs no alignment and puts a short header
# ("F1") over the middle of its numbers instead of against their right edge.
JUDGE_GROUPS = [("Counts", COUNT_COLS, "r"),
                ("Catching Mistakes", CATCH_COLS, "c"),
                ("Discriminability", DISC_COLS, "c")]


def _header_rows(groups, lead: list[str]) -> tuple[str, list[str]]:
    """Group spans, their rules, the column names, and the tabular spec.

    Driven off `groups` so the two tables cannot drift from their own headers:
    adding a column changes the spec and the `\\cmidrule` ranges with it.
    """
    spans, rules, headers, spec = [], [], [], ["l"] * len(lead)
    at = len(lead) + 1
    for name, cs, align in groups:
        spans.append(rf"\multicolumn{{{len(cs)}}}{{c}}{{{name}}}")
        rules.append(rf"\cmidrule(lr){{{at}-{at + len(cs) - 1}}}")
        headers += [h for h, _k, _d in cs]
        spec.append(align * len(cs))
        at += len(cs)
    lines = [" ".join(["&"] * len(lead)) + " " + " & ".join(spans) + r" \\",
             " ".join(rules),
             " & ".join([*lead, *headers]) + r" \\"]
    return " ".join(spec), lines


def _cells(row, groups, mark: str = "") -> list[str]:
    """One table row's numbers, formatted to each column's decimals."""
    return [f"{mark}{int(row[k])}" if dp == 0 else f"{mark}{row[k]:.{dp}f}"
            for _group, cs, _align in groups for _header, k, dp in cs]


def judge_latex(df: pd.DataFrame, *, setups=JUDGE_SETUP, order=SETUP_ORDER,
                caption: str | None = None, label: str | None = None) -> str:
    """The grouped judge table: counts, catching mistakes, discriminability.

    `df` is a `binary.table` result; its `pred` column selects and names the
    rows through `setups`, so a predictor with no entry there (the shuffled
    null) is simply left out of the paper table.

    Needs `booktabs` and `multirow`.
    """
    rows = {r["pred"]: r for _, r in df.iterrows()}

    body = []
    for setup in order:
        preds = [p for p, (s, _label) in setups.items() if s == setup and p in rows]
        for i, pred in enumerate(preds):
            head = (rf"\multirow{{{len(preds)}}}{{*}}{{{setup}}}" if i == 0 else "")
            body.append(" & ".join([head, _escape(setups[pred][1]),
                                    *_cells(rows[pred], JUDGE_GROUPS)]) + r" \\")
        if setup != order[-1] and preds:
            body.append(r"\midrule")

    spec, header = _header_rows(JUDGE_GROUPS, ["Setup", "Rater"])

    lines = [
        r"% requires \usepackage{booktabs, multirow}",
        r"\begin{table}[!h]",
        r"\centering",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{" + spec + "}",
        r"\toprule",
        *header,
        r"\midrule",
        *body,
        r"\bottomrule",
        r"\end{tabular}",
    ]
    if caption:
        lines.append(r"\caption{" + caption + "}")
    if label:
        lines.append(r"\label{" + label + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ---- the agreement matrix ----------------------------------------------------
#
# Every rater pair in one square, the way a correlation matrix is read: Pearson
# above the diagonal, chance-corrected kappa below, so a cell and its mirror
# image are the two readings of the same pair and the gap between them is how
# much of that agreement was free.

MATRIX_RATERS = ("LZ", "KB", "claude", "codex", "claude_unsup", "codex_unsup")
MATRIX_LABELS = {"LZ": "Evaluator #1", "KB": "Evaluator #2",
                 "claude": "Claude", "codex": "Codex",
                 "claude_unsup": "Claude Unsup", "codex_unsup": "Codex Unsup"}


def agreement_matrix_latex(df: pd.DataFrame, raters=MATRIX_RATERS, *,
                           labels=MATRIX_LABELS, caption: str | None = None,
                           label: str | None = None, decimals: int = 3) -> str:
    """The rater-by-rater agreement square, as LaTeX.

    Columns are numbered rather than named — six names across is wider than a
    column — with the number repeated in the row label, which is the usual
    correlation-matrix convention.

    `df` is any frame with one column per rater; the numbers come from
    `agreement.pair_stats`, so they match the row-per-pair table exactly.
    """
    from .agreement import pair_stats

    n = len(raters)
    stats = {}
    for i, a in enumerate(raters):
        for b in raters[i + 1:]:
            stats[(a, b)] = pair_stats(df, a, b)

    def cell(i, j):
        if i == j:
            return r"---"
        a, b = (raters[i], raters[j]) if i < j else (raters[j], raters[i])
        value = stats[(a, b)]["pearson" if i < j else "kappa"]
        return "--" if pd.isna(value) else f"{value:.{decimals}f}"

    body = []
    for i in range(n):
        name = _escape(labels.get(raters[i], raters[i]))
        body.append(" & ".join([f"({i + 1}) {name}"] + [cell(i, j) for j in range(n)])
                    + r" \\")

    lines = [
        r"% requires \usepackage{booktabs}",
        r"\begin{table}[!h]",
        r"\centering",
        r"\setlength{\tabcolsep}{6pt}",
        r"\begin{tabular}{l" + "c" * n + r"}",
        r"\toprule",
        " & ".join([""] + [f"({i + 1})" for i in range(n)]) + r" \\",
        r"\midrule",
        *body,
        r"\bottomrule",
        r"\end{tabular}",
    ]
    if caption:
        lines += [r"\vspace{5pt}", r"\caption{" + caption + "}"]
    if label:
        lines.append(r"\label{" + label + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ---- judge vs the agent it is scoring ----------------------------------------
#
# The same four numbers again, split by whose trials are being judged. The
# question is whether a judge goes easier on the agent that shares its model,
# so the two rows where judge and target differ are the comparison and are
# shaded in the paper table.

AGENT_TARGET = {"claude-code": "Claude", "codex": "Codex"}
CROSS_GROUPS = JUDGE_GROUPS
CROSS_COLUMNS = {"family": "Family", "judge": "Judge", "target": "Target",
                 "TP": "TP", "FP": "FP", "FN": "FN", "TN": "TN",
                 "f1": "F1", "recall": "Recall", "precision": "Precision",
                 "balanced_acc": "Balanced Acc", "d_prime": "d'"}

# What `cross_judge_frame` carries over from `binary.table`: every measure the
# two tables show, plus `n` for the caption.
CROSS_MEASURES = tuple(k for _g, cs, _a in CROSS_GROUPS for _h, k, _d in cs) + ("n",)


def cross_judge_frame(df: pd.DataFrame, *, setups=JUDGE_SETUP,
                      targets=AGENT_TARGET) -> pd.DataFrame:
    """`binary.table(..., by="agent")` reshaped into family / judge / target rows.

    Ordered judge-major inside each family, so the two middle rows of a block
    are the cross-model ones. Adds a boolean `cross` column for the shading.
    """
    rows = []
    for _, r in df.iterrows():
        if r["pred"] not in setups or r["agent"] not in targets:
            continue
        family, judge = setups[r["pred"]]
        rows.append({"family": family, "judge": judge,
                     "target": targets[r["agent"]],
                     "cross": judge != targets[r["agent"]],
                     **{k: r[k] for k in CROSS_MEASURES}})

    order = {f: i for i, f in enumerate(SETUP_ORDER)}
    side = {name: i for i, name in enumerate(targets.values())}
    out = pd.DataFrame(rows)
    return (out.sort_values(by=["family", "judge", "target"],
                            key=lambda c: c.map(lambda v: order.get(v, side.get(v, 0))))
               .reset_index(drop=True))


def cross_judge(df: pd.DataFrame):
    """The family / judge / target table, cross-model rows shaded."""
    frame = cross_judge_frame(df)
    shaded = frame["cross"].to_numpy()
    prepared = frame[[c for c in CROSS_COLUMNS if c in frame.columns]].rename(
        columns=CROSS_COLUMNS)
    floats = [CROSS_COLUMNS[k] for k in
              ("f1", "recall", "precision", "balanced_acc", "d_prime")]
    return (prepared.style.hide(axis="index")
            .format({c: "{:.3f}" for c in floats})
            .apply(lambda _row: ["background-color: #f0f0f0" if shaded[_row.name] else ""]
                   * len(prepared.columns), axis=1))


def cross_judge_latex(df: pd.DataFrame, *, caption: str | None = None,
                      label: str | None = None) -> str:
    """The same table in the paper's format, with the cross rows shaded.

    Needs `booktabs`, `multirow` and `xcolor` with a `rowgray` color defined;
    the `\\crossrow` shorthand is emitted above the table. A `{n}` in `caption`
    is filled in with the number of rows behind each pairing.
    """
    frame = cross_judge_frame(df)

    body = []
    families = [f for f in SETUP_ORDER if f in set(frame["family"])]
    for family in families:
        block = frame[frame["family"] == family]
        for i, (_, r) in enumerate(block.iterrows()):
            head = (rf"\multirow{{{len(block)}}}{{*}}{{{family}}}" if i == 0 else "")
            mark = r"\crossrow " if r["cross"] else ""
            body.append(" & ".join([head, f"{mark}{r['judge']}",
                                    f"{mark}{r['target']}",
                                    *_cells(r, CROSS_GROUPS, mark)]) + r" \\")
        if family != families[-1]:
            body.append(r"\midrule")

    spec, header = _header_rows(CROSS_GROUPS, ["Family", "Judge", "Target"])

    lines = [
        r"% requires \usepackage{booktabs, multirow} and xcolor with a rowgray color",
        r"\newcommand{\crossrow}{\cellcolor{rowgray}}",
        r"",
        r"\begin{table}[!h]",
        r"\centering",
        r"\setlength{\tabcolsep}{4pt}",
        r"\begin{tabular}{" + spec + "}",
        r"\toprule",
        *header,
        r"\midrule",
        *body,
        r"\bottomrule",
        r"\end{tabular}",
    ]
    if caption:
        sizes = sorted(set(int(v) for v in frame["n"]))
        n = sizes[0] if len(sizes) == 1 else "$-$".join(str(s) for s in sizes)
        lines += [r"\vspace{5pt}", r"\caption{" + caption.replace("{n}", str(n)) + "}"]
    if label:
        lines.append(r"\label{" + label + "}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


def _escape(s: str) -> str:
    return "".join(_LATEX_ESCAPES.get(ch, ch) for ch in s)


def agreement_markdown(df: pd.DataFrame, **kwargs) -> str:
    """The agreement table as a pipe table — paste into a README or an issue."""
    prepared = _prepare(df, AGREEMENT_COLUMNS)
    return _to_markdown(prepared, _float_labels(prepared, AGREEMENT_COLUMNS), **kwargs)


def binary_markdown(df: pd.DataFrame, **kwargs) -> str:
    """The binary-accuracy table as a pipe table."""
    prepared = _prepare(df, BINARY_COLUMNS)
    return _to_markdown(prepared, _float_labels(prepared, BINARY_COLUMNS), **kwargs)


def _to_markdown(df: pd.DataFrame, floats: list[str], *,
                 caption: str | None = None) -> str:
    """GitHub-flavored pipe table, padded so the source is readable too.

    Written out here rather than through `DataFrame.to_markdown`, which needs
    `tabulate` — not installed in this environment, and not worth a dependency
    for eleven rows. Numbers are right-aligned, text left-aligned, and the
    three-decimal formatting matches the printed and LaTeX versions.
    """
    head = [str(c) for c in df.columns]
    numeric = [df[c].dtype.kind in "if" for c in df.columns]
    rows = [[_md_cell(v, c in floats) for c, v in zip(df.columns, row)]
            for row in df.itertuples(index=False, name=None)]

    # Minimum 3, so the separator row always has room for `--:`.
    width = [max([3, len(h)] + [len(r[i]) for r in rows])
             for i, h in enumerate(head)]

    def line(cells):
        return "| " + " | ".join(
            c.rjust(w) if num else c.ljust(w)
            for c, w, num in zip(cells, width, numeric)) + " |"

    rule = "| " + " | ".join(("-" * (w - 1) + ":") if num else ("-" * w)
                             for w, num in zip(width, numeric)) + " |"
    out = [line(head), rule, *(line(r) for r in rows)]
    if caption:
        out = [f"**{caption}**", "", *out]
    return "\n".join(out)


def _md_cell(value, is_float: bool) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "—"
    return f"{value:.3f}" if is_float else str(value)
