import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    matrix = json.loads((ROOT / "results/candidate_matrix.json").read_text())
    both = [
        row
        for row in matrix["candidates"]
        if row["category"] == "both_resolved"
    ]
    different = {
        row["instance_id"]
        for row in both
        if (ROOT / row["baseline_patch"]).read_bytes()
        != (ROOT / row["fvk_patch"]).read_bytes()
    }
    analysis_dir = ROOT / "verified500_fvk_baseline_buggy"
    substantive = {
        path.stem for path in analysis_dir.glob("*.md") if path.name != "README.md"
    }
    severity = Counter()
    for instance_id in substantive:
        text = (analysis_dir / f"{instance_id}.md").read_text()
        matches = [
            level
            for level in ("High", "Medium", "Low")
            if f"**Severity:** {level}" in text
        ]
        if len(matches) != 1:
            raise ValueError(f"expected one severity label for {instance_id}")
        severity[matches[0]] += 1

    summary = matrix["summary"]
    if len(both) != summary["both_resolved"]:
        raise ValueError("candidate matrix both-resolved count does not match summary")
    if not substantive <= different:
        raise ValueError("substantive cases must be drawn from the 86 rewrites")
    if sum(severity.values()) != len(substantive):
        raise ValueError("severity counts do not cover every substantive case")

    print("Verified500 published analysis")
    print(f"  baseline resolved: {summary['baseline_resolved']}/500")
    print(f"  FVK resolved:      {summary['fvk_resolved']}/500")
    print(f"  both resolved:     {summary['both_resolved']}/500")
    print(f"  different patches: {len(different)}")
    print(f"  substantive:       {len(substantive)}")
    print(f"  excluded:          {len(different - substantive)}")
    print(
        "  severity:          "
        f"{severity['High']} high, "
        f"{severity['Medium']} medium, "
        f"{severity['Low']} low"
    )


if __name__ == "__main__":
    main()
