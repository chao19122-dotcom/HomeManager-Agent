"""Opt-in paid integration, executes A-H assertions in scripts/evaluate.py."""
import pytest
from config import Settings


@pytest.mark.live
def test_real_deepseek_A_to_H(tmp_path):
    if not Settings.load().api_key:
        pytest.skip("缺少真实 DEEPSEEK_API_KEY，不能声明真实联调通过")
    from scripts.evaluate import evaluate
    report = evaluate(live=True, output_dir=tmp_path)
    assert report["failed"] == 0, report
