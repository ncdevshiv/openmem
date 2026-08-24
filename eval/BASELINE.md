# Retrieval-Quality Baseline — OpenMem Phase 3

First measured baseline of the golden retrieval eval. This file is the
reference for every threshold asserted by `tests/test_retrieval_gate.py`.

## Measurement environment

- **Date**: 2026-08-22
- **Interpreter**: F:\openmem\.venv\Scripts\python.exe (Python 3.12.14)
- **Storage**: lancedb 0.37.1 / pyarrow 25, fixed-size vector schema
- **Retrieval mode at measurement time**: `keyword-fallback`
  (sentence-transformers NOT installed → `VectorDB.search()` routes to
  `_keyword_search`: case-insensitive per-term substring OR-match, score =
  fraction of distinct query terms matched, ranked by distinct-term hits
  then total term frequency, stable sort over insertion order)
- **Reranker**: not installed (`BAAI/bge-reranker-*` unavailable), no GPU
- **Corpus**: hermetic, deterministic — 36 fixtures across 6 topics
  (deepseek harness port, nc-code repo, retrieval internals, plus
  gardening/baking/travel distractors), explicit `golden-*` ids, built in a
  TEMP LanceDB via the standard constructor; live `data/lancedb` untouched.
- **Queries**: `eval/golden_queries.json` v1.0.0 — 16 queries: 6 exact-term,
  6 paraphrase, 4 negative/distractor.

## Measured results (verbatim from first run)

```
### OpenMem Retrieval Eval - mode: keyword-fallback

- golden queries v1.0.0 | corpus v1.0.0 (36 fixtures)
- embedder available: False | reranker installed: False, loaded: False | gpu: False

| class | queries | recall@5 | MRR | nDCG@5 | fallout@5 |
|---|---:|---:|---:|---:|---:|
| exact_term | 6 | 0.972 | 1.000 | 1.000 | 0.333 |
| paraphrase | 6 | 1.000 | 0.889 | 0.917 | 0.300 |
| negative (any-hit 0.000) | 4 | 0.000 | 0.000 | 0.000 | 0.000 |
| **aggregate** | 16 | 0.740 | 0.708 | 0.719 | 0.237 |
```

Metric conventions are defined in `memory_store/retrieval_metrics.py`.
Negative-class recall/MRR/nDCG are trivially 0.0 because no relevant docs
exist for those queries; `fallout@5` (mean share of the top-5 window that
is non-relevant) and any-hit rate are the numbers that matter there.

## Re-measurement 2026-08-24 — weighted keyword search (current)

