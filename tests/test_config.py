from pathlib import Path

import pytest

from saasgen.config import GeneratorConfig


def test_config_rejects_too_short_history(tmp_path: Path):
    with pytest.raises(ValueError, match="months"):
        GeneratorConfig(100, 1000, 42, tmp_path, months=6).validate()


def test_config_rejects_invalid_margin(tmp_path: Path):
    with pytest.raises(ValueError, match="gross-margin"):
        GeneratorConfig(100, 1000, 42, tmp_path, gross_margin=0.5).validate()

