from pathlib import Path

from saasgen.config import GeneratorConfig
from saasgen.generator import _onboarding_d30_effect


def test_onboarding_d30_effect_does_not_leak_to_notification_treatment(tmp_path: Path):
    config = GeneratorConfig(10, 100, 42, tmp_path,
                             model={"experiments": {"onboarding": {"d30_effect": 0.5}}})
    onboarding = {"experiment_id": "exp_onboarding_v2", "variant": "treatment"}
    notification = {"experiment_id": "exp_notifications", "variant": "treatment"}
    assert _onboarding_d30_effect(onboarding, config) == 0.5
    assert _onboarding_d30_effect(notification, config) == 0.0