`_keyword_search` was rewritten to target the three levers listed in the
findings below: word-boundary matching with light suffix expansion
(`port` → matches *ported*, refuses *report*/*passport*), IDF-style term
weighting (rare terms outweigh common ones), and an importance tie-break
after hits/frequency before the stable insertion-order fallback. Score is
now IDF-weighted coverage instead of distinct-term fraction. Same
environment otherwise; still `keyword-fallback` mode, no embedder.

```
### OpenMem Retrieval Eval - mode: keyword-fallback

- golden queries v1.0.0 | corpus v1.0.0 (36 fixtures)
- embedder available: False | reranker installed: False, loaded: False | gpu: False

| class | queries | recall@5 | MRR | nDCG@5 | fallout@5 |
|---|---:|---:|---:|---:|---:|
| exact_term | 6 | 0.972 | 1.000 | 1.000 | 0.333 |
| paraphrase | 6 | 1.000 | 1.000 | 1.000 | 0.300 |
| negative (any-hit 0.000) | 4 | 0.000 | 0.000 | 0.000 | 0.000 |
| **aggregate** | 16 | 0.740 | 0.750 | 0.750 | 0.237 |
```

Movement vs first run, with cause:

- paraphrase MRR 0.889 → **1.000**, nDCG 0.917 → **1.000**: pa-06's
  single-shared-term losses ('keep' ⊂ "OpenMem keeps…") are gone — IDF now
  lets 'travel'/'documents'/'dry' dominate 'keep'.
- aggregate MRR 0.708 → **0.750**, nDCG 0.719 → **0.750**.
- exact_term unchanged, including fallout 0.333: ex-02's window fillers are
  genuine word-boundary matches from the same topic cluster (other harness
  fixtures), i.e. judgment tightness, not matcher noise. Morphology fixes
  cannot and should not remove them.
- negatives stay strict-zero (runner enforces substring-disjoint terms).

Threshold changes in the table below: paraphrase MRR floor 0.75 → **0.90**
(observed 1.000), paraphrase nDCG floor 0.80 → **0.90** (observed 1.000),
aggregate MRR floor 0.60 → **0.65** (observed 0.750), aggregate nDCG floor
0.62 → **0.65** (observed 0.750). All re-tightened to −10…−13% slack under
the new observed values; no ceilings moved (no fallout change).

## Re-measurement 2026-08-24 — vector mode (ml extra landed)

Later on 2026-08-24 the `ml` extra was installed into the project venv
(uv; torch CPU + sentence-transformers + transformers). This flipped the
served retrieval mode to `vector` and surfaced two real defects:

1. **Reranker config bug**: config.json `memory.reranker_model: "auto"`
   was passed verbatim to `CrossEncoder`, 401-ing against
   `huggingface.co/cross-encoder/auto`. Fixed: `"auto"`/empty are treated
   as selection directives. With the fix the CPU reranker
   (`BAAI/bge-reranker-base`) actually loads, and since `force_rerank`
   defaults True it now participates in every vector-path search.
2. **Eval harness bug (all-zero vector report)**: `build_golden_corpus`
   hardcoded `auto_embed=False`, leaving every fixture's vector NULL.
   Keyword fallback still matched raw text, but vector search over NULL
   vectors returns nothing — the first "vector" run scored 0.000 on every
   metric while honestly reporting mode `vector`. Fixed: fixtures are
   embedded exactly when the store has an embedder.

```
### OpenMem Retrieval Eval - mode: vector

- golden queries v1.0.0 | corpus v1.0.0 (36 fixtures)
- embedder available: True | reranker installed: True, loaded: True | gpu: False

| class | queries | recall@5 | MRR | nDCG@5 | fallout@5 |
|---|---:|---:|---:|---:|---:|
| exact_term | 6 | 0.972 | 1.000 | 1.000 | 0.633 |
| paraphrase | 6 | 0.917 | 0.875 | 0.841 | 0.800 |
| negative (any-hit 1.000) | 4 | 0.000 | 0.000 | 0.000 | 1.000 |
| **aggregate** | 16 | 0.708 | 0.703 | 0.690 | 0.787 |
```

Interpretation:

- Positives are comparable to the weighted keyword path: exact_term is
  identical (0.972 / 1.000 / 1.000); paraphrase is slightly below keyword's
  perfect post-fix scores (one paraphrase query misses its golden doc).
  On a 36-doc corpus with heavy lexical overlap between queries and golden
  text, IDF-weighted keyword matching remains very strong.
- **Negatives are structurally non-silent under vector retrieval**
  (any-hit 1.000): nearest-neighbour search always fills the window, and
  substring-disjointness of negative terms — the property that made
  strict-zero enforceable — has no semantic analogue. The gate therefore
  skips negative-class assertions in vector mode (keyword-mode assertions
  unchanged); a semantic replacement metric is future work.
- Vector fallout ceilings look high because 30 of 36 corpus docs are
  distractors and every query retrieves a full window of nearest items;
  ceilings sit +20% over observed like everywhere else.

Gate thresholds are now keyed by retrieval mode (`tests/test_retrieval_gate.py::THRESHOLDS`);
the vector set below was measured once and calibrated −10…−20% like the
keyword sets.

| Gate assertion (vector) | Observed | Threshold |
|---|---:|---:|
| exact_term recall@5 ≥ | 0.972 | **0.87** |
| exact_term MRR ≥ | 1.000 | **0.90** |
| exact_term nDCG@5 ≥ | 1.000 | **0.90** |
| exact_term fallout@5 ≤ | 0.633 | **0.76** |
| paraphrase recall@5 ≥ | 0.917 | **0.82** |
| paraphrase MRR ≥ | 0.875 | **0.75** |
| paraphrase nDCG@5 ≥ | 0.841 | **0.74** |
| paraphrase fallout@5 ≤ | 0.800 | **0.96** |
| negative class | — | skipped (mode semantics, see above) |
| aggregate recall@5 ≥ | 0.708 | **0.63** |
| aggregate MRR ≥ | 0.703 | **0.62** |
| aggregate nDCG@5 ≥ | 0.690 | **0.61** |
| aggregate fallout@5 ≤ | 0.787 | **0.94** |

## Re-measurement 2026-08-24 — ENR BM25 keyword search (current)

`_keyword_search` was rewritten again, vendoring the lexical layer of
[ENR](https://github.com/ncdevshiv/nc-nir) (`memory_store/enr_lexical.py`, MIT):
full Porter stemming on index and query side (all inflections, replacing the
five-suffix boundary regex), BM25 scoring with tf-saturation and document-length
normalization (k1=1.2, b=0.75), a Lucene-style coord factor (coverage of distinct
query terms — one rare term in a short doc no longer crowds out broad-coverage
evidence), positional exact-phrase detection for quoted spans, a cached positional
inverted index invalidated on every mutation, and per-result `score_details`
(matched words, raw BM25, term coverage, phrase hits) so ranking is explainable.
Same environment otherwise; still `keyword-fallback` mode.

```
### OpenMem Retrieval Eval - mode: keyword-fallback

- golden queries v1.0.0 | corpus v1.0.0 (36 fixtures)
- embedder available: False | reranker installed: True, loaded: True | gpu: False

| class | queries | recall@5 | MRR | nDCG@5 | fallout@5 |
|---|---:|---:|---:|---:|---:|
| exact_term | 6 | 0.972 | 1.000 | 1.000 | 0.433 |
| paraphrase | 6 | 1.000 | 1.000 | 1.000 | 0.267 |
| negative (any-hit 0.000) | 4 | 0.000 | 0.000 | 0.000 | 0.000 |
| **aggregate** | 16 | 0.740 | 0.750 | 0.750 | 0.263 |
```

Movement vs the weighted-keyword rewrite, with cause:

- All ranking metrics are UNCHANGED (recall/MRR/nDCG identical in every class) —
  the golden set was already saturated at 0.75 aggregate by the previous rewrite.
- Paraphrase fallout improved 0.300 → **0.267** (coord demotes single-term
  window fillers).
- Exact_term fallout rose 0.333 → **0.433**, entirely window-composition:
  BM25's length normalization surfaces same-topic single-term harness fixtures
  more often inside ex-02's top-5 (its golden doc matches all five query terms
  and stays rank 1; fillers now carry visibly separated scores ≤0.095 after
  coord). Judgment tightness, not matcher noise — same classification as the
  first baseline's note on ex-02. Gate ceiling moved 0.40 → **0.52** (+20%
  over observed), justification recorded here per protocol; paraphrase fallout
  ceiling tightened is NOT needed (0.267 < 0.36 existing).
- Negatives stay strict-zero under the new path.

New capabilities this rewrite brings that the golden set does not yet measure
(future query-class candidates): full-stemming morphology ("cancel" ↔
"cancelled"/"cancellation"), quoted-phrase constraints, score explanations via
`score_details`, and an O(1)-per-mutation cached index instead of a full-table
Arrow scan per search.

## Chosen gate thresholds and rationale

The corpus, ids, contents, and ranking path are fully deterministic
(stable sort over per-term hit counts; no embedder, no network), so an
unchanged system reproduces these numbers exactly. Thresholds therefore do
NOT budget statistical noise — they exist to trip when *ranking semantics*
drift (scoring formula changes, sort-order changes, schema/search rewrites,
a future vector-mode switch). Floors are set ~10–20% below observed;
fallout ceilings ~10–20% above observed; negatives stay strict-zero
because the runner validates negative-query terms as substring-disjoint
from the corpus at runtime, making silence enforceable rather than lucky.

| Gate assertion | Observed | Threshold | Slack |
|---|---:|---:|---|
| exact_term recall@5 ≥ | 0.972 | **0.87** | −10% |
| exact_term MRR ≥ | 1.000 | **0.95** | −5% |
| exact_term nDCG@5 ≥ | 1.000 | **0.90** | −10% |
| exact_term fallout@5 ≤ | 0.333 | **0.40** | +20% |
| paraphrase recall@5 ≥ | 1.000 | **0.90** | −10% |
| paraphrase MRR ≥ | 1.000 | **0.90** | −10% |
| paraphrase nDCG@5 ≥ | 1.000 | **0.90** | −10% |
| paraphrase fallout@5 ≤ | 0.300 | **0.36** | +20% |
| negative any-hit rate ≤ | 0.000 | **0.00** | strict |
| negative fallout@5 ≤ | 0.000 | **0.02** | strict |
| aggregate recall@5 ≥ | 0.740 | **0.65** | −12% |
| aggregate MRR ≥ | 0.750 | **0.65** | −13% |
| aggregate nDCG@5 ≥ | 0.750 | **0.65** | −13% |
| aggregate fallout@5 ≤ | 0.237 | **0.28** | +18% |

Notes on interpretation:

- exact_term recall@5 is structurally capped below 1.0: query ex-01 judges
  all six harness fixtures relevant, so its ceiling is 5/6 ≈ 0.833.
- aggregate recall/MRR average across ALL queries including negatives,
  whose recall/MRR are honest zeros by construction.
- Positive-class fallout > 0 is expected: tight relevance judgments mean
  topically-correct-but-not-judged docs count as false discoveries within
  the window.

## Reproduce

```bash
python main.py eval                       # writes data/eval/latest.json
python -m eval.run_eval --report out.json # same thing, library entry too
python -m unittest tests.test_retrieval_gate -v   # regression gate
```

## Search quirks exposed by the first run (findings — status after 2026-08-24 rewrite)

1. **Substring morphological collisions** drive real fallout:
   - `'port'` matches *Ported* AND *re**port***, *im**portance***,
     *pass**port***, *Air**port*** (pa-01 pulls travel/harness docs).
   - `'repo'` matches *report* — nc-code query ex-03 surfaced a DeepSeek
     harness doc ("…jobs that **report** job ids") inside its top-5.
   - STATUS: **fixed** for embedded coincidences — boundary matching with
     suffix expansion still admits *ported* but refuses *report*/…
     (residual exact fallout is same-topic, legitimately matching docs).
2. **Polysemy across domains**: `'scoring'` matches bread-scoring
   (`golden-bak-05`) just like search-scoring (`golden-ret-02`); ex-05's
   runner-up is literally about crust.
   - STATUS: **mitigated, not solved** — IDF down-weights terms shared
     across domains, but only embeddings/reranking can read meaning.
3. **Tie-breaks are insertion order**: single-shared-term paraphrase pa-06
   ("keep travel documents dry") loses to earlier-inserted docs matching
   only one equally-weighted term ('keep' ⊂ "OpenMem keeps…", "keep cane
   borers away"), dropping MRR to 0.333 for that query — term frequency
   tie-break only fires after distinct-hit counts, which are equal (1 vs 1).
   - STATUS: **fixed** — IDF weighting makes 'travel'/'documents'/'dry'
     outweigh 'keep'; pa-06 now ranks its golden doc first.
4. **Frequency tie-break favors repetition**: ex-01 ranks `golden-dsh-06`
   first purely because it repeats 'harness' twice.
   - STATUS: unchanged and harmless (all five ranked docs are relevant;
     order within the window doesn't move MRR/nDCG here).
5. Any future reranker/embedder work should target exactly these three
   levers: morphology-aware matching, IDF-style term weighting, and a
   semantic tie-break.
   - STATUS: levers 1–2 landed in `_keyword_search` on 2026-08-24; a true
     semantic tie-break still awaits the embedder/reranker path.

When a deliberate retrieval improvement lands here, re-measure
(`python main.py eval`), update the table above, and tighten or loosen the
gate thresholds with a one-line justification each — never silently.
