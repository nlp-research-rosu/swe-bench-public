# Formal-methods knowledge raises the review standard after tests pass

## Result

The experiment ran Codex twice on each of the 500 SWE-bench Verified
instances. The baseline session solved the issue normally. The FVK session
resumed the baseline context, received general formal-methods, semantics, and
verification guidance, and reviewed the baseline solution.

The official SWE-bench harness produced:

| Outcome | Count |
|---|---:|
| Baseline resolved | 407/500 |
| FVK resolved | 413/500 |
| Both resolved | 405/500 |
| FVK only | 8 |
| Baseline only | 2 |
| Neither | 85 |

Within the 405 instances that both versions resolved, 319 patches were
identical and 86 were different. Those 86 are the review population: FVK chose
to rewrite code that already had a positive official verdict.

## Review of the 86 rewrites

Every different patch is not automatically an improvement. The 86 cases were
reviewed individually and divided into:

| Review outcome | Count |
|---|---:|
| Substantive FVK improvement | 60 |
| Excluded: equivalent, cosmetic, or insufficiently supported | 26 |

The 60 retained cases have a defensible issue in the baseline patch, such as an
untested boundary, an incomplete sibling code path, a backward-compatibility
break, a wrong result, or a valid-input crash. Their publication-facing
articles and artifact links are indexed in
[analysis](../README.md).

Five retained cases were conservatively judged more correct than the merged
human fix. This does not mean the human patch failed SWE-bench: it means the
FVK version covered a real behavior that neither the official tests nor the
merged patch covered.

## What is and is not claimed

- Passing the official tests means an arm resolved the SWE-bench instance.
- “Different” means the two passing patches are not byte-identical.
- “Substantive” is a post-hoc correctness judgment backed by per-case artifacts;
  it is not another official SWE-bench metric.
- The missed behavior belongs to the limits of the official test coverage, not
  to a custom failure criterion introduced by this experiment.
- The FVK arm used formal-methods knowledge without calling a proof tool.
  Proof-shaped reasoning should not be described as a machine-checked proof.

## Reproducibility map

- Canonical runs and official scores:
  [results/INDEX.md](../../results/INDEX.md)
- Canonical selection matrix:
  [results/candidate_matrix.json](../../results/candidate_matrix.json)
- Primary 60-case analysis:
  [analysis/README.md](../README.md)
- Twenty-one deeper supporting analyses:
  [SUMMARY_TABLE.md](SUMMARY_TABLE.md)
- Three executable enhanced tests:
  [ENHANCED_TESTS.md](ENHANCED_TESTS.md)
