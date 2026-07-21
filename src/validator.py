"""Activity data validation with row-level diagnostics."""

from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = ("date", "facility", "category", "amount", "unit")


def validate_activity_data(frame: pd.DataFrame, factors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return cleaned records and a diagnostics table.

    Invalid records remain in the cleaned frame but are marked as errors so the
    UI can explain exactly why they were excluded from totals.
    """
    data = frame.copy().reset_index(drop=True)
    data["source_row"] = data.index + 2
    diagnostics: list[dict[str, object]] = []

    for column in REQUIRED_COLUMNS:
        missing = data[column].isna() | data[column].astype(str).str.strip().isin(("", "nan", "<NA>"))
        for row in data.loc[missing, "source_row"]:
            diagnostics.append({"row": row, "level": "错误", "field": column, "message": f"必填字段 {column} 为空"})

    parsed_dates = pd.to_datetime(data["date"], errors="coerce")
    for row in data.loc[parsed_dates.isna(), "source_row"]:
        diagnostics.append({"row": row, "level": "错误", "field": "date", "message": "日期格式无法识别"})
    data["date"] = parsed_dates

    amounts = pd.to_numeric(data["amount"], errors="coerce")
    for row in data.loc[amounts.isna(), "source_row"]:
        diagnostics.append({"row": row, "level": "错误", "field": "amount", "message": "活动数据必须是数字"})
    for row in data.loc[amounts < 0, "source_row"]:
        diagnostics.append({"row": row, "level": "错误", "field": "amount", "message": "活动数据不能为负数"})
    data["amount"] = amounts

    known_categories = set(factors["category"])
    unknown = ~data["category"].isin(known_categories) & data["category"].notna()
    for row in data.loc[unknown, "source_row"]:
        diagnostics.append({"row": row, "level": "错误", "field": "category", "message": "排放源不在因子库中"})

    duplicate_mask = data.duplicated(subset=["date", "facility", "category", "amount", "unit"], keep=False)
    for row in data.loc[duplicate_mask, "source_row"]:
        diagnostics.append({"row": row, "level": "警告", "field": "record", "message": "疑似重复记录，请确认"})

    if "mapping_status" in data.columns:
        review_mapping = data["mapping_status"].eq("需复核")
        for _, row in data.loc[review_mapping].iterrows():
            diagnostics.append({"row": row["source_row"], "level": "警告", "field": "category", "message": row["mapping_note"]})

    if "scope_hint" in data.columns:
        scope_lookup = factors.drop_duplicates("category").set_index("category")["scope"].to_dict()
        calculated_scope = data["category"].map(scope_lookup)
        scope_values = data["scope_hint"].astype("string").fillna("")
        calculated_values = calculated_scope.astype("string").fillna("")
        scope_mismatch = scope_values.ne("") & calculated_values.ne("") & scope_values.ne(calculated_values)
        for index, row in data.loc[scope_mismatch].iterrows():
            diagnostics.append(
                {
                    "row": row["source_row"],
                    "level": "警告",
                    "field": "scope_hint",
                    "message": f"申报范围为 {row['scope_hint']}，因子库按 {calculated_scope.loc[index]} 核算，请复核",
                }
            )

    transport = data["category"].isin(factors.loc[factors["calculation_method"] == "ton_km", "category"])
    data["distance_km"] = pd.to_numeric(data["distance_km"], errors="coerce")
    data["weight_ton"] = pd.to_numeric(data["weight_ton"], errors="coerce")
    has_components = (data["distance_km"] > 0) & (data["weight_ton"] > 0)
    has_turnover = data["unit"].eq("t.km") & (data["amount"] > 0)
    invalid_transport = transport & ~(has_components | has_turnover)
    for row in data.loc[invalid_transport, "source_row"]:
        diagnostics.append(
            {
                "row": row,
                "level": "错误",
                "field": "transport_activity",
                "message": "物流记录需提供有效吨公里，或同时提供运输距离和货物重量",
            }
        )

    factor_units = factors.groupby("category")["input_unit"].apply(set).to_dict()
    mismatch = data.apply(
        lambda row: bool(row["category"] in factor_units and row["unit"] not in factor_units[row["category"]]),
        axis=1,
    )
    for _, row in data.loc[mismatch].iterrows():
        expected = "、".join(sorted(factor_units.get(row["category"], set())))
        diagnostics.append({"row": row["source_row"], "level": "错误", "field": "unit", "message": f"单位不匹配，应为：{expected}"})

    issues = pd.DataFrame(diagnostics, columns=["row", "level", "field", "message"])
    error_rows = set(issues.loc[issues["level"] == "错误", "row"]) if not issues.empty else set()
    warning_rows = set(issues.loc[issues["level"] == "警告", "row"]) if not issues.empty else set()
    data["quality_status"] = data["source_row"].map(
        lambda row: "错误" if row in error_rows else ("警告" if row in warning_rows else "有效")
    )
    return data, issues
