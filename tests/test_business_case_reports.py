from pathlib import Path

from analysis.business_cases import generate_reports


def test_business_cases_are_derived_from_dataset(analytical_dataset: Path, tmp_path: Path):
    reports = generate_reports(analytical_dataset, tmp_path / "cases")
    assert set(reports) == {"android_incident", "pricing", "acquisition"}
    assert "3.7.0" in reports["android_incident"]
    assert "new_pricing" in reports["pricing"]
    assert "tiktok" in reports["acquisition"]
    for name in reports:
        text = (tmp_path / "cases" / name / "report.md").read_text(encoding="utf-8")
        for section in ("Question", "Evidence", "Analysis", "Metric impact", "Interpretation", "Recommendation", "Limitations"):
            assert f"## {section}" in text
