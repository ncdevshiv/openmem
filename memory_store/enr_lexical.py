"""ENR lexical layer, vendored for OpenMem's embedder-free search path.

Extracted from ENR — Evidence-Native Retrieval
(https://github.com/ncdevshiv/nc-nir, MIT License, © 2026 Shivam Tiwari)
and merged into this single dependency-free-plus-numpy module.

What it provides over the previous `_keyword_search` heuristics:

- full Porter stemming on both index and query side (all inflections, not a
  five-suffix regex), pinned against the paper's own examples;
- BM25 ranking (k1=1.2, b=0.75, Lucene-style idf) — term-frequency saturation
  and document-length normalization replace frequency-rewarding tie-breaks;
- positional exact-phrase matching ("deepseek harness" as a unit);
- deterministic scores; callers can attach per-hit explanations.

Formula (cross-checked by hand-computed tests upstream):
    idf  = ln(1 + (N - df + 0.5) / (df + 0.5))
    tf'  = tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / avgdl))
    bm25 = sum over query terms of idf * tf'
"""

from __future__ import annotations

import math
import re
from collections import defaultdict

import numpy as np

K1 = 1.2
B = 0.75

STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "of", "to", "in",
    "on", "at", "by", "for", "with", "about", "into", "from", "is", "are", "was",
    "were", "be", "been", "being", "it", "its", "this", "that", "these", "those",
    "as", "so", "than", "too", "very", "can", "will", "just", "do", "does", "did",
    "not", "no", "nor", "only", "own", "same", "such", "s", "t", "don", "now",
})

_WORD_RE = re.compile(r"[A-Za-z0-9]+")
# split camelCase/PascalCase: lower->Upper boundary and letter->digit boundary
_CAMEL_RE = re.compile(
    r"(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])"
)


def raw_words(text: str) -> list[str]:
    """Alphanumeric words, case preserved."""
    return _WORD_RE.findall(text)


def split_camel(word: str) -> list[str]:
    parts = _CAMEL_RE.split(word)
    return [p for p in parts if p]


def tokenize(text: str) -> list[str]:
    """Words -> camelCase split -> lowercase -> drop stopwords."""
    out: list[str] = []
    for word in raw_words(text):
        for part in split_camel(word):
            p = part.lower()
            if p in STOPWORDS:
                continue
            out.append(p)
    return out


def stem(word: str) -> str:
    """Porter stemmer, faithful implementation of the 1980 algorithm."""
    w = word.lower()
    if len(w) <= 2:
        return w
    w = _step1(w)
    w = _step2(w)
    w = _step3(w)
    w = _step4(w)
    w = _step5(w)
    return w


def tokens_for_index(text: str) -> list[str]:
    """Indexed/query representation: stemmed tokens."""
    return [stem(t) for t in tokenize(text)]


# ---- Porter internals --------------------------------------------------------

_VOWELS = "aeiou"


def _cons(w: str, i: int) -> bool:
    c = w[i]
    if c in _VOWELS:
        return False
    if c == "y":
        return i == 0 or not _cons(w, i - 1)
    return True


def _m(w: str) -> int:
    n = len(w)
    i = 0
    while i < n and _cons(w, i):
        i += 1
    vc = 0
    while i < n:
        while i < n and not _cons(w, i):
            i += 1
        if i >= n:
            break
        vc += 1
        while i < n and _cons(w, i):
            i += 1
    return vc


def _has_vowel(stem_: str) -> bool:
    return any(not _cons(stem_, i) for i in range(len(stem_)))


def _ends_double_cons(w: str) -> bool:
    return len(w) >= 2 and w[-1] == w[-2] and _cons(w, len(w) - 1)


def _cvc(w: str) -> bool:
    if len(w) < 3:
        return False
    if _cons(w, len(w) - 3) and not _cons(w, len(w) - 2) and _cons(w, len(w) - 1):
        return w[-1] not in "wxy"
    return False


def _step1(w: str) -> str:
    if w.endswith("sses"):
        w = w[:-2]
    elif w.endswith("ies"):
        w = w[:-2]
    elif w.endswith("ss"):
        pass
    elif w.endswith("s"):
        w = w[:-1]
    flag = False
    if w.endswith("eed"):
        if _m(w[:-3]) > 0:
            w = w[:-1]
    elif w.endswith("ed"):
        if _has_vowel(w[:-2]):
            w = w[:-2]
            flag = True
    elif w.endswith("ing"):
        if _has_vowel(w[:-3]):
            w = w[:-3]
            flag = True
    if flag:
        if w.endswith(("at", "bl", "iz")):
            w += "e"
        elif _ends_double_cons(w) and not w.endswith(("l", "s", "z")):
            w = w[:-1]
        elif _m(w) == 1 and _cvc(w):
            w += "e"
    if w.endswith("y") and _has_vowel(w[:-1]):
        w = w[:-1] + "i"
    return w


