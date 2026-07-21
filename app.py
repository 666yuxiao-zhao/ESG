"""Enterprise carbon accounting dashboard."""

from __future__ import annotations

from html import escape as html_escape
from pathlib import Path

import pandas as pd
import streamlit as st
from streamlit_echarts import st_echarts

from src.calculator import calculate_emissions, summarize_results
from src.charts import category_bar, facility_bar, monthly_trend, scope_donut
from src.constants import DISPLAY_COLUMNS
from src.data_loader import build_excel_template, load_activity_data, load_emission_factors
from src.exporter import export_results_excel
from src.report_generator import build_management_pdf, build_management_summary, build_recommendations
from src.validator import validate_activity_data


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(
    page_title="碳衡 · 企业碳足迹看板",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_reference_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    factors = load_emission_factors(DATA_DIR / "emission_factors.csv")
    sample = load_activity_data(DATA_DIR / "sample_activity_data.csv")
    return factors, sample


def apply_styles() -> None:
    css = (BASE_DIR / "assets" / "styles.css").read_text(encoding="utf-8")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def section(title: str, caption: str) -> None:
    st.markdown(
        f'<div class="section-heading">{title}</div><div class="section-caption">{caption}</div>',
        unsafe_allow_html=True,
    )


def metric_value(value: float) -> str:
    return f"{value:,.1f} t"


def prepare_uploaded_data(uploaded_file, sample: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    if uploaded_file is None:
        return sample.copy(), "内置演示数据"
    return load_activity_data(uploaded_file, uploaded_file.name), uploaded_file.name


def reset_filters() -> None:
    for key in ("facility_filter", "scope_filter", "category_filter", "date_filter"):
        st.session_state.pop(key, None)


def filter_results(results: pd.DataFrame) -> pd.DataFrame:
    with st.sidebar:
        st.markdown('<div class="sidebar-section-label">分析范围</div>', unsafe_allow_html=True)
        facilities = sorted(results["facility"].dropna().unique().tolist())
        selected_facilities = st.multiselect("工厂", facilities, placeholder="全部工厂", key="facility_filter")
        scopes = [scope for scope in ("Scope 1", "Scope 2", "Scope 3") if scope in results["scope"].dropna().unique()]
        selected_scopes = st.multiselect("排放范围", scopes, placeholder="全部范围", key="scope_filter")
        categories = sorted(results["category"].dropna().unique().tolist())
        selected_categories = st.multiselect("排放源", categories, placeholder="全部排放源", key="category_filter")

        valid_dates = results["date"].dropna()
        if valid_dates.empty:
            date_range = None
        else:
            date_range = st.date_input(
                "核算期间",
                value=(valid_dates.min().date(), valid_dates.max().date()),
                min_value=valid_dates.min().date(),
                max_value=valid_dates.max().date(),
                key="date_filter",
            )
        st.button("重置筛选", icon=":material/restart_alt:", on_click=reset_filters, width="stretch")

    facility_mask = results["facility"].isin(selected_facilities) if selected_facilities else pd.Series(True, index=results.index)
    scope_mask = results["scope"].isin(selected_scopes) if selected_scopes else pd.Series(True, index=results.index)
    category_mask = results["category"].isin(selected_categories) if selected_categories else pd.Series(True, index=results.index)
    filtered = results[facility_mask & scope_mask & category_mask]
    if date_range and len(date_range) == 2:
        start, end = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
        filtered = filtered[filtered["date"].between(start, end)]
    return filtered


apply_styles()
factors, sample_data = load_reference_data()

with st.sidebar:
    st.markdown(
        '<div class="brand-lockup"><div><div class="brand-name"><span class="brand-accent"></span>CarbonScope</div><div class="brand-tagline">企业碳管理工作台</div></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="sidebar-section-label">数据源</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader("上传活动数据", type=["csv", "xlsx"], help="支持中文或英文字段的 CSV / XLSX 文件")
    template_bytes = build_excel_template(sample_data.head(3))
    demo_bytes = build_excel_template(sample_data)
    with st.popover("数据工具", icon=":material/dataset:", width="stretch"):
        st.download_button(
            "下载数据模板",
            data=template_bytes,
            file_name="企业碳核算数据模板.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/download:",
            width="stretch",
        )
        st.download_button(
            "下载演示数据",
            data=demo_bytes,
            file_name="CarbonScope_演示数据.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            icon=":material/database:",
            width="stretch",
        )

try:
    raw_data, source_name = prepare_uploaded_data(uploaded_file, sample_data)
except Exception as exc:
    st.error(f"文件读取失败：{exc}")
    st.stop()

with st.sidebar:
    source_details = [f"{len(raw_data):,} 条活动记录"]
    source_meta = html_escape(" · ".join(source_details))
    st.markdown(
        f'<div class="source-panel"><div class="source-label">当前数据</div><div class="source-name">{html_escape(source_name)}</div><div class="source-meta">{source_meta}</div></div>',
        unsafe_allow_html=True,
    )

validated_data, issues = validate_activity_data(raw_data, factors)
results = calculate_emissions(validated_data, factors)
filtered = filter_results(results)
valid_filtered = filtered.loc[filtered["quality_status"] != "错误"].copy()

with st.sidebar:
    st.divider()
    version = factors["factor_version"].iloc[0]
    st.markdown(
        f'<div class="sidebar-footnote">因子库 {html_escape(str(version))}<br>演示环境 · 不构成审计或披露依据</div>',
        unsafe_allow_html=True,
    )

st.markdown('<div class="dashboard-kicker">ESG PERFORMANCE CENTER</div>', unsafe_allow_html=True)
st.markdown('<h1 class="dashboard-title">企业碳排放与能源绩效</h1>', unsafe_allow_html=True)
st.markdown(
    f'<div class="dashboard-subtitle">数据源：{html_escape(source_name)} · 核算单位：tCO2e · 更新时间：{pd.Timestamp.now().strftime("%Y-%m-%d %H:%M")}</div>',
    unsafe_allow_html=True,
)

valid_count = int((validated_data["quality_status"] != "错误").sum())
total_count = len(validated_data)
quality_rate = valid_count / total_count * 100 if total_count else 0
st.markdown(
    f'<div class="status-strip"><span>核算已完成 · {valid_count}/{total_count} 条记录纳入统计</span><span>数据有效率 {quality_rate:.1f}%</span></div>',
    unsafe_allow_html=True,
)

if valid_filtered.empty:
    st.error("当前数据没有记录通过核算校验。下方已列出自动识别结果和具体问题。")
    section("导入诊断", "核对原始排放源、识别结果、单位和问题说明")
    diagnostic_columns = [
        column
        for column in ("source_row", "facility", "original_category", "category", "amount", "original_unit", "unit", "mapping_status", "mapping_note", "quality_status")
        if column in filtered.columns
    ]
    diagnostic_names = {
        "source_row": "原始行号",
        "facility": "工厂",
        "original_category": "原始排放源",
        "category": "识别结果",
        "amount": "消耗量",
        "original_unit": "上传单位",
        "unit": "标准单位",
        "mapping_status": "识别状态",
        "mapping_note": "识别说明",
        "quality_status": "数据状态",
    }
    st.dataframe(filtered[diagnostic_columns].rename(columns=diagnostic_names), width="stretch", hide_index=True)
    if not issues.empty:
        st.dataframe(
            issues.rename(columns={"row": "原始行号", "level": "级别", "field": "字段", "message": "问题说明"}),
            width="stretch",
            hide_index=True,
        )
    st.stop()

summary = summarize_results(valid_filtered)
monthly_total = valid_filtered.assign(month=valid_filtered["date"].dt.to_period("M")).groupby("month")["emissions_t"].sum()
delta = None
if len(monthly_total) >= 2 and monthly_total.iloc[-2] != 0:
    delta = f"{(monthly_total.iloc[-1] / monthly_total.iloc[-2] - 1) * 100:+.1f}% 环比"

kpi_columns = st.columns(4)
kpi_columns[0].metric("总排放量", metric_value(summary["total"]), delta=delta, delta_color="inverse")
kpi_columns[1].metric("Scope 1 · 直接排放", metric_value(summary["scope_1"]))
kpi_columns[2].metric("Scope 2 · 能源间接排放", metric_value(summary["scope_2"]))
kpi_columns[3].metric("Scope 3 · 其他间接排放", metric_value(summary["scope_3"]))

overview_tab, detail_tab, quality_tab, factor_tab, report_tab = st.tabs(["排放总览", "核算明细", "数据质量", "排放因子", "管理报告"])

with overview_tab:
    left, right = st.columns([0.88, 1.52], gap="large")
    with left:
        section("排放范围构成", "按 GHG Protocol 范围归类")
        st_echarts(scope_donut(valid_filtered), height="340px", key="scope_donut")
    with right:
        section("月度排放趋势", "查看各排放范围的变化与贡献")
        st_echarts(monthly_trend(valid_filtered), height="340px", key="monthly_trend")

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        section("排放源贡献", "识别减排优先级最高的能源与活动")
        st_echarts(category_bar(valid_filtered), height="360px", key="category_bar")
    with right:
        section("工厂排放对比", "按所选核算范围汇总")
        st_echarts(facility_bar(valid_filtered), height="360px", key="facility_bar")

    top_share = summary["top_source_value"] / summary["total"] * 100 if summary["total"] else 0
    st.markdown(
        f'<div class="insight-band">重点观察：<strong>{html_escape(str(summary["top_source"]))}</strong> 是当前最大排放源，占所选范围总排放的 <strong>{top_share:.1f}%</strong>。</div>',
        unsafe_allow_html=True,
    )

with detail_tab:
    section("逐笔核算结果", "每条结果均保留活动数据、因子版本和计算结果")
    detail_columns = [column for column in DISPLAY_COLUMNS if column in filtered.columns]
    detail = filtered[detail_columns].rename(columns=DISPLAY_COLUMNS)
    st.dataframe(
        detail,
        width="stretch",
        hide_index=True,
        column_config={
            "排放量 (kgCO2e)": st.column_config.NumberColumn(format="%.2f"),
            "排放量 (tCO2e)": st.column_config.NumberColumn(format="%.4f"),
            "排放因子": st.column_config.NumberColumn(format="%.4f"),
        },
    )
    export_bytes = export_results_excel(filtered, issues)
    st.download_button(
        "导出当前核算结果",
        data=export_bytes,
        file_name="碳排放核算结果.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with quality_tab:
    section("数据质量检查", "错误记录不进入排放总量；警告记录保留但建议复核")
    status_counts = validated_data["quality_status"].value_counts()
    quality_columns = st.columns(3)
    quality_columns[0].metric("有效", int(status_counts.get("有效", 0)))
    quality_columns[1].metric("警告", int(status_counts.get("警告", 0)))
    quality_columns[2].metric("错误", int(status_counts.get("错误", 0)))
    if issues.empty:
        st.success("未发现字段缺失、单位冲突或重复记录。")
    else:
        issue_display = issues.rename(columns={"row": "原始行号", "level": "级别", "field": "字段", "message": "问题说明"})
        st.dataframe(issue_display, width="stretch", hide_index=True)

with factor_tab:
    section("排放因子台账", "因子独立于计算代码维护，便于替换、复核和版本追踪")
    factor_display = factors.rename(
        columns={
            "factor_id": "因子编号",
            "category": "排放源",
            "scope": "范围",
            "input_unit": "活动单位",
            "factor_value": "因子值",
            "factor_unit": "因子单位",
            "region": "适用地区",
            "factor_year": "年份",
            "factor_source": "来源",
            "factor_version": "版本",
        }
    )
    st.dataframe(
        factor_display[["因子编号", "排放源", "范围", "活动单位", "因子值", "因子单位", "适用地区", "年份", "来源", "版本"]],
        width="stretch",
        hide_index=True,
    )
    st.warning("本项目内置数值用于功能演示。正式盘查前，应由专业人员按组织边界、核算年度和适用标准更新并审核因子。")

with report_tab:
    section("管理层报告", "根据当前筛选范围生成，可用于内部汇报和方案演示")
    report_summary = build_management_summary(valid_filtered)
    st.markdown(f'<div class="report-summary">{html_escape(report_summary)}</div>', unsafe_allow_html=True)
    recommendation_columns = st.columns(2)
    for index, (title, description) in enumerate(build_recommendations(valid_filtered)):
        with recommendation_columns[index % 2]:
            st.markdown(f"**{index + 1}. {title}**")
            st.caption(description)
    report_bytes = build_management_pdf(filtered, factors, source_name)
    st.download_button(
        "下载管理层 PDF 报告",
        data=report_bytes,
        file_name=f"CarbonScope_管理报告_{pd.Timestamp.now():%Y%m%d}.pdf",
        mime="application/pdf",
        icon=":material/picture_as_pdf:",
        type="primary",
    )
