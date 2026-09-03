import hashlib
import re

import pytest

from fvk_bench import config
from fvk_bench.prompting import render_prompt, template_hashes


@pytest.mark.parametrize("arm", config.ARMS)
def test_rendered_prompts_have_no_unexpanded_placeholders(arm, fixture_instance):
    rendered = render_prompt(arm, fixture_instance)
    assert fixture_instance.base_commit in rendered
    assert re.search(r"\{[a-z_]+\}", rendered) is None


def test_baseline_explicitly_forbids_fvk_method():
    text = (config.PROMPTS_DIR / "baseline.md").read_text(encoding="utf-8").lower()
    assert "do not use" in text
    assert "formal-verification-kit" in text
    assert "/formalize" in text


def test_template_hashes_cover_two_arms():
    hashes = template_hashes()
    assert set(hashes) == set(config.ARMS)
    for arm, digest in hashes.items():
        assert digest == hashlib.sha256(
            (config.PROMPTS_DIR / f"{arm}.md").read_bytes()
        ).hexdigest()


def test_unknown_arm_is_rejected(fixture_instance):
    with pytest.raises(KeyError):
        render_prompt("control", fixture_instance)
