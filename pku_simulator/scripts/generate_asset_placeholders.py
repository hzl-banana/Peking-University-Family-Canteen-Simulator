from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = PROJECT_ROOT / "assets" / "placeholders"
POSITION_DOC = PROJECT_ROOT / "assets" / "asset_positions.json"

CATEGORY_DIRS = {
    "functional": "功能性图片",
    "tools": "厨具图片",
    "ingredients": "食材图片",
    "labels": "标签名字图片",
}

CATEGORY_COLORS = {
    "functional": (245, 220, 176),
    "tools": (196, 214, 224),
    "ingredients": (201, 231, 193),
    "labels": (245, 245, 245),
}

BACKGROUND_SIZE = (8640, 5592)

RAW_ASSETS: dict[str, list[str]] = {
    "functional": [
        "开局背景.jpg",
        "价格背景按钮.jpg",
        "购买红色背景按钮.jpg",
        "购买灰色背景按钮.jpg",
        "出锅红色背景按钮.jpg",
        "出锅灰色背景按钮.jpg",
        "完成采购红色背景按钮.jpg",
        "完成采购灰色背景按钮.jpg",
        "开局按钮.jpg",
        "商场背景.jpg",
        "烤盘区背景.jpg",
        "计时器背景.jpg",
        "点餐台背景.jpg",
        "聊天框背景.jpg",
        "聊天中的清单背景.jpg",
        "被查看的清单背景.jpg",
        "悬挂的清单.jpg",
        "顾客A.jpg",
        "顾客B.jpg",
        "顾客C.jpg",
        "顾客D.jpg",
        "顾客E.jpg",
        "顾客F.jpg",
        "顾客G.jpg",
        "主食区背景.jpg",
        "烧烤区背景.jpg",
    ],
    "tools": [
        "垃圾桶.jpg",
        "烤盘.jpg",
        "烤盘盖子.jpg",
        "损坏的烤盘.jpg",
        "破洞的烤台.jpg",
        "电饭煲.jpg",
        "爆炸的电饭煲.jpg",
    ],
    "ingredients": [
        "面筋.jpg",
        "槽里的面筋.png",
        "玉米粒.jpg",
        "槽里的玉米粒.png",
        "土豆片.jpg",
        "槽里的土豆片.png",
        "鸡肉.jpg",
        "槽里的鸡肉.png",
        "五花肉.jpg",
        "槽里的五花肉.png",
        "培根片.jpg",
        "槽里的培根片.png",
        "青菜.jpg",
        "槽里的青菜.png",
        "大白菜.jpg",
        "槽里的大白菜.png",
        "冻豆腐.jpg",
        "槽里的冻豆腐.png",
        "鱼丸.jpg",
        "槽里的鱼丸.png",
        "鱼豆腐.png",
        "槽里的鱼豆腐.png",
        "冻豆腐.jpg",
        "腐竹片.jpg",
        "槽里的腐竹片.png",
        "肠粉面糊.jpg",
        "鲜虾.jpg",
        "鸡蛋.jpg",
        "水杯.jpg",
        "米堆.jpg",
        "生羊肉串.jpg",
        "生鸡翅串.jpg",
        "生腰子串.jpg",
        "生尖椒串.jpg",
        "生面筋串.jpg",
        "生烤肠串.jpg",
        "熟羊肉串.jpg",
        "熟鸡翅串.jpg",
        "熟腰子串.jpg",
        "熟尖椒串.jpg",
        "熟面筋串.jpg",
        "熟烤肠串.jpg",
        "孜然粉罐.jpg",
        "辣椒粉罐.jpg",
        "孜然粉.jpg（非卖）",
        "辣椒粉.jpg（非卖）",
    ],
    "labels": [
        "面筋标签.jpg",
        "玉米粒标签.jpg",
        "土豆片标签.jpg",
        "鸡肉标签.jpg",
        "五花肉标签.jpg",
        "培根片标签.jpg",
        "青菜标签.jpg",
        "大白菜标签.jpg",
        "冻豆腐标签.jpg",
        "鱼丸标签.jpg",
        "冻豆腐标签.jpg",
        "腐竹片标签.jpg",
        "肠粉面糊标签.jpg",
        "鲜虾标签.jpg",
        "鸡蛋标签.jpg",
        "水杯标签.jpg",
        "米堆标签.jpg",
        "羊肉串标签.jpg",
        "鸡翅串标签.jpg",
        "腰子串标签.jpg",
        "尖椒串标签.jpg",
        "面筋串标签.jpg",
        "烤肠串标签.jpg",
        "孜然粉标签.jpg",
        "辣椒粉标签.jpg",
    ],
}

