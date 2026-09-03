from types import SimpleNamespace

from fvkbench import config, doctor


def test_codex_version_and_auth_checks(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(argv, **kwargs):
        if argv[-2:] == ["login", "status"]:
            return SimpleNamespace(
                returncode=0, stdout="Logged in using ChatGPT\n", stderr=""
            )
        if argv[-1] == "--version":
            return SimpleNamespace(
                returncode=0,
                stdout=f"codex-cli {config.TESTED_CODEX_VERSION}\n",
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(doctor.subprocess, "run", fake_run)
    checks = {
        name: (verdict, detail)
        for name, verdict, detail in doctor.run_checks(eval_checks=False)
    }
    assert checks["codex"][0] is True
    assert checks["codex_auth"] == (True, "Logged in using ChatGPT")


def test_untested_codex_version_warns(monkeypatch):
    monkeypatch.setattr(doctor.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(
        doctor.subprocess,
        "run",
        lambda argv, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="Logged in using ChatGPT\n"
            if argv[-2:] == ["login", "status"]
            else "codex-cli 9.9.9\n",
            stderr="",
        ),
    )
    checks = {name: verdict for name, verdict, _ in doctor.run_checks(eval_checks=False)}
    assert checks["codex"] is None
