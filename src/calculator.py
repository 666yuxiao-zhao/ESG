"""Traceable carbon emission calculations."""

from __future__ import annotations

import pandas as pd


RESULT_FACTOR_COLUMNS = [
    "factor_id",
    "scope",
    "input_unit",
    "factor_value",
    "factor_unit",
    "factor_year",
    "factor_source",
    "calculation_method",
]


def calculate_emissions(data: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    """Match activity records to factors and calculate kg/t CO2e."""
    factor_lookup = factors.sort_values("factor_year").drop_duplicates(["category", "input_unit"], keep="last")
    merged = data.merge(
        factor_lookup[["category", *RESULT_FACTOR_COLUMNS]],
        left_on=["category", "unit"],
        right_on=["category", "input_unit"],
        how="left",
    )

    direct = merged["calculation_method"].eq("activity")
    transport = merged["calculation_method"].eq("ton_km")
    activity_amount = pd.to_numeric(merged["amount"], errors="coerce").astype("float64")
    distance = pd.to_numeric(merged["distance_km"], errors="coerce").astype("float64")
    weight = pd.to_numeric(merged["weight_ton"], errors="coerce").astype("float64")
    component_amount = distance * weight
    transport_amount = component_amount.where(
        (distance > 0) & (weight > 0),
        activity_amount,
    )
    merged["normalized_amount"] = activity_amount.where(direct, transport_amount.where(transport, 0.0))
    merged["normalized_amount"] = pd.to_numeric(merged["normalized_amount"], errors="coerce").fillna(0.0)

    calculable = merged["quality_status"].ne("错误") & merged["factor_value"].notna()
    calculated = merged["normalized_amount"] * merged["factor_value"]
    merged["emissions_kg"] = calculated.where(calculable, 0.0).fillna(0.0).astype(float)
    merged["emissions_t"] = merged["emissions_kg"] / 1000
    return merged


def summarize_results(results: pd.DataFrame) -> dict[str, float | str]:
    valid = results.loc[results["quality_status"] != "错误"]
    total = float(valid["emissions_t"].sum())
    by_scope = valid.groupby("scope", dropna=False)["emissions_t"].sum().to_dict()
    by_category = valid.groupby("category")["emissions_t"].sum().sort_values(ascending=False)
    return {
        "total": total,
        "scope_1": float(by_scope.get("Scope 1", 0)),
        "scope_2": float(by_scope.get("Scope 2", 0)),
        "scope_3": float(by_scope.get("Scope 3", 0)),
        "top_source": str(by_category.index[0]) if not by_category.empty else "--",
        "top_source_value": float(by_category.iloc[0]) if not by_category.empty else 0,
    }
