"""Qt 资源名、坐标和绘制常量。

这个文件是图形层的“索引表”：把业务食材 key 映射到素材名，把工作台槽位映射
到画布坐标，并提供几个覆盖层通用的动画/颜色 helper。
"""

from __future__ import annotations

from PySide6.QtCore import QRectF

from pku_simulator.core.catalog import CATALOG
from pku_simulator.core.models import IngredientCategory


# 商店和烤盘素材 key 映射：业务层只认识英文 key，图形层用中文文件名。
SHOP_ASSET_NAMES_BY_KEY = {
    "gluten": "面筋.jpg",
    "corn": "玉米粒.jpg",
    "potato_slice": "土豆片.jpg",
    "chicken": "鸡肉.jpg",
    "pork_belly": "五花肉.jpg",
    "bacon": "培根片.jpg",
    "greens": "青菜.jpg",
    "cabbage": "大白菜.jpg",
    "tofu": "冻豆腐.jpg",
    "fish_ball": "鱼丸.jpg",
    "fish_tofu": "鱼豆腐.png",
    "bean_curd_sheet": "腐竹片.jpg",
    "rice_batter": "淀粉面糊.png",
    "shrimp": "鲜虾.jpg",
    "egg": "鸡蛋.jpg",
    "rice": "米堆.jpg",
    "water": "水杯.jpg",
    "raw_lamb_skewer": "生羊肉串.jpg",
    "raw_chicken_wing_skewer": "生鸡翅串.jpg",
    "raw_kidney_skewer": "生腰子串.jpg",
    "raw_pepper_skewer": "生尖椒串.jpg",
    "raw_gluten_skewer": "生面筋串.jpg",
    "raw_sausage_skewer": "生烤肠串.jpg",
    "cumin": "孜然粉罐.jpg",
    "chili": "辣椒粉罐.jpg",
}

SHOP_LAYOUT_ASSET_NAMES_BY_KEY = {
    key: f"商场商品_{asset_name}"
    for key, asset_name in SHOP_ASSET_NAMES_BY_KEY.items()
}

ASSET_NAMES_BY_GRIDDLE_KEY = {
    "gluten": "面筋.jpg",
    "corn": "玉米粒.jpg",
    "potato_slice": "土豆片.jpg",
    "chicken": "鸡肉.jpg",
    "pork_belly": "五花肉.jpg",
    "bacon": "培根片.jpg",
    "greens": "青菜.jpg",
    "cabbage": "大白菜.jpg",
    "tofu": "冻豆腐.jpg",
    "fish_ball": "鱼丸.jpg",
    "fish_tofu": "鱼豆腐.png",
    "bean_curd_sheet": "腐竹片.jpg",
}

GRIDDLE_KEYS_BY_ASSET_NAME = {
    asset_name: key
    for key, asset_name in ASSET_NAMES_BY_GRIDDLE_KEY.items()
}

# 烤盘间：锅、锅盖、损坏态、热区和计时参数。
GRIDDLE_PAN_ASSET_NAMES = [
    "烤盘1.png",
    "烤盘2.png",
    "烤盘3.png",
    "烤盘4.png",
]

GRIDDLE_LID_ASSET_NAMES = [
    "烤盘盖子1.png",
    "烤盘盖子2.png",
    "烤盘盖子3.png",
    "烤盘盖子4.png",
]

GRIDDLE_DAMAGED_ASSET_NAMES = [
    "损坏的烤盘1.jpg",
    "损坏的烤盘2.jpg",
    "损坏的烤盘3.jpg",
    "损坏的烤盘4.jpg",
]

GRIDDLE_OUT_HOTZONE_ASSET_NAMES = [
    "出锅透明热区1",
    "出锅透明热区2",
    "出锅透明热区3",
    "出锅透明热区4",
]

GRIDDLE_DYNAMIC_ASSET_NAMES = set(
    GRIDDLE_LID_ASSET_NAMES
    + GRIDDLE_DAMAGED_ASSET_NAMES
    + GRIDDLE_OUT_HOTZONE_ASSET_NAMES
    + [
        "破洞的烤台.jpg",
        "计时器背景.jpg",
        "出锅红色背景按钮.jpg",
        "出锅灰色背景按钮.jpg",
    ]
)

GRIDDLE_VEGETABLE_COOK_SECONDS = 5.0
GRIDDLE_MEAT_COOK_SECONDS = 10.0
GRIDDLE_OVERCOOK_SECONDS = 45.0

