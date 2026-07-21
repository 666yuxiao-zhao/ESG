"""Input parsing, schema normalization, and template generation."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from .constants import COLUMN_ALIASES, INPUT_COLUMNS


def _normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    frame.columns = [str(column).strip() for column in frame.columns]
    frame = frame.rename(columns=COLUMN_ALIASES)
    for column in INPUT_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame[INPUT_COLUMNS]


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

