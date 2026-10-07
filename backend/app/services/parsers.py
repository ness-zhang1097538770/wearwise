"""模型输出解析器：宽容解析 + 枚举归一化 + 强校验。

原则（手册第九节"格式约束三件套"）：
1. Prompt 写正反例；
2. 解析器宽容（兼容 # 标题、中文序号、点分编号、markdown 代码块、键名别名）；
3. 数量/内容约束不遵守记瑕疵，不当作解析错误反复重试。
"""
from __future__ import annotations

import json
import re

# ---- 枚举与别名归一化 ----
CATEGORIES = ["上装", "下装", "外套", "连衣裙", "鞋", "包", "配饰", "其他"]
COLORS = ["黑", "白", "灰", "米白", "棕", "藏青", "蓝", "红", "粉", "黄", "绿", "紫", "橙", "不确定"]
PATTERNS = ["纯色", "条纹", "格纹", "印花", "波点", "几何", "其他", "不确定"]
MATERIALS = ["棉", "麻", "羊毛", "羊绒", "真丝", "涤纶", "尼龙", "牛仔", "皮革", "针织", "雪纺", "其他", "不确定"]
FITS = ["修身", "合身", "宽松", "oversize", "不确定"]
SEASONS = ["春", "夏", "秋", "冬", "四季", "不确定"]

_ALIASES: dict[str, dict[str, str]] = {
    "category": {
        "上衣": "上装", "衬衫": "上装", "t恤": "上装", "T恤": "上装", "卫衣": "上装", "毛衣": "上装",
        "针织衫": "上装", "夹克": "外套", "风衣": "外套", "大衣": "外套", "西装": "外套", "羽绒服": "外套",
        "裤子": "下装", "牛仔裤": "下装", "裙子": "下装", "半裙": "下装", "短裤": "下装",
        "连衣裙": "连衣裙", "one piece": "连衣裙",
        "鞋子": "鞋", "靴子": "鞋", "运动鞋": "鞋", "高跟鞋": "鞋", "乐福鞋": "鞋",
        "包": "包", "包包": "包", "手提包": "包",
        "帽子": "配饰", "围巾": "配饰", "腰带": "配饰", "首饰": "配饰", "眼镜": "配饰",
    },
    "color": {
        "黑色": "黑", "白色": "白", "灰色": "灰", "米白色": "米白", "米色": "米白", "驼色": "棕",
        "棕色": "棕", "咖啡色": "棕", "藏蓝色": "藏青", "深蓝": "藏青", "蓝色": "蓝", "红色": "红",
        "粉色": "粉", "黄色": "黄", "绿色": "绿", "紫色": "紫", "橙色": "橙", "卡其色": "米白",
    },
    "pattern": {
        "素色": "纯色", "单色": "纯色", "条纹": "条纹", "横条纹": "条纹", "竖条纹": "条纹",
        "格纹": "格纹", "格子": "格纹", "方格": "格纹", "印花": "印花", "图案": "印花",
        "碎花": "印花", "波点": "波点", "圆点": "波点", "几何": "几何",
    },
    "material": {
        "棉质": "棉", "纯棉": "棉", "亚麻": "麻", "毛": "羊毛", "羊绒": "羊绒", "真丝": "真丝",
        "桑蚕丝": "真丝", "聚酯纤维": "涤纶", "涤纶": "涤纶", "锦纶": "尼龙", "牛仔布": "牛仔",
        "丹宁": "牛仔", "皮质": "皮革", "皮": "皮革", "针织": "针织", "雪纺": "雪纺",
    },
    "fit": {
        "紧身": "修身", "修身": "修身", "合身": "合身", "标准": "合身", "宽松": "宽松",
        "廓形": "宽松", "oversize": "oversize", "宽大": "宽松",
    },
    "season": {
        "春季": "春", "春": "春", "夏季": "夏", "夏": "夏", "秋季": "秋", "秋": "秋",
        "冬季": "冬", "冬": "冬", "四季皆宜": "四季", "全年": "四季",
    },
}