GRIDDLE_PAN_RECTS = [
    QRectF(4200, 350, 1555, 1080),
    QRectF(6200, 350, 1555, 1080),
    QRectF(4200, 1850, 1555, 1080),
    QRectF(6200, 1850, 1555, 1080),
]

# 肠粉台：勺子、配料、烤台组合态和命中热区。
CHEUNG_FUN_EMPTY_SPOON_ASSET_NAME = "空的面糊勺.png"
CHEUNG_FUN_FILLED_SPOON_ASSET_NAME = "装着面糊的面糊勺.png"
CHEUNG_FUN_SPATULA_ASSET_NAME = "炒勺.png"
CHEUNG_FUN_FINISHED_ASSET_NAME = "成品肠粉.png"
CHEUNG_FUN_INGREDIENT_ASSET_KEYS = {
    "鸡蛋.png": "egg",
    "鲜虾.png": "shrimp",
}
CHEUNG_FUN_INVENTORY_ASSET_NAMES_BY_KEY = {
    "egg": {"一筐鸡蛋.png", "鸡蛋.png"},
    "shrimp": {"盒装鲜虾.png", "鲜虾.png"},
}
CHEUNG_FUN_KEY_BY_INVENTORY_ASSET_NAME = {
    asset_name: key
    for key, asset_names in CHEUNG_FUN_INVENTORY_ASSET_NAMES_BY_KEY.items()
    for asset_name in asset_names
}
CHEUNG_FUN_LEFT_ASSET_NAMES_BY_INGREDIENTS = {
    frozenset(): ("左侧的肠粉.png", "左侧的肠粉2.png"),
    frozenset({"egg"}): ("左侧的鸡蛋肠粉.png", "左侧的鸡蛋肠粉2.png"),
    frozenset({"shrimp"}): ("左侧的鲜虾肠粉.png", "左侧的鲜虾肠粉2.png"),
    frozenset({"egg", "shrimp"}): ("左侧的鸡蛋鲜虾肠粉.png", "左侧的鸡蛋鲜虾肠粉2.png"),
}
CHEUNG_FUN_RIGHT_ASSET_NAMES_BY_INGREDIENTS = {
    frozenset(): ("右侧的肠粉.png", "右侧的肠粉2.png"),
    frozenset({"egg"}): ("右侧的鸡蛋肠粉.png", "右侧的鸡蛋肠粉2.png"),
    frozenset({"shrimp"}): ("右侧的鲜虾肠粉.png", "右侧的鲜虾肠粉2.png"),
    frozenset({"egg", "shrimp"}): ("右侧的鸡蛋鲜虾肠粉.png", "右侧的鸡蛋鲜虾肠粉2.png"),
}
CHEUNG_FUN_FINISHED_ASSET_NAMES = (
    CHEUNG_FUN_FINISHED_ASSET_NAME,
    "成品肠粉2.png",
    "成品肠粉3.png",
    "成品肠粉4.png",
)
CHEUNG_FUN_DAMAGED_ASSET_NAMES = (
    "左侧的破洞烤台.png",
    "右侧的破洞烤台.png",
    "左侧的破洞烤台2.png",
    "右侧的破洞烤台2.png",
)
CHEUNG_FUN_RECIPE_ASSET_NAMES = {
    asset_name
    for asset_pair in (
        *CHEUNG_FUN_LEFT_ASSET_NAMES_BY_INGREDIENTS.values(),
        *CHEUNG_FUN_RIGHT_ASSET_NAMES_BY_INGREDIENTS.values(),
        CHEUNG_FUN_FINISHED_ASSET_NAMES,
        CHEUNG_FUN_DAMAGED_ASSET_NAMES,
    )
    for asset_name in asset_pair
}
CHEUNG_FUN_DYNAMIC_ASSET_NAMES = {
    CHEUNG_FUN_EMPTY_SPOON_ASSET_NAME,
    CHEUNG_FUN_FILLED_SPOON_ASSET_NAME,
    *CHEUNG_FUN_RECIPE_ASSET_NAMES,
}
CHEUNG_FUN_SUPPRESSED_STATIC_ASSET_NAMES = {
    "肠粉面糊.jpg",
    "鲜虾.jpg",
    "鸡蛋.jpg",
}
CHEUNG_FUN_BATTER_HOTZONE_RECT = QRectF(1050, 2850, 2050, 1220)
CHEUNG_FUN_PAN_RECTS = [
    QRectF(4020, 1980, 1840, 650),
    QRectF(5920, 1980, 1840, 650),
    QRectF(4020, 2720, 1840, 720),
    QRectF(5920, 2720, 1840, 720),
]
CHEUNG_FUN_BATTER_COOK_SECONDS = 5.0
CHEUNG_FUN_OVERCOOK_SECONDS = 45.0

