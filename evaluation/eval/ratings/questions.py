"""The question taxonomy: what each rating question is *about*.

Every question in a dossier belongs to one category (Data Loading / Neural Data
/ Data Variables / Missing-Data Handling / End-to-End / Code Efficiency) and,
inside Data Variables, to one sub-type (source variables / processing /
thresholding / alignment). `categorize` works that out from the question's
*text*, not its number — question numbers have been reshuffled twice in this
project, and anything keyed to them silently rots (see archive/README.md).
"""

from __future__ import annotations

import re

import numpy as np


RATING_SCALE = {
    "incorrect": -2,
    "concerning": -1,
    "ok": 0,
    "match": 1,
    "better": 2,
}


CATEGORY_ORDER = [
    "Data Loading",
    "Neural Data",
    "Data Variables",
    "Missing-Data Handling",
    "End-to-End",
    "Code Efficiency",
]

SUBTYPE_ORDER = {
    "Data Loading": [
        "Overall",
        "Split into subjects",
        "Split into sessions",
        "Split into trials",
        "Trial filtering",
    ],
    "Neural Data": [
        "Source variables",
        "Processing",
        "Filtering",
        "Time resolution",
        "Alignment",
    ],
    "Data Variables": [
        "Source variables",
        "Processing",
        "Thresholding",
        "Alignment",
    ],
    "Missing-Data Handling": [""],
    "End-to-End": [""],
    "Code Efficiency": [
        "Processing time",
        "Vectorization",
        "Repeated work",
        "Unnecessary work",
        "Memory usage",
    ],
}

_Q1_SUB = {
    "a": "Overall",
    "b": "Split into subjects",
    "c": "Split into sessions",
    "d": "Split into trials",
    "e": "Trial filtering",
}
_Q2_SUB = {
    "a": "Source variables",
    "b": "Processing",
    "c": "Filtering",
    "d": "Time resolution",
    "e": "Alignment",
}
# Which sub-question a Data Variables row is, keyed by what it ASKS rather
# than by its sub-letter. The letters moved when the references were
# renumbered (alignment went from -c to -d, and -c became "thresholded"), so
# letter-keyed classification silently dropped every alignment row and
# mislabelled the thresholding ones.
_VAR_ROLE_KEYWORDS = [
    ("derived from", "Source variables"),
    ("processing is involved", "Processing"),
    ("is the `output`", "Processing"),
    ("data processed", "Processing"),
    ("thresholded", "Thresholding"),
    ("discretiz", "Thresholding"),
    ("aligned", "Alignment"),
    ("alignment", "Alignment"),
]

# Display order of the Data Variables sub-blocks.
VAR_SUBTYPES = ("Source variables", "Processing", "Thresholding", "Alignment")

# Fallback for anything the keywords miss: the historical sub-letter map.
_VAR_SUB = {
    "a": "Source variables",
    "b": "Processing",
    "c": "Alignment",
}


def _var_subtype(title_lower: str) -> str | None:
    for kw, sub in _VAR_ROLE_KEYWORDS:
        if kw in title_lower:
            return sub
    return None
_EFF_KEYWORDS = [
    ("time-consuming", "Processing time"),
    ("vectorized", "Vectorization"),
    ("repeat", "Repeated work"),
    ("unnecessary", "Unnecessary work"),
    ("memory", "Memory usage"),
]

_VAR_TITLE_RE = re.compile(r"`(input|output)`\s*\*([^*]+)\*")


def categorize(qid, title):
    """Map (qid, title) -> (category, subtype, var_label) or None."""
    title_lower = title.lower()

    if qid.startswith("1-"):
        sub = _Q1_SUB.get(qid.split("-", 1)[1])
        if sub:
            return ("Data Loading", sub, None)

    if qid.startswith("2-"):
        sub = _Q2_SUB.get(qid.split("-", 1)[1])
        if sub:
            return ("Neural Data", sub, None)

    if "missing data" in title_lower:
        return ("Missing-Data Handling", "", None)

    for kw, sub in _EFF_KEYWORDS:
        if kw in title_lower:
            return ("Code Efficiency", sub, None)

    m = _VAR_TITLE_RE.search(title)
    if m and "-" in qid:
        kind, name = m.group(1), m.group(2).strip()
        sub_letter = qid.split("-", 1)[1]
        sub = _var_subtype(title_lower) or _VAR_SUB.get(sub_letter)
        if sub:
            return ("Data Variables", sub, f"{kind}: {name}")

    return None


BUCKET_ORDER = ["≥ match", "≥ ok", "≥ concerning", "has incorrect"]


def bucket(min_rating):
    """Map the worst rating in a trial to a coarse bucket label."""
    if min_rating is None or (isinstance(min_rating, float) and np.isnan(min_rating)):
        return None
    if min_rating >= 1:  return "≥ match"
    if min_rating >= 0:  return "≥ ok"
    if min_rating >= -1: return "≥ concerning"
    return "has incorrect"