INVENTORY_KEYS_BY_ASSET_NAME = {
    "槽里的面筋.png": "gluten",
    "槽里的玉米粒.png": "corn",
    "槽里的土豆片.png": "potato_slice",
    "槽里的鸡肉.png": "chicken",
    "槽里的五花肉.png": "pork_belly",
    "槽里的培根片.png": "bacon",
    "槽里的青菜.png": "greens",
    "槽里的大白菜.png": "cabbage",
    "槽里的冻豆腐.png": "tofu",
    "槽里的鱼丸.png": "fish_ball",
    "槽里的鱼豆腐.png": "fish_tofu",
    "槽里的腐竹片.png": "bean_curd_sheet",
}

SHOP_PRODUCT_LAYOUT = [
    ("gluten", "面筋.jpg"),
    ("corn", "玉米粒.jpg"),
    ("potato_slice", "土豆片.jpg"),
    ("chicken", "鸡肉.jpg"),
    ("pork_belly", "五花肉.jpg"),
    ("bacon", "培根片.jpg"),
    ("greens", "青菜.jpg"),
    ("cabbage", "大白菜.jpg"),
    ("tofu", "冻豆腐.jpg"),
    ("fish_ball", "鱼丸.jpg"),
    ("fish_tofu", "鱼豆腐.png"),
    ("bean_curd_sheet", "腐竹片.jpg"),
    ("rice_batter", "肠粉面糊.jpg"),
    ("shrimp", "鲜虾.jpg"),
    ("egg", "鸡蛋.jpg"),
    ("rice", "米堆.jpg"),
    ("water", "水杯.jpg"),
    ("raw_lamb_skewer", "生羊肉串.jpg"),
    ("raw_chicken_wing_skewer", "生鸡翅串.jpg"),
    ("raw_kidney_skewer", "生腰子串.jpg"),
    ("raw_pepper_skewer", "生尖椒串.jpg"),
    ("raw_gluten_skewer", "生面筋串.jpg"),
    ("raw_sausage_skewer", "生烤肠串.jpg"),
    ("cumin", "孜然粉罐.jpg"),
    ("chili", "辣椒粉罐.jpg"),
]


def clean_name(name: str) -> str:
    return name.replace("（非卖）", "").strip()


def dedupe_assets(raw: dict[str, list[str]]) -> dict[str, list[str]]:
    deduped: dict[str, list[str]] = {}
    for category, names in raw.items():
        seen: set[str] = set()
        ordered: list[str] = []
        for item in names:
            cleaned = clean_name(item)
            if cleaned in seen:
                continue
            seen.add(cleaned)
            ordered.append(cleaned)
        deduped[category] = ordered
    return deduped


def choose_size(category: str, name: str) -> tuple[int, int]:
    if "按钮" in name:
        return (360, 120)
    if "计时器" in name:
        return (420, 140)
    if "聊天框" in name:
        return (620, 340)
    if "清单" in name:
        return (420, 260)
    if name.startswith("顾客"):
        return (300, 460)
    if "标签" in name:
        return (300, 90)
    if "背景" in name:
        return BACKGROUND_SIZE

    if category == "tools":
        return (260, 220)
    if category == "ingredients":
        return (220, 200)
    if category == "labels":
        return (300, 90)

    return (320, 200)


def guess_scene(name: str, category: str) -> str:
    if name.startswith("槽里的"):
        return "griddle_station"
    if "开局" in name:
        return "start_screen"
    if "商场" in name or "购买" in name or "价格" in name or "完成采购" in name:
        return "shop_screen"
    if "点餐台" in name or "聊天" in name or "清单" in name or name.startswith("顾客"):
        return "counter_station"
    if "主食" in name or "电饭煲" in name or name in {"米堆.jpg", "水杯.jpg", "米堆标签.jpg", "水杯标签.jpg"}:
        return "staple_station"
    if "烧烤" in name or "串" in name or "孜然" in name or "辣椒" in name:
        return "bbq_station"
    if "肠粉" in name or name in {"鲜虾.jpg", "鸡蛋.jpg", "鲜虾标签.jpg", "鸡蛋标签.jpg"}:
        return "cheung_fun_station"
    if "烤盘" in name or "计时器" in name or "垃圾桶" in name or name == "破洞的烤台.jpg":
        return "griddle_station"
    if category == "labels":
        return "shared_labels"
    if category == "ingredients":
        return "shared_ingredients"
    return "shared"


