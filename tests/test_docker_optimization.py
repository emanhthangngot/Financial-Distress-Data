from scripts.export_docker_optimization import comparison


def test_docker_comparison_requires_and_reports_real_reduction():
    report = comparison(1000, 700)

    assert report["status"] == "pass"
    assert report["saved_bytes"] == 300
    assert report["reduction_percent"] == 30.0
    assert comparison(1000, 1000)["status"] == "fail"
