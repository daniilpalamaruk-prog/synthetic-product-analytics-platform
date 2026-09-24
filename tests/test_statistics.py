from analysis.experiment_analysis import holm_adjust, srm_test, two_proportion


def test_two_proportion_detects_large_uplift():
    result = two_proportion(100, 1000, 160, 1000)
    assert result["absolute_uplift"] == 0.06
    assert result["p_value"] < 0.01
    assert result["ci_95_absolute"][0] > 0


def test_holm_is_monotonic_and_bounded():
    result = holm_adjust([("a", 0.001), ("b", 0.02), ("c", 0.8)])
    assert 0 <= result["a"] <= result["b"] <= result["c"] <= 1


def test_srm_detects_material_allocation_mismatch():
    balanced = srm_test({"control": 500, "treatment": 500}, {"control": 0.5, "treatment": 0.5})
    mismatched = srm_test({"control": 700, "treatment": 300}, {"control": 0.5, "treatment": 0.5})
    assert not balanced["srm_detected"]
    assert mismatched["srm_detected"]