def default_layer(name: str) -> int:
    if "背景" in name:
        return 0
    if name.startswith("槽里的"):
        return 35
    if "按钮" in name:
        return 70
    if "清单" in name or "聊天" in name:
        return 65
    if "标签" in name:
        return 60
    if name.startswith("顾客"):
        return 50
    return 40


def load_font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
    ]
    for font_path in candidates:
        try:
            return ImageFont.truetype(font_path, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def create_placeholder(path: Path, size: tuple[int, int], color: tuple[int, int, int], title: str, category_title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)

    border = (65, 65, 65)
    draw.rectangle((6, 6, size[0] - 7, size[1] - 7), outline=border, width=3)

    font_title = load_font(max(22, min(48, size[0] // 12)))
    font_meta = load_font(max(18, min(36, size[0] // 20)))

    title_bbox = draw.textbbox((0, 0), title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]

    meta_1 = category_title
    meta_2 = f"{size[0]} x {size[1]}"

    draw.text(((size[0] - title_w) / 2, size[1] * 0.34 - title_h / 2), title, fill=(30, 30, 30), font=font_title)
    draw.text((size[0] * 0.08, size[1] * 0.68), meta_1, fill=(50, 50, 50), font=font_meta)
    draw.text((size[0] * 0.08, size[1] * 0.78), meta_2, fill=(50, 50, 50), font=font_meta)

    if path.suffix.lower() == ".png":
        image.save(path, format="PNG")
    else:
        image.save(path, format="JPEG", quality=90)


def build_position_doc(assets: dict[str, list[str]]) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    for category, names in assets.items():
        for idx, name in enumerate(names):
            size = choose_size(category, name)
            scene = guess_scene(name, category)
            entries[name] = {
                "path": f"assets/placeholders/{CATEGORY_DIRS[category]}/{name}",
                "category": category,
                "scene": scene,
                "position": {
                    "x": 0,
                    "y": 0,
                    "width": size[0],
                    "height": size[1],
                    "anchor": "top-left",
                    "layer": default_layer(name),
                },
                "visible": True,
                "note": "修改 x/y/width/height/layer 以调整布局",
                "order": idx,
            }
            inventory_key = INVENTORY_KEYS_BY_ASSET_NAME.get(name)
            if inventory_key:
                entries[name]["inventory_key"] = inventory_key

    columns = 4
    start_x = 620
    start_y = 760
    cell_w = 1880
    row_h = 760
    image_size = 430
    for idx, (product_key, source_name) in enumerate(SHOP_PRODUCT_LAYOUT):
        source = entries.get(source_name)
        if source is None:
            continue

        row = idx // columns
        col = idx % columns
        name = f"商场商品_{source_name}"
        entries[name] = {
            "path": source["path"],
            "category": "shop_item",
            "scene": "shop_screen",
            "position": {
                "x": start_x + col * cell_w + 120,
                "y": start_y + row * row_h,
                "width": image_size,
                "height": image_size,
                "anchor": "top-left",
                "layer": 120,
            },
            "visible": True,
            "product_key": product_key,
            "source_asset": source_name,
            "note": "商场商品图片，可在布局拖拽模式中调整位置和大小。",
            "order": 3000 + idx,
        }

    return {
        "meta": {
            "coordinate_system": "screen_px",
            "origin": "top-left",
            "description": "所有占位图的默认位置文档，后续调布局只改此文件。",
        },
        "assets": entries,
    }


def main() -> None:
    assets = dedupe_assets(RAW_ASSETS)

    total = 0
    for category, names in assets.items():
        category_title = CATEGORY_DIRS[category]
        color = CATEGORY_COLORS[category]

        for name in names:
            size = choose_size(category, name)
            output = ASSET_ROOT / category_title / name
            create_placeholder(output, size, color, name, category_title)
            total += 1

    position_doc = build_position_doc(assets)
    POSITION_DOC.write_text(json.dumps(position_doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Generated {total} placeholder images.")
    print(f"Wrote position document: {POSITION_DOC}")


if __name__ == "__main__":
    main()
