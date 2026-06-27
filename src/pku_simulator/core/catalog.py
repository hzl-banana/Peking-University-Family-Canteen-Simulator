"""食材目录。

`CATALOG` 是价格、中文名、分类和保质期的单一来源；商店、订单生成、库存
提示和出餐结算都通过 key 回查这里。
"""

from pku_simulator.core.models import IngredientCategory, IngredientDef


def _make(
    key: str,
    name: str,
    price: float,
    category: IngredientCategory,
    max_age_days: int,
) -> IngredientDef:
    """保持目录定义简短，避免每个条目重复写字段名。"""
    return IngredientDef(
        key=key,
        name=name,
        price=price,
        category=category,
        max_age_days=max_age_days,
    )


# 商店展示顺序默认沿用 CATALOG 的插入顺序。
CATALOG: dict[str, IngredientDef] = {
    "gluten": _make("gluten", "面筋", 6.0, IngredientCategory.VEGETABLE, 1),
    "corn": _make("corn", "玉米粒", 5.0, IngredientCategory.VEGETABLE, 1),
    "potato_slice": _make("potato_slice", "土豆片", 5.0, IngredientCategory.VEGETABLE, 1),
    "chicken": _make("chicken", "鸡肉", 10.0, IngredientCategory.MEAT, 1),
    "pork_belly": _make("pork_belly", "五花肉", 12.0, IngredientCategory.MEAT, 1),
    "bacon": _make("bacon", "培根片", 11.0, IngredientCategory.MEAT, 1),
    "greens": _make("greens", "青菜", 4.0, IngredientCategory.VEGETABLE, 1),
    "cabbage": _make("cabbage", "大白菜", 4.0, IngredientCategory.VEGETABLE, 1),
    "tofu": _make("tofu", "冻豆腐", 6.0, IngredientCategory.VEGETABLE, 1),
    "fish_ball": _make("fish_ball", "鱼丸", 8.0, IngredientCategory.MEAT, 1),
    "fish_tofu": _make("fish_tofu", "鱼豆腐", 8.0, IngredientCategory.MEAT, 1),
    "bean_curd_sheet": _make("bean_curd_sheet", "腐竹片", 6.0, IngredientCategory.VEGETABLE, 1),
    "rice_batter": _make("rice_batter", "肠粉面糊", 7.0, IngredientCategory.OTHER, 1),
    "shrimp": _make("shrimp", "鲜虾", 12.0, IngredientCategory.MEAT, 1),
    "egg": _make("egg", "鸡蛋", 3.0, IngredientCategory.MEAT, 1),
    "rice": _make("rice", "米堆", 2.0, IngredientCategory.STAPLE, 999),
    "water": _make("water", "水杯", 1.0, IngredientCategory.STAPLE, 999),
    "raw_lamb_skewer": _make(
        "raw_lamb_skewer", "生羊肉串", 6.0, IngredientCategory.SKEWER, 1
    ),
    "raw_chicken_wing_skewer": _make(
        "raw_chicken_wing_skewer", "生鸡翅串", 7.0, IngredientCategory.SKEWER, 1
    ),
    "raw_kidney_skewer": _make(
        "raw_kidney_skewer", "生腰子串", 7.0, IngredientCategory.SKEWER, 1
    ),
    "raw_pepper_skewer": _make(
        "raw_pepper_skewer", "生尖椒串", 4.0, IngredientCategory.SKEWER, 1
    ),
    "raw_gluten_skewer": _make(
        "raw_gluten_skewer", "生面筋串", 4.0, IngredientCategory.SKEWER, 1
    ),
    "raw_sausage_skewer": _make(
        "raw_sausage_skewer", "生烤肠串", 6.0, IngredientCategory.SKEWER, 1
    ),
    "cumin": _make("cumin", "孜然粉", 3.0, IngredientCategory.SEASONING, 999),
    "chili": _make("chili", "辣椒粉", 3.0, IngredientCategory.SEASONING, 999),
}

SHOP_LIST: list[str] = list(CATALOG.keys())
