# Formal-Methods Review of SWE-bench Verified

This repository contains the artifacts and runner for an experiment over all
500 instances in SWE-bench Verified. The experiment asks a narrow question:

> Does general knowledge of formal methods help an LLM find defects in code
> that already passes the benchmark's official tests?

For each instance, Codex first solved the public issue normally. We then
resumed the frozen baseline session, supplied general guidance about formal
methods, semantics, and verification through the Formal Verification Kit
(FVK), and asked the model to review its own patch and rewrite it only when
needed. The baseline and FVK patches were evaluated independently by the
official SWE-bench harness.

The model was not given hidden test names or contents, and the FVK arm did not
call a proof tool.

> This is an experiment repository built on
> [SWE-bench](https://github.com/SWE-bench/SWE-bench). For the benchmark itself,
> its datasets, and general evaluation documentation, use the upstream project.

## Results at a glance

| Outcome | Count |
|---|---:|
| Baseline resolved by the official harness | 407/500 |
| FVK resolved by the official harness | 413/500 |
| Both resolved | 405/500 |
| FVK only | 8 |
| Baseline only | 2 |
| Both resolved with identical patches | 319 |
| Both resolved with different patches | 86 |
| Different-patch cases judged substantively better after FVK review | 60 |
| Different-patch cases excluded from that claim | 26 |

The 86 cases are a mechanical selection: both patches passed the official
evaluation, but their contents differed. A changed patch is not automatically
better. We reviewed all 86 cases individually and retained 60 where the FVK
rewrite addressed a defensible correctness, completeness, boundary, or
robustness issue that the official tests did not distinguish.

Five of the retained cases were conservatively judged more correct than the
merged human fix. This is not a claim that the human fixes failed SWE-bench;
it means the FVK patch covered a real behavior that neither the official tests
nor the merged patch covered.

## Explore the evidence

| Start here | What it contains |
|---|---|
| [Primary 60-case analysis](verified500_fvk_baseline_buggy/README.md) | Publication-facing case articles, grouped by severity, with links to patches, prompts, findings, proof artifacts, and verification evidence. |
| [Three executable regression tests](verified500_analysis/ENHANCED_TESTS.md) | New tests that fail on the baseline patch and pass on the FVK patch; two also fail on the merged human fix. |
| [Supporting 21-case analysis](verified500_analysis/README.md) | Fifteen deeper positive cases and six negative controls showing why not every rewrite was counted. |
| [Canonical results index](results/INDEX.md) | The 50 canonical 10-instance runs and their baseline/FVK official scores. |
| [Candidate matrix](results/candidate_matrix.json) | Machine-readable canonical-run selection and per-instance official verdicts. |
| [Experiment procedure](START.md) | Environment checks, instance selection, model runs, official evaluation, and report generation. |

A useful concrete starting point is
[`pydata__xarray-4094`](verified500_fvk_baseline_buggy/pydata__xarray-4094.md).
Its article links the baseline, FVK, and human patches to a regression test and
the saved official-harness reports for all three variants.

## Reproduce the published analysis

There are three different levels of reproduction. They have different cost and
different determinism.

### 1. Verify the published accounting from saved artifacts

This check uses only Python's standard library. It recomputes the 86 changed
patches, verifies that all 60 retained articles belong to that population, and
recounts the severity labels. It does not repeat the qualitative case review;
the reasoning and evidence for those judgments live in the 60 case articles.

```bash
python - <<'PY'
import json
from collections import Counter
from pathlib import Path

matrix = json.loads(Path("results/candidate_matrix.json").read_text())
both = [
    row for row in matrix["candidates"]
    if row["category"] == "both_resolved"
]
different = {
    row["instance_id"]
    for row in both
    if Path(row["baseline_patch"]).read_bytes()
    != Path(row["fvk_patch"]).read_bytes()
}
articles = {
    path.stem
    for path in Path("verified500_fvk_baseline_buggy").glob("*.md")
    if path.name != "README.md"
}
severity = Counter()
for instance_id in articles:
    text = (
        Path("verified500_fvk_baseline_buggy") / f"{instance_id}.md"
    ).read_text()
    for level in ("High", "Medium", "Low"):
        if f"**Severity:** {level}" in text:
            severity[level] += 1
            break

assert articles <= different
print(matrix["summary"])
print({"both_passed_different_patch": len(different)})
print({"substantive": len(articles), "excluded": len(different - articles)})
print({"severity": dict(severity)})
PY
```

Expected key values are `407` baseline resolved, `413` FVK resolved, `405`
both resolved, `86` different passing patches, `60` retained cases, and `26`
excluded cases. The retained cases comprise 9 high-, 21 medium-, and 30
low-severity findings.

### 2. Inspect or rerun the added regression tests

The three strongest behavioral demonstrations are documented in
[`verified500_analysis/ENHANCED_TESTS.md`](verified500_analysis/ENHANCED_TESTS.md).
The test sources and official-harness `report.json` files are checked in under
each instance's `enhanced_tests/` directory, so the red/green results can be
inspected without Docker.

Rerunning them requires Docker and the standard SWE-bench evaluation images.
The enhanced-tests document explains how each one-row dataset and prediction
file is constructed and gives the harness invocation. At present this is a
documented recipe, not a single wrapper command.

### 3. Rerun the model experiment and official evaluation

See [`START.md`](START.md) for the runner workflow. A full run requires Python
3.10+, Git, Docker, an authenticated Codex CLI, substantial disk space, and an
FVK checkout. Model generation is nondeterministic: this reproduces the method,
not necessarily byte-identical patches.

The saved artifacts remain the source of truth for the published run. Each run
records its model configuration, host, prompts, patch hashes, session metadata,
FVK revision, and copied evaluator reports.

## FVK version note

The canonical manifests record two historical FVK revisions:

- 47 of the 50 runs used
  [`fef0123cd40a0205c03751ab42126c03b9a2c6ad`](https://github.com/grosu/formal-verification-kit/commit/fef0123cd40a0205c03751ab42126c03b9a2c6ad),
  which is recoverable from the public
  [Formal Verification Kit repository](https://github.com/grosu/formal-verification-kit).
- `verified018`, `verified019`, and `verified020` used
  `25a33f4e0002ede9074f86b12156d46b2fd7ec67`. That exact source revision is not
  currently available from the public repository; the prompts, generated FVK
  artifacts, patches, and evaluator outputs for those runs are preserved here.

The current public FVK repository uses the original repository-style layout,
while this benchmark runner expects a later packaged-skill installer layout.
Consequently, artifact inspection and accounting are self-contained, but a
fresh clean-room model rerun still requires reconstructing that historical
installation step.

## Claim boundaries

- “Resolved” means resolved by the official SWE-bench harness.
- “Different” means the two resolved patches are not byte-identical.
- “Substantive improvement” is a post-hoc, case-by-case correctness judgment,
  not an official SWE-bench metric.
- The missed behaviors expose limits in the official test coverage; they do
  not redefine what counts as passing SWE-bench.
- FVK supplied knowledge and a review procedure. No external proof tool was
  called during the experiment.
- K and proof-shaped artifacts that were not machine-checked are described as
  proof-structured reasoning, not completed formal proofs.

## License and upstream attribution

This repository retains the upstream SWE-bench implementation and its MIT
license. See [`LICENSE`](LICENSE) and the
[upstream SWE-bench repository](https://github.com/SWE-bench/SWE-bench) for the
original benchmark project and citation information.