# 主食区：背景、电饭煲槽位、米/水源和状态素材。
STAPLE_EMPTY_BACKGROUND_ASSET_NAME = "没米的主食区背景.png"
STAPLE_FILLED_BACKGROUND_ASSET_NAME = "有米的主食区背景.png"
STAPLE_BACKGROUND_ASSET_NAMES = {
    STAPLE_EMPTY_BACKGROUND_ASSET_NAME,
    STAPLE_FILLED_BACKGROUND_ASSET_NAME,
}
STAPLE_SOURCE_ASSET_KEYS = {
    "米堆.jpg": "rice",
    "水杯.jpg": "water",
    "水杯2.jpg": "water",
}
STAPLE_COOKER_SLOT_ASSET_NAMES = [
    f"电饭煲{index}.png"
    for index in range(1, 7)
]
STAPLE_DEFAULT_COOKER_RECTS = [
    QRectF(3150 + col * 1450, 1320 + row * 1640, 1050, 1120)
    for row in range(2)
    for col in range(3)
]
STAPLE_COOKER_ASSET_NAMES_BY_STATE = {
    "empty": "空的电饭煲.png",
    "rice": "有米没水的电饭煲.png",
    "water": "有水的电饭煲.png",
    "ready": "有水有米的电饭煲.png",
    "cooking": "正在蒸饭的电饭煲.png",
    "done": "蒸饭完成的电饭煲.png",
}
STAPLE_DYNAMIC_ASSET_NAMES = (
    set(STAPLE_COOKER_SLOT_ASSET_NAMES)
    | set(STAPLE_COOKER_ASSET_NAMES_BY_STATE.values())
    | STAPLE_BACKGROUND_ASSET_NAMES
    | set(STAPLE_SOURCE_ASSET_KEYS.keys())
    | {"主食区背景.jpg", "电饭煲.jpg", "爆炸的电饭煲.jpg"}
)
STAPLE_RICE_COOK_SECONDS = 30.0

# 点餐台：顾客弹入、票据、挂单栏和逐行显示动画参数。
COUNTER_DESK_ASSET_NAME = "点餐台桌面.png"
COUNTER_CUSTOMER_FINAL_RECT = QRectF(760, 1800, 1640, 2300)
COUNTER_CUSTOMER_POP_DISTANCE = 1180
COUNTER_CUSTOMER_POP_SECONDS = 0.62
COUNTER_ORDER_TICKET_RECT = QRectF(2500, 980, 3150, 3580)
COUNTER_HANGING_TICKET_WIDTH = 700
COUNTER_HANGING_TICKET_HEIGHT = 435
COUNTER_HANGING_TICKET_GAP = 44
COUNTER_HANGING_TICKET_Y = 375
COUNTER_HANGING_TICKET_START_X = 700
COUNTER_HANGING_ANIMATION_SECONDS = 0.46
COUNTER_LINE_REVEAL_SECONDS = 0.36