_MAP2 = {
    "ational": "ate", "tional": "tion", "enci": "ence", "anci": "ance",
    "izer": "ize", "bli": "ble",  # DEPARTURE from paper (bli->ble per official later fix)
    "alli": "al", "entli": "ent", "eli": "e", "ousli": "ous",
    "ization": "ize", "ation": "ate", "ator": "ate", "alism": "al", "iveness": "ive",
    "fulness": "ful", "ousness": "ous", "aliti": "al", "iviti": "ive",
    "biliti": "ble", "logi": "log",  # later addition
}


def _step2(w: str) -> str:
    for suf, rep in _MAP2.items():
        if w.endswith(suf):
            stem_ = w[: -len(suf)]
            if _m(stem_) > 0:
                return stem_ + rep
            return w
    return w


_MAP3 = {
    "icate": "ic", "ative": "", "alize": "al", "iciti": "ic",
    "ical": "ic", "ful": "", "ness": "",
}


def _step3(w: str) -> str:
    for suf, rep in _MAP3.items():
        if w.endswith(suf):
            stem_ = w[: -len(suf)]
            if _m(stem_) > 0:
                return stem_ + rep
            return w
    return w


_MAP4 = {
    "al": "", "ance": "", "ence": "", "er": "", "ic": "", "able": "", "ible": "",
    "ant": "", "ement": "", "ment": "", "ent": "",
    "ion": None,   # special: only when stem ends s or t
    "ou": "", "ism": "", "ate": "", "iti": "", "ous": "", "ive": "", "ize": "",
}


def _step4(w: str) -> str:
    for suf, rep in _MAP4.items():
        if w.endswith(suf):
            stem_ = w[: -len(suf)]
            if suf == "ion":
                if stem_.endswith(("s", "t")) and _m(stem_) > 1:
                    return stem_
                return w
            if _m(stem_) > 1:
                return stem_ + rep
            return w
    return w


def _step5(w: str) -> str:
    if w.endswith("e"):
        stem_ = w[:-1]
        m = _m(stem_)
        if m > 1 or (m == 1 and not _cvc(stem_)):
            w = stem_
    if _m(w) > 1 and _ends_double_cons(w) and w.endswith("l"):
        w = w[:-1]
    return w


# ---- positional inverted index ----------------------------------------------

class EnrLexicalIndex:
    """Positional inverted index with BM25 scoring and exact phrase matching."""

    def __init__(self) -> None:
        # term -> {unit_idx: [positions]}
        self.postings: dict[str, dict[int, list[int]]] = defaultdict(dict)
        self.unit_len: list[int] = []
        self.n_units: int = 0
        self.avgdl: float = 0.0

    def add_unit(self, unit_idx: int, text: str) -> None:
        toks = tokens_for_index(text)
        self.unit_len.append(len(toks))  # assumes dense 0..N-1 insertion order
        for pos, t in enumerate(toks):
            self.postings[t].setdefault(unit_idx, []).append(pos)
        self.n_units += 1
        tot = sum(self.unit_len)
        self.avgdl = tot / max(1, len(self.unit_len))

    def finalize(self) -> None:
        self.avgdl = sum(self.unit_len) / max(1, len(self.unit_len))

    def df(self, term: str) -> int:
        return len(self.postings.get(term, ()))

    def idf(self, term: str) -> float:
        d = self.df(term)
        if d == 0:
            return 0.0
        n = len(self.unit_len)
        return math.log(1.0 + (n - d + 0.5) / (d + 0.5))

    def bm25(self, query_text: str) -> np.ndarray:
        """BM25 scores over all units for a free-text query."""
        terms = tokens_for_index(query_text)
        scores = np.zeros(len(self.unit_len), dtype=np.float64)
        if not terms:
            return scores
        for t in terms:
            plist = self.postings.get(t)
            if not plist:
                continue
            idf = self.idf(t)
            for uidx, positions in plist.items():
                tf = len(positions)
                dl = self.unit_len[uidx]
                denom = tf + K1 * (1.0 - B + B * dl / max(1e-9, self.avgdl))
                scores[uidx] += idf * (tf * (K1 + 1.0)) / denom
        return scores

    def phrase_units(self, phrase: str) -> set[int]:
        """Units containing the exact token sequence of `phrase`."""
        toks = tokens_for_index(phrase)
        if not toks:
            return set()
        candidate_sets = []
        for t in toks:
            plist = self.postings.get(t)
            if not plist:
                return set()
            candidate_sets.append(set(plist.keys()))
        result: set[int] = set()
        for uidx in set.intersection(*candidate_sets):
            pos_lists = [self.postings[t][uidx] for t in toks]
            first_positions = set(pos_lists[0])
            for offset in range(1, len(toks)):
                shifted = {p - offset for p in pos_lists[offset]}
                first_positions &= shifted
                if not first_positions:
                    break
            if first_positions:
                result.add(uidx)
        return result

    def matched_terms(self, query_text: str, uidx: int) -> list[str]:
        """Surface query words whose stems occur in unit `uidx` (for reasons)."""
        out = []
        seen: set[str] = set()
        for w in tokenize(query_text):
            st = stem(w)
            if st in seen:
                continue
            seen.add(st)
            if uidx in self.postings.get(st, {}):
                out.append(w)
        return out
