# 北大家园食堂模拟器

一个基于 PySide6 的桌面端经营小游戏。玩家从采购食材开始，进入营业区后在不同工位完成备餐、接单和出餐：烤盘、肠粉台、主食区、烧烤架和点餐台共同组成一天的营业流程。项目目前支持在mac上运行，代码已经拆成较清晰的模块，方便继续扩展玩法和素材。

## 运行环境

- Python 3.10 或更新版本
- macOS / Windows / Linux 均可运行，已主要在 macOS 上调试
- 依赖：PySide6

## 快速开始

在项目根目录执行：

```bash
python -m pip install -e .
python run_qt.py
```

也可以安装后直接运行命令行入口：

```bash
pku-simulator
```

如果本机已经有虚拟环境，建议先激活虚拟环境再安装依赖。

## 项目结构

```text
pku_simulator_release/
├── README.md
├── pyproject.toml
├── run_qt.py
├── pku_simulator.spec
├── assets/
│   ├── asset_positions.json
│   ├── generated/
│   └── placeholders/
├── bgm/
├── save/
├── scripts/
└── src/pku_simulator/
```

几个核心目录的作用：

- `src/pku_simulator/`：游戏主代码。
- `assets/`：图片资源和场景布局配置。`asset_positions.json` 记录每个素材的位置、尺寸、图层和所属场景。
- `bgm/`：背景音乐文件。
- `save/`：开发运行时的本地存档目录。仓库里只保留空目录，不提交个人游玩存档。
- `scripts/`：打包和辅助脚本。

## 代码主线

项目入口很短，真正的装配都在 `qt_app.py`：

```text
run_qt.py / pku_simulator.main
        ↓
QtApp
        ↓
MainWindow
        ↓
GameSceneView + 页面栈 + GameService
```

`MainWindow` 是主窗口，也是各类控制器的汇合点。它负责创建游戏状态、业务服务、图形场景、页面栈和开发用布局编辑器，并把图形场景发出的 Qt signal 接到对应的控制器方法。

主要模块分工如下：

- `qt_app.py`：创建 Qt 应用和主窗口，连接页面、场景和控制器。
- `qt_app_navigation.py`：页面切换、场景同步、重置游戏。
- `qt_scene.py`：图形场景视图，负责加载静态素材并刷新 overlay。
- `qt_scene_drag.py`：鼠标拖拽、投放命中和拖拽动画。
- `qt_scene_drawing.py`：图片、文字、矩形、圆角矩形等绘制辅助。
- `qt_click_router.py`：根据图形项的 `data` 字符串分发点击事件。
- `qt_workbench_drops.py`：把拖拽投放结果转成工作台业务操作。
- `qt_overlays_*.py`：绘制开始页、商店、工作台和点餐台的动态图层。
- `qt_pages_workbench.py`：营业区总控页面，协调各工作台和点餐台。
- `qt_workbench_*.py`：各个工作台的状态和玩法逻辑。
- `services/game_service.py`：购买、库存、订单、出餐、日结和维修扣费等业务规则。
- `core/`：配置、数据模型、食材目录、库存批次和存档读写。

## 交互流程

图形场景本身不直接修改业务数据。它只负责识别“点了什么”或“拖到了哪里”，然后发出 signal：

```text
GameSceneView
  ├─ asset_clicked(str)          -> qt_click_router.py
  ├─ griddle_ingredient_dropped  -> qt_workbench_drops.py
  ├─ bbq_skewer_dropped          -> qt_workbench_drops.py
  └─ staple_ingredient_dropped   -> qt_workbench_drops.py
```

点击事件靠图形项的 `data` 字段区分来源。例如：

- `buy:egg:1`：购买 1 个鸡蛋。
- `dock:bbq_station`：切换到烧烤架。
- `griddle_out:0`：第 1 个烤盘出锅。
- `bbq_finish:2`：第 3 个烧烤槽位出串。
- `counter_serve:5`：为 5 号订单出餐。

这种写法的好处是 overlay 只需要负责绘制和标记 `data`，具体业务统一交给 router、drop controller 和 service。

## 业务数据

`GameState` 是可以保存到 JSON 的整局状态，包含天数、余额、库存、出餐仓和损坏设备。`GameService` 是主要业务入口，负责对 `GameState` 做合法修改。

典型的数据流：

```text
商店购买
  buy:* 点击
  -> ShopControllerMixin.buy_shop_ingredient()
  -> GameService.buy_ingredient()
  -> InventoryManager.add()
  -> save_state()

工作台出餐
  拖拽食材 / 点击出锅
  -> WorkbenchPage 的工作台 mixin
  -> GameService.record_prepared_dish()
  -> prepared_dishes

点餐台出餐
  counter_serve:* 点击
  -> CounterControllerMixin._on_counter_serve_clicked()
  -> GameService.preview_order_match()
  -> GameService.serve_order()
  -> 更新余额、订单和出餐仓
```

## 资源布局

场景素材的位置不写死在代码里，而是集中在：

```text
assets/asset_positions.json
```

运行时由 `AssetLayoutStore` 读取该文件，`GameSceneView` 根据当前 scene 加载素材。项目内也保留了布局编辑器，可以在开发模式下拖拽调整素材位置，再写回 JSON。

开发控件默认隐藏。如需显示布局拖拽模式和后台表格控件，可以设置环境变量：

```bash
PKU_SIMULATOR_DEV_CONTROLS=1 python run_qt.py
```

## 存档

开发运行时，存档写在项目内：

```text
save/game_state.json
```

打包运行时，存档会写到用户目录：

```text
~/.pku_simulator/save/game_state.json
```


## 打包

项目提供了 PyInstaller 打包脚本：

```bash
./scripts/build_executable.sh
```

脚本会把 `assets/` 和 `bgm/` 一起打进产物。macOS 下也可以使用：

```bash
./scripts/open_macos_app.sh
```

## 后续可以继续做的事

- 增加更多顾客和订单组合。
- 补充真实美术素材，替换占位图。
- 给关键业务逻辑增加单元测试。
- 继续整理工作台 UI，让图形 overlay 更轻量。
