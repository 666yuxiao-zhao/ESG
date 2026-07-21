"""Management-ready PDF report generation."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .calculator import summarize_results


GREEN = colors.HexColor("#16856A")
DARK = colors.HexColor("#203642")
MUTED = colors.HexColor("#6C7C84")
LINE = colors.HexColor("#D9E3E1")
PALE_GREEN = colors.HexColor("#EAF5F1")
PALE_GRAY = colors.HexColor("#F3F6F6")


def _register_font() -> str:
    font_name = "CarbonScopeCN"
    if font_name in pdfmetrics.getRegisteredFontNames():
        return font_name
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/PingFang.ttc"),
    ]
    for candidate in candidates:
        if candidate.exists():
            pdfmetrics.registerFont(TTFont(font_name, str(candidate)))
            return font_name
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    return "STSong-Light"


def build_management_summary(results: pd.DataFrame) -> str:
    summary = summarize_results(results)
    scope_2_share = summary["scope_2"] / summary["total"] * 100 if summary["total"] else 0
    facilities = results["facility"].dropna().nunique()
    return (
        f"本报告覆盖 {facilities} 个核算场所，总温室气体排放为 {summary['total']:,.1f} tCO2e。"
        f"最大排放源为{summary['top_source']}，Scope 2 占总排放的 {scope_2_share:.1f}%。"
        "建议先核实高贡献排放源的活动数据，再将减排资源配置到可量化、可复核的项目。"
    )


def build_recommendations(results: pd.DataFrame) -> list[tuple[str, str]]:
    summary = summarize_results(results)
    top_source = summary["top_source"]
    recommendations: list[tuple[str, str]] = []
    if top_source == "外购电力" or summary["scope_2"] >= summary["total"] * 0.5:
        recommendations.extend(
            [
                ("用能效率", "对高耗能产线建立分项计量和单位产出能耗基线，优先治理待机、空转和峰值负荷。"),
                ("低碳电力", "评估分布式光伏与绿电采购；环境权益应按适用标准单独留存凭证并分别披露核算口径。"),
            ]
        )
    if summary["scope_1"] > 0:
        recommendations.append(("直接排放", "复核锅炉、备用发电及燃料计量，评估电气化替代和燃烧效率提升的减排潜力。"))
    if summary["scope_3"] > 0:
        recommendations.append(("供应链物流", "按承运商、运输方式和线路补齐吨公里数据，优先提高装载率并评估公转铁或水运替代。"))
    recommendations.append(("数据治理", "固定月度关账、异常复核和因子版本审批流程，保留原始凭证与计算链路以支持审阅。"))
    return recommendations[:4]


def _styles(font_name: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("TitleCN", parent=base["Title"], fontName=font_name, fontSize=24, leading=32, textColor=DARK, alignment=TA_LEFT, spaceAfter=5 * mm),
        "subtitle": ParagraphStyle("SubtitleCN", parent=base["Normal"], fontName=font_name, fontSize=9.5, leading=15, textColor=MUTED, spaceAfter=4 * mm),
        "h1": ParagraphStyle("H1CN", parent=base["Heading1"], fontName=font_name, fontSize=15, leading=22, textColor=DARK, spaceBefore=6 * mm, spaceAfter=3 * mm),
        "h2": ParagraphStyle("H2CN", parent=base["Heading2"], fontName=font_name, fontSize=11, leading=17, textColor=DARK, spaceBefore=3 * mm, spaceAfter=1.5 * mm),
        "body": ParagraphStyle("BodyCN", parent=base["BodyText"], fontName=font_name, fontSize=9.5, leading=17, textColor=DARK, alignment=TA_LEFT),
        "small": ParagraphStyle("SmallCN", parent=base["BodyText"], fontName=font_name, fontSize=8, leading=13, textColor=MUTED),
        "number": ParagraphStyle("NumberCN", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=14, textColor=DARK, alignment=TA_RIGHT),
        "center": ParagraphStyle("CenterCN", parent=base["BodyText"], fontName=font_name, fontSize=9, leading=14, textColor=DARK, alignment=TA_CENTER),
    }


def _p(value: object, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(str(value)), style)


def _table(data: list[list[object]], widths: list[float], font_name: str, header: bool = True) -> Table:
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("LEADING", (0, 0), (-1, -1), 14),
        ("TEXTCOLOR", (0, 0), (-1, -1), DARK),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_GRAY]),
    ]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), DARK), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white)])
    table.setStyle(TableStyle(commands))
    return table


def build_management_pdf(results: pd.DataFrame, factors: pd.DataFrame, source_name: str) -> bytes:
    """Build a traceable PDF from the currently filtered calculation results."""
    valid = results.loc[results["quality_status"] != "错误"].copy()
    if valid.empty:
        raise ValueError("没有可用于生成报告的有效记录。")

    font_name = _register_font()
    styles = _styles(font_name)
    summary = summarize_results(valid)
    facilities = sorted(valid["facility"].dropna().astype(str).unique())
    organization = facilities[0] if len(facilities) == 1 else f"多场所汇总（{len(facilities)} 个场所）"
    start = valid["date"].min().strftime("%Y-%m-%d")
    end = valid["date"].max().strftime("%Y-%m-%d")
    factor_versions = "、".join(sorted(factors["factor_version"].dropna().astype(str).unique()))
    quality_rate = (results["quality_status"] != "错误").mean() * 100

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=17 * mm,
        title="CarbonScope 企业碳排放管理报告",
        author="CarbonScope",
    )

    def page_footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font_name, 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 9 * mm, "CarbonScope · 企业温室气体核算管理报告")
        canvas.drawRightString(A4[0] - 18 * mm, 9 * mm, f"第 {doc.page} 页")
        canvas.restoreState()

    story: list[object] = []
    story.append(Paragraph("CarbonScope 企业碳排放管理报告", styles["title"]))
    story.append(Paragraph(f"组织范围：{escape(organization)}　|　核算期间：{start} 至 {end}　|　生成日期：{datetime.now():%Y-%m-%d}", styles["subtitle"]))
    story.append(Table([[""]], colWidths=[174 * mm], rowHeights=[1.2 * mm], style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN)])))
    story.append(Spacer(1, 6 * mm))

    summary_box = Table(
        [[Paragraph("管理摘要", styles["h2"])], [Paragraph(build_management_summary(valid), styles["body"])], [Paragraph(f"数据有效率 {quality_rate:.1f}%　·　数据源 {escape(source_name)}　·　因子版本 {escape(factor_versions)}", styles["small"]) ]],
        colWidths=[174 * mm],
        style=TableStyle([("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN), ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B9DED2")), ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]),
    )
    story.append(summary_box)

    story.append(Paragraph("一、排放范围盘查", styles["h1"]))
    scope_values = valid.groupby("scope")["emissions_t"].sum().to_dict()
    scope_definitions = {"Scope 1": "企业控制的燃料燃烧等直接排放", "Scope 2": "外购电力与热力产生的能源间接排放", "Scope 3": "物流等价值链其他间接排放"}
    scope_rows: list[list[object]] = [["排放范围", "定义", "排放量 (tCO2e)", "占比"]]
    for scope in ("Scope 1", "Scope 2", "Scope 3"):
        value = float(scope_values.get(scope, 0))
        share = value / summary["total"] * 100 if summary["total"] else 0
        scope_rows.append([scope, scope_definitions[scope], f"{value:,.1f}", f"{share:.2f}%"])
    scope_rows.append(["总计", "", f"{summary['total']:,.1f}", "100.00%"])
    story.append(_table(scope_rows, [27 * mm, 83 * mm, 38 * mm, 26 * mm], font_name))

    story.append(Paragraph("二、排放源结构", styles["h1"]))
    category_values = valid.groupby("category")["emissions_t"].sum().sort_values(ascending=False)
    category_rows: list[list[object]] = [["排放源", "排放范围", "排放量 (tCO2e)", "占比"]]
    category_scopes = valid.drop_duplicates("category").set_index("category")["scope"].to_dict()
    for category, value in category_values.head(8).items():
        category_rows.append([category, category_scopes.get(category, ""), f"{value:,.1f}", f"{value / summary['total'] * 100:.2f}%"])
    story.append(_table(category_rows, [57 * mm, 35 * mm, 45 * mm, 37 * mm], font_name))

    story.append(PageBreak())
    story.append(Paragraph("三、场所表现", styles["h1"]))
    facility_values = valid.groupby("facility")["emissions_t"].sum().sort_values(ascending=False)
    facility_rows: list[list[object]] = [["核算场所", "排放量 (tCO2e)", "占比"]]
    for facility, value in facility_values.items():
        facility_rows.append([facility, f"{value:,.1f}", f"{value / summary['total'] * 100:.2f}%"])
    story.append(_table(facility_rows, [86 * mm, 48 * mm, 40 * mm], font_name))

    story.append(Paragraph("四、减排优先事项", styles["h1"]))
    story.append(Paragraph("以下建议由当前排放结构触发，适合作为立项筛选依据；实际减排量应在完成技术、财务及适用标准评估后确认。", styles["body"]))
    story.append(Spacer(1, 2 * mm))
    for index, (title, description) in enumerate(build_recommendations(valid), start=1):
        story.append(Paragraph(f"{index}. {escape(title)}", styles["h2"]))
        story.append(Paragraph(description, styles["body"]))

    story.append(Paragraph("五、核算口径与审阅提示", styles["h1"]))
    method_rows = [
        ["项目", "本报告采用的口径"],
        ["计算逻辑", "活动数据 × 排放因子；物流活动按货物重量 × 运输距离 × 因子计算。"],
        ["组织范围", "、".join(facilities)],
        ["排除规则", "数据质量状态为“错误”的记录不进入排放合计。"],
        ["因子版本", factor_versions],
        ["限制说明", "内置因子用于产品演示。正式披露前应复核组织边界、原始凭证、因子适用性及环境权益口径。"],
    ]
    story.append(_table(method_rows, [35 * mm, 139 * mm], font_name))
    story.append(Spacer(1, 6 * mm))
    story.append(Paragraph("本报告由 CarbonScope 根据当前筛选结果自动生成，仅供内部管理和方案演示，不构成鉴证、审计或监管披露结论。", styles["small"]))

    document.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return output.getvalue()
