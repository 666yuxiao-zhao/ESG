from io import BytesIO

from src.data_loader import load_activity_data


def test_chinese_headers_are_normalized():
    source = BytesIO("日期,工厂,排放源,活动数据,单位\n2026-01-01,A,外购电力,100,kWh\n".encode("utf-8-sig"))
    frame = load_activity_data(source, "input.csv")
    assert frame.loc[0, "facility"] == "A"
    assert frame.loc[0, "amount"] == 100
    assert "distance_km" in frame.columns


def test_known_business_sources_and_ton_km_are_normalized():
    source = BytesIO(
        "日期,工厂,排放源,活动数据,单位\n"
        "2026-01-01,A,EDA工作站与编译服务器,100,kWh\n"
        "2026-01-01,A,覆铜板与阻焊油墨运输,580,t·km\n".encode("utf-8-sig")
    )
    frame = load_activity_data(source, "input.csv")
    assert frame["category"].tolist() == ["外购电力", "公路运输"]
    assert frame["unit"].tolist() == ["kWh", "t.km"]
