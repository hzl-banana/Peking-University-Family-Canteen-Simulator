# Assets Notes

当前图片资源按“文件类型”存放，按“游戏场景”通过 `assets/asset_positions.json` 绑定到玩法区域。不要只移动图片文件；如果确实要移动，需要同步更新位置文档和 Web/PWA 中的资源引用。

## 资源目录

- `assets/placeholders/功能性图片`
- `assets/placeholders/厨具图片`
- `assets/placeholders/食材图片`
- `assets/placeholders/标签名字图片`
- `assets/generated`
- `bgm`

## 布局文档

- `assets/asset_positions.json`

这个文件记录每个资源的场景、位置、大小、层级和可见状态，是布局拖拽模式保存坐标的来源。

## 场景索引

- `assets/SCENE_INDEX.md`

这里按开局、商店、烤盘间、肠粉台、主食区、烧烤架、点餐台整理了各类资源的用途。

## 批量重建脚本

- `scripts/generate_asset_placeholders.py`

接入正式资源时，优先保持文件名不变，直接替换对应图片内容；资源查找支持同名不同后缀。
