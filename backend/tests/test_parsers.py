"""解析器单测：宽容解析 + 枚举归一化。"""
from app.services import parsers


def test_parse_garment_tags_normal():
    raw = '{"name":"白色衬衫","category":"上装","color":"白","pattern":"纯色","material":"棉","fit":"合身","season":"四季","style":"简约"}'
    tags = parsers.parse_garment_tags(raw)
    assert tags["category"] == "上装"
    assert tags["color"] == "白"
    assert tags["material"] == "棉"


def test_parse_garment_tags_with_fence_and_aliases():
    raw = '```json\n{"category":"牛仔裤","color":"藏蓝色","material":"牛仔布","fit":"宽松"}\n```'
    tags = parsers.parse_garment_tags(raw)
    assert tags["category"] == "下装"   # 牛仔裤 → 下装
    assert tags["color"] == "藏青"      # 藏蓝色 → 藏青
    assert tags["material"] == "牛仔"   # 牛仔布 → 牛仔
    assert tags["fit"] == "宽松"
    # 缺失字段给默认
    assert tags["pattern"] == "不确定"
    assert tags["season"] == "不确定"


def test_parse_garment_tags_missing_all():
    tags = parsers.parse_garment_tags('{"foo":"bar"}')
    assert tags["category"] == "不确定"
    assert tags["name"] == ""


def test_parse_outfit_plan_normal():
    raw = '{"outfits":[{"name":"A","items":{"上装":"衬衫"},"reasons":["r1"],"scores":{"场景":8}}]}'
    plan = parsers.parse_outfit_plan(raw)
    assert len(plan["outfits"]) == 1
    assert plan["outfits"][0]["name"] == "A"


def test_parse_outfit_plan_truncates_to_3():
    raw = '{"outfits":[' + ",".join(f'{{"name":"o{i}"}}' for i in range(6)) + ']}'
    plan = parsers.parse_outfit_plan(raw)
    assert len(plan["outfits"]) == 3


def test_parse_outfit_plan_invalid_raises():
    import pytest
    with pytest.raises(ValueError):
        parsers.parse_outfit_plan('{"hello":"world"}')
