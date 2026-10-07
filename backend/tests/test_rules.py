"""天气分档与规则引擎单元测试。"""
from app.services import weather_service
from app.services import outfit_service


def test_temperature_profile_tiers():
    assert weather_service.temperature_profile(0)["label"] == "寒冷"
    assert weather_service.temperature_profile(10)["label"] == "偏凉"
    assert weather_service.temperature_profile(20)["label"] == "舒适"
    assert weather_service.temperature_profile(28)["label"] == "偏热"
    assert weather_service.temperature_profile(35)["label"] == "炎热"
    assert weather_service.temperature_profile(None)["label"] == "舒适"


def test_season_compatible():
    assert weather_service.season_compatible("四季", {"冬"}) is True
    assert weather_service.season_compatible("冬", {"冬"}) is True
    assert weather_service.season_compatible("夏", {"冬"}) is False
    assert weather_service.season_compatible("不确定", {"春", "秋"}) is False


def test_normalize_category():
    assert outfit_service._normalize_category("上装") == "上装"
    assert outfit_service._normalize_category("包") == "配饰"
    assert outfit_service._normalize_category("连衣裙") == "上装"
    assert outfit_service._normalize_category("其他") is None


def test_rank_garments_filters_by_season():
    garments = [
        {"name": "羽绒服", "category": "外套", "season": "冬", "style": "", "color": "黑"},
        {"name": "T恤", "category": "上装", "season": "夏", "style": "", "color": "白"},
    ]
    tp = weather_service.temperature_profile(0)  # 寒冷 → 冬
    cats = outfit_service._rank_garments(garments, tp, "日常")
    assert cats["外套"][0]["garment"]["name"] == "羽绒服"
    assert cats["上装"] == []  # 夏装被温度过滤


def test_rank_garments_scene_bonus():
    garments = [
        {"name": "简约衬衫", "category": "上装", "season": "四季", "style": "简约", "color": "白"},
        {"name": "花T恤", "category": "上装", "season": "四季", "style": "街头", "color": "粉"},
    ]
    tp = weather_service.temperature_profile(20)  # 舒适
    cats = outfit_service._rank_garments(garments, tp, "通勤")
    top = cats["上装"][0]["garment"]["name"]
    assert top == "简约衬衫"  # 风格匹配通勤得更高分
