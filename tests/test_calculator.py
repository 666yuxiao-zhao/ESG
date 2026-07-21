import pandas as pd

from src.calculator import calculate_emissions, summarize_results


def test_calculates_activity_and_transport_emissions():
    data = pd.DataFrame(
        [
            {"category": "外购电力", "unit": "kWh", "amount": 1000, "distance_km": None, "weight_ton": None, "quality_status": "有效"},
            {"category": "公路运输", "unit": "t.km", "amount": 1, "distance_km": 100, "weight_ton": 2, "quality_status": "有效"},
        ]
    )
    factors = pd.DataFrame(
        [
            {"factor_id": "e", "category": "外购电力", "scope": "Scope 2", "input_unit": "kWh", "factor_value": 0.5, "factor_unit": "kgCO2e/kWh", "factor_year": 2022, "factor_source": "test", "calculation_method": "activity"},
            {"factor_id": "r", "category": "公路运输", "scope": "Scope 3", "input_unit": "t.km", "factor_value": 0.1, "factor_unit": "kgCO2e/t.km", "factor_year": 2022, "factor_source": "test", "calculation_method": "ton_km"},
        ]
    )

    result = calculate_emissions(data, factors)

    assert result["emissions_kg"].tolist() == [500.0, 20.0]
    summary = summarize_results(result)
    assert summary["total"] == 0.52
    assert summary["scope_2"] == 0.5
    assert summary["scope_3"] == 0.02


def test_error_rows_do_not_contribute_to_total():
    data = pd.DataFrame(
        [{"category": "天然气", "unit": "m3", "amount": 100, "distance_km": None, "weight_ton": None, "quality_status": "错误"}]
    )
    factors = pd.DataFrame(
        [{"factor_id": "g", "category": "天然气", "scope": "Scope 1", "input_unit": "m3", "factor_value": 2.0, "factor_unit": "kgCO2e/m3", "factor_year": 2022, "factor_source": "test", "calculation_method": "activity"}]
    )
    result = calculate_emissions(data, factors)
    assert result.loc[0, "emissions_kg"] == 0


def test_transport_accepts_precalculated_ton_km():
    data = pd.DataFrame(
        [{"category": "公路运输", "unit": "t.km", "amount": 580, "distance_km": None, "weight_ton": None, "quality_status": "有效"}]
    )
    factors = pd.DataFrame(
        [{"factor_id": "r", "category": "公路运输", "scope": "Scope 3", "input_unit": "t.km", "factor_value": 0.1, "factor_unit": "kgCO2e/t.km", "factor_year": 2022, "factor_source": "test", "calculation_method": "ton_km"}]
    )
    result = calculate_emissions(data, factors)
    assert result.loc[0, "normalized_amount"] == 580
    assert result.loc[0, "emissions_kg"] == 58