# 键名别名
_KEY_ALIASES = {
    "category": ["category", "品类", "类别", "类型", "type"],
    "color": ["color", "颜色", "colour"],
    "pattern": ["pattern", "图案", "花色", "花纹"],
    "material": ["material", "材质", "面料", "fabric"],
    "fit": ["fit", "版型", "剪裁", "廓形"],
    "season": ["season", "季节", "适用季节"],
    "style": ["style", "风格"],
    "name": ["name", "名称", "名字"],
}


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract_json(text: str) -> dict:
    """从模型输出中提取第一个 JSON 对象；失败抛 ValueError。"""
    text = _strip_fences(text)
    # 直接尝试
    try:
        return json.loads(text)
    except Exception:
        pass
    # 取第一个 {...}
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    # 取第一个 [...]
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    raise ValueError("无法从模型输出中解析 JSON")


def _pick(obj: dict, field: str) -> str | None:
    for key in _KEY_ALIASES.get(field, [field]):
        if key in obj and obj[key] is not None:
            return str(obj[key]).strip()
    return None


def _normalize(value: str | None, field: str) -> str:
    if not value:
        return "不确定"
    v = value.strip()
    aliases = _ALIASES.get(field, {})
    if v in aliases:
        v = aliases[v]
    # 枚举含多值时取第一个命中
    enums = {
        "category": CATEGORIES, "color": COLORS, "pattern": PATTERNS,
        "material": MATERIALS, "fit": FITS, "season": SEASONS,
    }.get(field)
    if enums and v in enums:
        return v
    # 模糊包含匹配（如"藏蓝色"→藏青）
    if aliases:
        for k, target in aliases.items():
            if k in v or v in k:
                return target
    return v if enums is None and v else "不确定"


def parse_garment_tags(text: str) -> dict:
    """解析衣物识别结果。缺失字段给"不确定"，不抛错（识别不完整不阻断保存）。"""
    obj = extract_json(text)
    # 兼容 {category:..., ...} 或 {"tags": {...}}
    src = obj.get("tags", obj) if isinstance(obj.get("tags"), dict) else obj
    return {
        "name": _pick(src, "name") or "",
        "category": _normalize(_pick(src, "category"), "category"),
        "color": _normalize(_pick(src, "color"), "color"),
        "pattern": _normalize(_pick(src, "pattern"), "pattern"),
        "material": _normalize(_pick(src, "material"), "material"),
        "fit": _normalize(_pick(src, "fit"), "fit"),
        "season": _normalize(_pick(src, "season"), "season"),
        "style": _pick(src, "style") or "",
    }


def parse_outfit_plan(text: str) -> dict:
    """解析穿搭方案：{outfits: [3 套]}。每套 {name, items, reasons, scores}。"""
    obj = extract_json(text)
    outfits = obj.get("outfits") or obj.get("方案") or obj.get("list")
    if isinstance(obj, list):
        outfits = obj
    if not isinstance(outfits, list):
        raise ValueError("穿搭方案缺少 outfits 列表")
    parsed = []
    for o in outfits[:3]:  # 最多取 3 套；超过 3 套是瑕疵，直接截断
        items = o.get("items") or o.get("单品") or o.get("搭配") or {}
        reasons = o.get("reasons") or o.get("理由") or o.get("原因") or []
        scores = o.get("scores") or o.get("匹配度") or {}
        parsed.append({
            "name": o.get("name") or o.get("名称") or f"方案 {len(parsed)+1}",
            "items": items if isinstance(items, dict) else {},
            "reasons": reasons if isinstance(reasons, list) else [],
            "scores": scores if isinstance(scores, dict) else {},
        })
    if not parsed:
        raise ValueError("穿搭方案为空")
    return {"outfits": parsed}
