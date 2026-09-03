import argparse

from fvk_bench import cli, config


def test_parser_exposes_only_verified500_codex_workflow():
    parser = cli.build_parser()
    help_text = parser.format_help()
    assert "regression-full" not in help_text
    assert "baseline/FVK" in help_text
    args = parser.parse_args(["run", "--all"])
    assert args.instance_set == "verified500"
    assert args.arms == "baseline,fvk"
    assert not hasattr(args, "agent")
    assert not hasattr(args, "claude_bin")


def test_parse_arms_rejects_removed_control(capsys):
    assert cli._parse_arms("baseline,fvk") == config.ARMS
    assert cli._parse_arms("control") is None
    assert "unknown arms" in capsys.readouterr().out


def test_resolve_verified_batch():
    known = {f"repo__repo-{index:03d}": object() for index in range(500)}
    args = argparse.Namespace(all=False, batch="verified050", instances=[])
    selected = cli._resolve_selection(args, known)
    assert selected == [f"repo__repo-{index:03d}" for index in range(490, 500)]
