"""Result export helpers."""

from __future__ import annotations

from io import BytesIO

import pandas as pd

from .constants import DISPLAY_COLUMNS


def export_results_excel(results: pd.DataFrame, issues: pd.DataFrame) -> bytes:
    output = BytesIO()
    detail_columns = [column for column in DISPLAY_COLUMNS if column in results.columns]
    detail = results[detail_columns].rename(columns=DISPLAY_COLUMNS)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        detail.to_excel(writer, sheet_name="核算明细", index=False)
        issues.rename(columns={"row": "原始行号", "level": "级别", "field": "字段", "message": "说明"}).to_excel(
            writer, sheet_name="数据质量", index=False
        )
        for sheet in writer.sheets.values():
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
    return output.getvalue()

