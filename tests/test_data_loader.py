from io import BytesIO

from src.data_loader import load_activity_data


def test_chinese_headers_are_normalized():
    source = BytesIO("日期,工厂,排放源,活动数据,单位\n2026-01-01,A,外购电力,100,kWh\n".encode("utf-8-sig"))
    frame = load_activity_data(source, "input.csv")
    assert frame.loc[0, "facility"] == "A"
    assert frame.loc[0, "amount"] == 100
    assert "distance_km" in frame.columns

