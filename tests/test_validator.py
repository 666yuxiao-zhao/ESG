import pandas as pd

from src.validator import validate_activity_data


def factors():
    return pd.DataFrame(
        [
            {"category": "外购电力", "input_unit": "kWh", "calculation_method": "activity"},
            {"category": "公路运输", "input_unit": "t.km", "calculation_method": "ton_km"},
        ]
    )


def test_valid_record_passes():
    frame = pd.DataFrame([{"date": "2026-01-01", "facility": "A", "category": "外购电力", "amount": 100, "unit": "kWh", "distance_km": None, "weight_ton": None}])
    cleaned, issues = validate_activity_data(frame, factors())
    assert issues.empty
    assert cleaned.loc[0, "quality_status"] == "有效"


def test_invalid_unit_and_missing_transport_fields_are_reported():
    frame = pd.DataFrame([{"date": "2026-01-01", "facility": "A", "category": "公路运输", "amount": 1, "unit": "kg", "distance_km": None, "weight_ton": None}])
    cleaned, issues = validate_activity_data(frame, factors())
    assert cleaned.loc[0, "quality_status"] == "错误"
    assert set(issues["field"]) == {"transport_activity", "unit"}


def test_direct_ton_km_is_valid_without_distance_and_weight():
    frame = pd.DataFrame([{"date": "2026-01-01", "facility": "A", "category": "公路运输", "amount": 580, "unit": "t.km", "distance_km": None, "weight_ton": None}])
    cleaned, issues = validate_activity_data(frame, factors())
    assert issues.empty
    assert cleaned.loc[0, "quality_status"] == "有效"
