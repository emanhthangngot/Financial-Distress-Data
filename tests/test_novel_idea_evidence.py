from scripts.export_novel_idea_evidence import run_probes


def test_novel_idea_probes_include_working_negative_controls():
    report = run_probes("novel-test")

    assert report["status"] == "pass"
    assert report["evidence_manifest"]["tamper_detected"] is True
    assert report["pit_leakage_guard"]["selected_feature"] == "past"
    assert report["pit_leakage_guard"]["injected_future_snapshot_rejected"] is True