# 烧烤架：槽位、烤串方向/熟度素材、调料和烟雾效果。
BBQ_GRILL_HOTZONE_RECT = QRectF(1380, 2740, 6100, 1500)
BBQ_SKEWER_COOK_SECONDS = 20.0
BBQ_SLOT_ASSET_NAMES = [
    f"烧烤架热区{index}"
    for index in range(1, 13)
]
BBQ_MIDDLE_SLOT_INDEXES = frozenset(range(3, 9))
BBQ_RIGHT_SLOT_INDEXES = frozenset(range(9, 12))
BBQ_DEFAULT_SLOT_RECTS = [
    QRectF(1500 + col * 500, 3020, 360, 900)
    for col in range(12)
]
BBQ_SLOT_SNAP_MAX_DISTANCE = 720.0
BBQ_RAW_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "生羊肉串.jpg",
    "raw_chicken_wing_skewer": "生鸡翅串.jpg",
    "raw_kidney_skewer": "生腰子串.jpg",
    "raw_pepper_skewer": "生尖椒串.jpg",
    "raw_gluten_skewer": "生面筋串.jpg",
    "raw_sausage_skewer": "生烤肠串.jpg",
}
BBQ_LEFT_COOKING_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "左羊肉串.png",
    "raw_chicken_wing_skewer": "左鸡翅.png",
    "raw_kidney_skewer": "左腰子.png",
    "raw_pepper_skewer": "左尖椒.png",
    "raw_gluten_skewer": "左面筋.png",
    "raw_sausage_skewer": "左烤肠.png",
}
BBQ_RIGHT_COOKING_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "右羊肉串.png",
    "raw_chicken_wing_skewer": "右鸡翅.png",
    "raw_kidney_skewer": "右腰子.png",
    "raw_pepper_skewer": "右尖椒.png",
    "raw_gluten_skewer": "右面筋.png",
    "raw_sausage_skewer": "右烤肠.png",
}
BBQ_RACKED_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "架子上的羊肉串.png",
    "raw_chicken_wing_skewer": "架子上的鸡翅.png",
    "raw_kidney_skewer": "架子上的腰子.png",
    "raw_pepper_skewer": "架子上的尖椒.png",
    "raw_gluten_skewer": "架子上的面筋.png",
    "raw_sausage_skewer": "架子上的烤肠.png",
}
BBQ_MIDDLE_COOKING_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "中羊肉串.png",
    "raw_chicken_wing_skewer": "中鸡翅.png",
    "raw_kidney_skewer": "中腰子.png",
    "raw_pepper_skewer": "中尖椒.png",
    "raw_gluten_skewer": "中面筋.png",
    "raw_sausage_skewer": "中烤肠.png",
}
BBQ_LEFT_COOKED_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "左熟羊肉串.png",
    "raw_chicken_wing_skewer": "左熟鸡翅.png",
    "raw_kidney_skewer": "左熟腰子.png",
    "raw_pepper_skewer": "左熟尖椒.png",
    "raw_gluten_skewer": "左熟面筋.png",
    "raw_sausage_skewer": "左熟烤肠.png",
}
BBQ_MIDDLE_COOKED_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "中熟羊肉串.png",
    "raw_chicken_wing_skewer": "中熟鸡翅.png",
    "raw_kidney_skewer": "中熟腰子.png",
    "raw_pepper_skewer": "中熟尖椒.png",
    "raw_gluten_skewer": "中熟面筋.png",
    "raw_sausage_skewer": "中熟烤肠.png",
}
BBQ_RIGHT_COOKED_SKEWER_ASSET_NAMES_BY_KEY = {
    "raw_lamb_skewer": "右熟羊肉串.png",
    "raw_chicken_wing_skewer": "右熟鸡翅.png",
    "raw_kidney_skewer": "右熟腰子.png",
    "raw_pepper_skewer": "右熟尖椒.png",
    "raw_gluten_skewer": "右熟面筋.png",
    "raw_sausage_skewer": "右熟烤肠.png",
}
BBQ_SKEWER_KEYS_BY_ASSET_NAME = {
    asset_name: key
    for key, asset_name in BBQ_RAW_SKEWER_ASSET_NAMES_BY_KEY.items()
}
BBQ_OLD_COOKED_SKEWER_ASSET_NAMES = {
    "熟羊肉串.jpg",
    "熟鸡翅串.jpg",
    "熟腰子串.jpg",
    "熟尖椒串.jpg",
    "熟面筋串.jpg",
    "熟烤肠串.jpg",
}
BBQ_DYNAMIC_SKEWER_ASSET_NAMES = (
    set(BBQ_LEFT_COOKING_SKEWER_ASSET_NAMES_BY_KEY.values())
    | set(BBQ_RIGHT_COOKING_SKEWER_ASSET_NAMES_BY_KEY.values())
    | set(BBQ_MIDDLE_COOKING_SKEWER_ASSET_NAMES_BY_KEY.values())
    | set(BBQ_LEFT_COOKED_SKEWER_ASSET_NAMES_BY_KEY.values())
    | set(BBQ_RIGHT_COOKED_SKEWER_ASSET_NAMES_BY_KEY.values())
    | set(BBQ_MIDDLE_COOKED_SKEWER_ASSET_NAMES_BY_KEY.values())
)
BBQ_SEASONING_ASSET_KEYS = {
    "孜然粉罐.jpg": "cumin",
    "辣椒粉罐.jpg": "chili",
}
BBQ_TILTED_SEASONING_ASSET_NAMES = {
    "cumin": "倾斜的胡椒粉罐.png",
    "chili": "倾斜的辣椒粉罐.png",
}
BBQ_SEASONING_PARTICLE_COLORS = {
    "cumin": "#8B5A2B",
    "chili": "#8F1D1D",
}
BBQ_SUPPRESSED_STATIC_ASSET_NAMES = (
    set(BBQ_TILTED_SEASONING_ASSET_NAMES.values())
    | BBQ_OLD_COOKED_SKEWER_ASSET_NAMES
    | BBQ_DYNAMIC_SKEWER_ASSET_NAMES
    | set(BBQ_SLOT_ASSET_NAMES)
)
BBQ_LAYOUT_EDITOR_SUPPRESSED_ASSET_NAMES = BBQ_OLD_COOKED_SKEWER_ASSET_NAMES
BBQ_SMOKE_LAYER = 235
BBQ_SMOKE_PARTICLE_COUNT = 14

