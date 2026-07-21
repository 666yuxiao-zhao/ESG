"""ECharts option builders."""

from __future__ import annotations

import pandas as pd

from .constants import SCOPE_COLORS


TEXT = "#23313d"
MUTED = "#71808d"
GRID = "#e7edf0"
PALETTE = ["#15966f", "#2774c7", "#e19a2b", "#d45252", "#6a67b8", "#28a2a2"]


def scope_donut(results: pd.DataFrame) -> dict:
    values = results.groupby("scope", dropna=False)["emissions_t"].sum().reindex(["Scope 1", "Scope 2", "Scope 3"]).fillna(0)
    return {
        "tooltip": {"trigger": "item", "formatter": "{b}<br/>{c} tCO2e · {d}%"},
        "legend": {"bottom": 0, "icon": "circle", "textStyle": {"color": MUTED}},
        "series": [{
            "name": "排放范围",
            "type": "pie",
            "radius": ["52%", "76%"],
            "center": ["50%", "44%"],
            "avoidLabelOverlap": True,
            "itemStyle": {"borderColor": "#ffffff", "borderWidth": 3},
            "label": {"show": True, "formatter": "{d}%", "color": TEXT, "fontWeight": 600},
            "data": [
                {"name": scope, "value": round(float(value), 4), "itemStyle": {"color": SCOPE_COLORS[scope]}}
                for scope, value in values.items()
            ],
        }],
    }


def category_bar(results: pd.DataFrame) -> dict:
    values = results.groupby("category")["emissions_t"].sum().sort_values()
    return {
        "grid": {"left": 12, "right": 22, "top": 12, "bottom": 8, "containLabel": True},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "xAxis": {"type": "value", "name": "tCO2e", "nameTextStyle": {"color": MUTED}, "axisLabel": {"color": MUTED}, "splitLine": {"lineStyle": {"color": GRID}}},
        "yAxis": {"type": "category", "data": values.index.tolist(), "axisLabel": {"color": TEXT}, "axisTick": {"show": False}, "axisLine": {"show": False}},
        "series": [{"type": "bar", "data": [round(float(value), 4) for value in values], "barMaxWidth": 22, "itemStyle": {"color": "#2774c7", "borderRadius": [0, 3, 3, 0]}, "emphasis": {"itemStyle": {"color": "#15966f"}}}],
    }


def monthly_trend(results: pd.DataFrame) -> dict:
    data = results.copy()
    data["month"] = data["date"].dt.strftime("%Y-%m")
    pivot = data.pivot_table(index="month", columns="scope", values="emissions_t", aggfunc="sum", fill_value=0)
    scopes = [scope for scope in ("Scope 1", "Scope 2", "Scope 3") if scope in pivot.columns]
    return {
        "color": [SCOPE_COLORS[scope] for scope in scopes],
        "tooltip": {"trigger": "axis"},
        "legend": {"top": 0, "icon": "circle", "textStyle": {"color": MUTED}},
        "grid": {"left": 12, "right": 22, "top": 42, "bottom": 8, "containLabel": True},
        "xAxis": {"type": "category", "data": pivot.index.tolist(), "boundaryGap": False, "axisLabel": {"color": MUTED}, "axisLine": {"lineStyle": {"color": GRID}}},
        "yAxis": {"type": "value", "name": "tCO2e", "axisLabel": {"color": MUTED}, "splitLine": {"lineStyle": {"color": GRID}}},
        "series": [
            {"name": scope, "type": "line", "smooth": True, "symbolSize": 7, "data": [round(float(value), 4) for value in pivot[scope]], "lineStyle": {"width": 3}, "areaStyle": {"opacity": 0.06}}
            for scope in scopes
        ],
    }


def facility_bar(results: pd.DataFrame) -> dict:
    values = results.groupby("facility")["emissions_t"].sum().sort_values(ascending=False)
    return {
        "color": PALETTE,
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "grid": {"left": 12, "right": 18, "top": 14, "bottom": 8, "containLabel": True},
        "xAxis": {"type": "category", "data": values.index.tolist(), "axisLabel": {"color": MUTED, "interval": 0}, "axisTick": {"show": False}, "axisLine": {"lineStyle": {"color": GRID}}},
        "yAxis": {"type": "value", "name": "tCO2e", "axisLabel": {"color": MUTED}, "splitLine": {"lineStyle": {"color": GRID}}},
        "series": [{"type": "bar", "data": [{"value": round(float(value), 4), "itemStyle": {"color": PALETTE[index % len(PALETTE)]}} for index, value in enumerate(values)], "barMaxWidth": 48, "itemStyle": {"borderRadius": [3, 3, 0, 0]}}],
    }
