from src.calculator import calculate_emissions
from src.data_loader import load_activity_data, load_emission_factors
from src.report_generator import build_management_pdf, build_management_summary, build_recommendations
from src.validator import validate_activity_data


def calculated_sample():
    factors = load_emission_factors("data/emission_factors.csv")
    activity = load_activity_data("data/sample_activity_data.csv")
    cleaned, _ = validate_activity_data(activity, factors)
    return calculate_emissions(cleaned, factors), factors


def test_management_pdf_is_generated_from_current_results():
    results, factors = calculated_sample()
    pdf = build_management_pdf(results, factors, "内置演示数据")
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 5_000


def test_summary_and_recommendations_reflect_emission_profile():
    results, _ = calculated_sample()
    summary = build_management_summary(results)
    recommendations = build_recommendations(results)
    assert "3 个核算场所" in summary
    assert "外购电力" in summary
    assert any(title == "低碳电力" for title, _ in recommendations)

