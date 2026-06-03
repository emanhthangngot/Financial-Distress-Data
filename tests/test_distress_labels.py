from src.transforms.compute_distress_labels import compute_distress_label, compute_labels

BASE_ROW = {
    "ticker": "AAA",
    "report_period": "2025Q4",
    "total_assets": 1000,
    "current_assets": 300,
    "current_liabilities": 200,
    "total_liabilities": 500,
    "equity": 500,
    "retained_earnings": 150,
    "ebit": 120,
    "interest_expense": 20,
    "net_income": 80,
    "event_timestamp": "2026-01-01",
    "created_ts": "2026-01-01T00:00:00+00:00",
}


def test_distress_label_safe_zone():
    label = compute_distress_label(BASE_ROW)
    assert label.z_score == 3.0014
    assert label.distress_label == 0
    assert "z_score_safe_zone" in label.distress_reason


def test_distress_label_warning_rules_can_trigger_distress():
    previous = {**BASE_ROW, "net_income": -10, "report_period": "2025Q3"}
    current = {
        **BASE_ROW,
        "total_liabilities": 900,
        "current_assets": 100,
        "current_liabilities": 250,
        "equity": -50,
        "ebit": 10,
        "net_income": -30,
    }
    label = compute_distress_label(current, previous)
    assert label.distress_label == 1
    assert "high_debt_to_asset" in label.distress_reason
    assert "negative_equity" in label.distress_reason


def test_null_z_score_with_insufficient_rules_returns_null_label():
    row = {**BASE_ROW, "retained_earnings": None}
    label = compute_distress_label(row)
    assert label.z_score is None
    assert label.distress_label is None
    assert "insufficient_data" in label.distress_reason


def test_two_quarter_net_loss_requires_consecutive_report_periods():
    labels = compute_labels(
        [
            {**BASE_ROW, "report_period": "2025Q1", "net_income": -10},
            {**BASE_ROW, "report_period": "2025Q3", "net_income": -20},
        ]
    )

    assert "two_quarter_net_loss" not in labels[1]["distress_reason"]


def test_two_quarter_net_loss_triggers_for_consecutive_report_periods():
    labels = compute_labels(
        [
            {**BASE_ROW, "report_period": "2025Q1", "net_income": -10},
            {**BASE_ROW, "report_period": "2025Q2", "net_income": -20},
        ]
    )

    assert "two_quarter_net_loss" in labels[1]["distress_reason"]


def test_financial_sector_rows_are_excluded_from_rule_based_labels():
    row = {**BASE_ROW, "sector": "Banks", "total_liabilities": 950, "equity": 50}

    label = compute_distress_label(row)

    assert label.z_score is None
    assert label.distress_label is None
    assert label.label_source == "rule_based_v1"
    assert label.label_confidence is None
    assert label.training_eligible is False
    assert "financial_sector_excluded" in label.distress_reason


def test_gray_zone_label_is_low_confidence_and_not_training_eligible():
    row = {
        **BASE_ROW,
        "current_assets": 250,
        "current_liabilities": 200,
        "retained_earnings": 40,
        "ebit": 80,
        "equity": 500,
        "total_liabilities": 500,
    }

    label = compute_distress_label(row)

    assert label.z_score == 2.046
    assert label.distress_label == 0
    assert label.label_confidence == "low"
    assert label.training_eligible is False
    assert "gray_zone_monitor" in label.distress_reason


def test_zero_liabilities_keeps_z_score_positive_instead_of_null():
    row = {**BASE_ROW, "total_liabilities": 0, "equity": 500}

    label = compute_distress_label(row)

    assert label.z_score is not None
    assert label.z_score > 2.6
    assert label.distress_label == 0
    assert "zero_liabilities_x4_capped" in label.distress_reason


def test_zero_interest_expense_does_not_trigger_weak_coverage_warning():
    row = {
        **BASE_ROW,
        "interest_expense": 0,
        "total_liabilities": 900,
        "current_assets": 100,
        "current_liabilities": 250,
    }

    label = compute_distress_label(row)

    assert "weak_interest_coverage" not in label.distress_reason
