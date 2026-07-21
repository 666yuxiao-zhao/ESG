"""Input parsing, schema normalization, and template generation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .constants import COLUMN_ALIASES, INPUT_COLUMNS


CATEGORY_ALIASES = {
    "EDA工作站与编译服务器": "外购电力",
    "EDA工作站与编译主机用电": "外购电力",
    "贴片机与回流焊高温区": "外购电力",
    "贴片机与回流焊高频用电": "外购电力",
    "高精度示波器与恒温箱": "外购电力",
    "高精度示波器与恒温烙铁用电": "外购电力",
    "实验室空调制冷剂补充": "制冷剂R410A",
    "实验室空调制冷剂(R410a)微损泄漏": "制冷剂R410A",
    "覆铜板与阻焊油墨运输": "公路运输",
    "覆铜板与阻焊油墨供应链物流": "公路运输",
    "无水乙醇与清洗剂消耗": "清洗剂",
}

UNIT_ALIASES = {
    "t·km": "t.km",
    "t-km": "t.km",
    "吨公里": "t.km",
}


def _normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.rename(columns=COLUMN_ALIASES)
    for column in INPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    frame = frame[INPUT_COLUMNS]
    frame["category"] = frame["category"].replace(CATEGORY_ALIASES)
    frame["unit"] = frame["unit"].replace(UNIT_ALIASES)
    return frame


def load_activity_data(source: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Read a standard CSV/XLSX template and normalize its headers."""
    name = (filename or getattr(source, "name", str(source))).lower()
    if name.endswith(".csv"):
        try:
            frame = pd.read_csv(source, encoding="utf-8-sig")
        except UnicodeDecodeError:
            if hasattr(source, "seek"):
                source.seek(0)
            frame = pd.read_csv(source, encoding="gb18030")
    elif name.endswith((".xlsx", ".xlsm")):
        frame = pd.read_excel(source, engine="openpyxl")
    else:
        raise ValueError("仅支持 CSV 或 XLSX 文件。")
    return _normalize_headers(frame)


def load_emission_factors(path: str | Path) -> pd.DataFrame:
    factors = pd.read_csv(path, encoding="utf-8-sig")
    factors["factor_value"] = pd.to_numeric(factors["factor_value"], errors="raise")
    factors["factor_year"] = pd.to_numeric(factors["factor_year"], errors="raise").astype(int)
    return factors


def build_excel_template(sample: pd.DataFrame) -> bytes:
    """Create a user-facing Excel template entirely in memory."""
    output = BytesIO()
    export = sample.rename(
        columns={
            "date": "日期",
            "facility": "工厂",
            "category": "排放源",
            "amount": "活动数据",
            "unit": "单位",
            "region": "地区",
            "distance_km": "运输距离_km",
            "weight_ton": "货物重量_t",
            "output_value": "产量",
            "output_unit": "产量单位",
            "note": "备注",
        }
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export.to_excel(writer, sheet_name="活动数据", index=False)
        worksheet = writer.sheets["活动数据"]
        worksheet.freeze_panes = "A2"
        worksheet.auto_filter.ref = worksheet.dimensions
        widths = {"A": 13, "B": 16, "C": 16, "D": 14, "E": 12, "F": 12, "G": 16, "H": 16, "I": 12, "J": 12, "K": 24}
        for column, width in widths.items():
            worksheet.column_dimensions[column].width = width
    return output.getvalue()
