# Scene Asset Index

`assets/asset_positions.json` is the source of truth for asset scene, position, size, and layer data. The image files stay under the existing type-based folders so the tuned layout paths remain stable.

## File Groups

- `assets/placeholders/功能性图片`: scene backgrounds, customer images, UI buttons, tickets, and global icons.
- `assets/placeholders/厨具图片`: pans, cooker states, spoons, trash cans, and appliance damage states.
- `assets/placeholders/食材图片`: shop products, draggable ingredients, raw/cooked skewers, cheung fun variants, rice, water, and seasoning cans.
- `assets/placeholders/标签名字图片`: legacy label images kept for layout compatibility.
- `assets/generated`: generated opening-cover assets.
- `bgm`: screen and service background music.

## Scene Keys

- `start_screen`: opening background, opening button, and global music gear overlay.
- `shop_screen`: shop background, product images, glass product cards, category badges, buy buttons, and purchase-finish controls.
- `griddle_station`: griddle background, pan hitboxes, pan lids, damaged pans, trash can, draggable griddle ingredients, and timer/out-button overlays.
- `cheung_fun_station`: cheung fun background, batter spoon states, spatula, egg/shrimp sources, batter/finished variants, damaged station images, and info overlays.
- `staple_station`: empty/filled staple backgrounds, six cooker slots, cooker state images, rice/water sources, and cooker info overlays.
- `bbq_station`: grill background, hot zones, source skewers, raw/cooked left/middle/right skewer variants, seasoning cans, tilted seasoning cans, and smoke overlays.
- `counter_station`: counter background, desktop foreground, customer images, active order ticket, hanging tickets, zoomed tickets, and cash event overlays.
- `shared`, `shared_ingredients`, `shared_labels`: reusable assets that multiple scenes may see.
- `global_overlay`: global UI assets such as the music gear.

When replacing art, prefer keeping the asset name stable and replacing the file contents or same-stem image format. Moving files is safe only when the matching path in `asset_positions.json` and any web/PWA references are updated together.
