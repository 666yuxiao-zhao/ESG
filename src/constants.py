"""Shared schema and display constants."""

INPUT_COLUMNS = [
    "date",
    "facility",
    "category",
    "amount",
    "unit",
    "region",
    "distance_km",
    "weight_ton",
    "output_value",
    "output_unit",
    "note",
]

COLUMN_ALIASES = {
    "日期": "date",
    "工厂": "facility",
    "场所": "facility",
    "排放源": "category",
    "活动类型": "category",
    "用量": "amount",
    "活动数据": "amount",
    "单位": "unit",
    "地区": "region",
    "运输距离_km": "distance_km",
    "运输距离": "distance_km",
    "货物重量_t": "weight_ton",
    "货物重量": "weight_ton",
    "产量": "output_value",
    "产量单位": "output_unit",
    "备注": "note",
}

DISPLAY_COLUMNS = {
    "date": "日期",
    "facility": "工厂",
    "category": "排放源",
    "scope": "范围",
    "amount": "活动数据",
    "unit": "原始单位",
    "normalized_amount": "标准化数据",
    "factor_value": "排放因子",
    "factor_unit": "因子单位",
    "emissions_kg": "排放量 (kgCO2e)",
    "emissions_t": "排放量 (tCO2e)",
    "factor_year": "因子年份",
    "factor_source": "因子来源",
    "quality_status": "数据状态",
}

SCOPE_COLORS = {
    "Scope 1": "#15966f",
    "Scope 2": "#2774c7",
    "Scope 3": "#e19a2b",
}
