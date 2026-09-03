# Reproducing the Verified500 baseline/FVK experiment

This repository contains one experiment over all 500 instances in
SWE-bench Verified. Each instance has two sequential Codex sessions:

1. **baseline** solves the issue from the public problem statement;
2. **fvk** resumes the frozen baseline session, receives general formal-methods
   guidance through the Formal Verification Kit skill, reviews the baseline
   patch, and may rewrite it.

Both patches are scored independently by the official SWE-bench harness. The
agent is not given hidden test names or hidden test contents.

## Published artifacts

- [Results index](results/INDEX.md) lists the 50 canonical 10-instance runs and
  their official scores.
- [Candidate matrix](results/candidate_matrix.json) records the canonical-run
  selection and per-instance baseline/FVK verdicts.
- [Primary 60-case analysis](verified500_fvk_baseline_buggy/README.md) is the
  publication-facing evidence set.
- [Supporting analysis](verified500_analysis/README.md) contains executed
  reproductions and enhanced tests for selected cases.

The canonical aggregate is 407/500 baseline resolved and 413/500 FVK resolved.
Both arms resolved 405 instances. Among those, 86 had different patches. A
separate case-by-case review found a substantive correctness improvement in 60
of those 86 rewrites.

## Requirements

- Python 3.10 or newer
- Git
- Docker with roughly 120 GB free for official evaluation
- Codex CLI authenticated through a ChatGPT/Codex subscription
- the Formal Verification Kit checkout at
  `third_party/formal-verification-kit`

Create an environment and install the project:

~~~bash
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
~~~

Set an isolated workspace root if desired:

~~~bash
export FVK_BENCH_WORKSPACE=/absolute/path/to/swe-fvk-runs
~~~

## Preflight

Run the static checks:

~~~bash
.venv/bin/python -m fvk_bench doctor
~~~

Add `--canary` to launch one real Codex session and verify that its transcript
does not contain leaked MCP/plugin tools or command execution:

~~~bash
.venv/bin/python -m fvk_bench doctor --canary
~~~

## Inspect the instance set

~~~bash
.venv/bin/python -m fvk_bench list
.venv/bin/python -m fvk_bench list --batch verified001
~~~

The vendored public metadata lives at
`fvk_bench/data/instances_verified500.json`. Refreshing it requires the
Hugging Face `datasets` package:

~~~bash
.venv/bin/python -m fvk_bench vendor-instances
~~~

## Run one instance or batch

Validate the official gold patch before spending model time:

~~~bash
.venv/bin/python -m fvk_bench validate-gold \
  --run-id reproduction \
  --instances astropy__astropy-12907
~~~

Run both arms:

~~~bash
.venv/bin/python -m fvk_bench run \
  --run-id reproduction \
  --instances astropy__astropy-12907 \
  --arms baseline,fvk
~~~

Or run one canonical 10-instance batch:

~~~bash
.venv/bin/python -m fvk_bench run \
  --run-id verified001-local \
  --batch verified001 \
  --arms baseline,fvk \
  --max-parallel 3
~~~

Reusing a run id resumes it. Completed arms are skipped; failed arms run again
only with `--retry-failed`.

## Evaluate and report

~~~bash
.venv/bin/python -m fvk_bench evaluate \
  --run-id reproduction \
  --max-workers 4

.venv/bin/python -m fvk_bench report --run-id reproduction
~~~

The official evaluator writes per-arm reports under the run directory. The
report command derives `scores.json` and `scores.md` from harvested artifacts.

## Artifact layout

~~~text
results/<run-id>/
  run_manifest.json
  scores.json
  scores.md
  <instance-id>/
    manifest.json
    prompts/
    solutions/
    reports/
    fvk/
    transcripts/
    eval/
~~~

The baseline patch is V1. Before the FVK review, the runner reconstructs V1,
restores the frozen baseline transcript, installs the FVK skill, and records a
separate FVK patch. Session parameters, prompt hashes, git state, and transcript
audits are retained in the manifests.
