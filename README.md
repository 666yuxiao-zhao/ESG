# 碳衡 CarbonScope

一个面向中国制造企业场景的碳足迹核算与 ESG 可视化看板。上传 CSV 或 Excel 活动数据后，系统会进行字段校验、排放因子匹配和 Scope 1/2/3 核算，并生成交互图表与可导出的核算明细。

## 功能

- 支持 CSV、XLSX 上传及中文字段模板
- 覆盖外购电力、热力、常见燃料与四类物流运输
- 按 GHG Protocol 的 Scope 1、2、3 分类
- 提供排放构成、月度趋势、排放源贡献和工厂对比图
- 逐行提示缺失字段、单位冲突、重复记录与物流数据错误
- 排放结果保留因子年份、来源和版本
- 支持导出 Excel 核算明细
- 根据当前筛选范围生成管理层 PDF 报告
- 支持下载数据模板和完整演示数据
- 未上传文件时自动展示虚构工厂演示数据

## 本地运行

建议使用 Python 3.11 或更高版本。

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

浏览器打开 `http://localhost:8501`。

## 数据模板

看板侧边栏可以直接下载 Excel 模板，也可以参考 `templates/carbon_activity_template.csv`。能源记录的 `活动数据` 直接参与核算；物流记录按下式计算：

```text
排放量 = 货物重量（t）× 运输距离（km）× 排放因子（kgCO2e/t.km）
```

模板中的物流 `活动数据` 可填写 `1`，实际周转量由重量和距离生成。

## 测试

```powershell
python -m pytest -q
```

## 使用边界

仓库内的排放因子是用于软件功能展示的参考数据，不构成第三方审计、监管披露或碳交易依据。正式使用前，应根据组织边界、核算年度、能源品种和适用标准，由专业人员复核并更新 `data/emission_factors.csv`。