# 商店覆盖层布局参数。
SHOP_SCENE_HEIGHT = 11600
SHOP_BACKGROUND_ASSET_NAME = "商店背景.png"
SHOP_COLUMNS = 3
SHOP_CARD_W = 2540
SHOP_CARD_H = 900
SHOP_CARD_GAP_X = 160
SHOP_CARD_GAP_Y = 170
SHOP_START_X = 340
SHOP_START_Y = 780
SHOP_LAYOUT_BASE_X = 740
SHOP_LAYOUT_BASE_Y = 760
SHOP_LAYOUT_BASE_STEP_X = 1880
SHOP_LAYOUT_BASE_STEP_Y = 760
SHOP_LAYOUT_BASE_COLUMNS = 4
SHOP_WORKBENCH_PRICE_MULTIPLIER = 1.2
SHOP_CATEGORY_BADGES = {
    IngredientCategory.VEGETABLE: ("蔬菜", "#DCFCE7", "#166534"),
    IngredientCategory.MEAT: ("肉类", "#FEE2E2", "#991B1B"),
    IngredientCategory.STAPLE: ("主食", "#E0F2FE", "#075985"),
    IngredientCategory.SKEWER: ("烤串", "#EDE9FE", "#6B21A8"),
    IngredientCategory.SEASONING: ("调料", "#FEF3C7", "#92400E"),
    IngredientCategory.OTHER: ("其他", "#E2E8F0", "#334155"),
}

MUSIC_GEAR_ASSET_NAME = "齿轮.png"

# 订单临近超时的屏幕嘲讽提示配置。
ORDER_TAUNT_30_SECOND_THRESHOLD = 30.0
ORDER_TAUNT_10_SECOND_THRESHOLD = 10.0
ORDER_TAUNT_DISPLAY_SECONDS = 3.0
ORDER_TAUNT_RISE_PIXELS = 96
ORDER_TAUNT_30_SECOND_LINES = (
    "你行不行啊",
    "老板，锅是不是还没热",
    "我都快把菜单背下来了",
    "这速度，饭都凉了吧",
    "还要我等到下节课吗",
    "再慢点我就自己下厨了",
)
ORDER_TAUNT_10_SECOND_LINES = (
    "就这速度，走喽",
    "最后十秒了，我真要走了",
    "我先撤了，你慢慢忙",
    "这单要凉了，老板",
    "再见了，下次争取快点",
    "不用送了，我已经准备走了",
)


def _alpha_color(rgb: str, opacity: float) -> str:
    """把 #RRGGBB 和透明度转成 Qt 支持的 #AARRGGBB。"""
    alpha = max(0, min(255, int(round(opacity * 255))))
    return f"#{alpha:02X}{rgb.lstrip('#')}"


def _griddle_cook_seconds_for_key(item_key: str) -> float:
    """烤盘计时 helper：肉类 10 秒，非肉类 5 秒。"""
    ingredient = CATALOG.get(item_key)
    if ingredient is not None and ingredient.category == IngredientCategory.MEAT:
        return GRIDDLE_MEAT_COOK_SECONDS
    return GRIDDLE_VEGETABLE_COOK_SECONDS


def _clamped_ratio(value: float) -> float:
    """限制到 0-1，供动画、透明度和音量复用。"""
    return max(0.0, min(1.0, value))


def _ease_out_cubic(value: float) -> float:
    """缓出曲线，覆盖层动画使用。"""
    ratio = _clamped_ratio(value)
    return 1.0 - (1.0 - ratio) ** 3


def _lerp_float(start: float, end: float, ratio: float) -> float:
    """线性插值。"""
    return start + (end - start) * ratio


def _safe_int(value: object, default: int) -> int:
    """布局 JSON 读取容错：无法转 int 时返回默认值。"""
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


__all__ = [
    name
    for name in globals()
    if name.isupper()
    or name in {
        "_alpha_color",
        "_griddle_cook_seconds_for_key",
        "_clamped_ratio",
        "_ease_out_cubic",
        "_lerp_float",
        "_safe_int",
    }
]
