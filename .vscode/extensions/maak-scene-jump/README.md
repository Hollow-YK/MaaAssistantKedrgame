# MAK SceneJump 节点跳转

工作区扩展，为 `agent/custom/action/scene_jump_map.json` 提供与 Maa 资源 pipeline JSON 相同的**引用跳转**体验。

`scene_jump_map.json` 里的引用分两类，跳转目标不同：

- **场景引用**（`scenes` 场景名 key、`parent`、`from`、`to`、`via`）→ 跳到 `scenes` 中同名场景的定义；
- **节点引用**（`detect`、`jump`，含组合 `detect` 的 `all_of` / `any_of` 数组元素）→ 跳到 pipeline 资源中该节点的定义。

## 功能

- **定义跳转**（`Ctrl+Click` / `F12`）：按上述规则跳到对应定义；场景 key 本身即定义，不提供自跳转。
- **悬停提示**：
  - 场景引用：显示名称、`desc` 与场景定义 JSON 块；
  - 场景 key：显示名称与 `desc`；
  - 节点引用：显示名称与 pipeline 定义位置。- **查找引用**（`Shift+F12`）：列出 `scene_jump_map.json` 中所有引用同一名称的地方。
- **文档链接**：引用处显示可点击下划线（场景 key 除外）。
- **补全**：场景引用字段（`from`/`to`/`parent`/`via`）提示场景名；节点引用字段（`detect`/`jump`，含组合 `detect` 的 `all_of` / `any_of` 数组内）提示 pipeline 节点名。
- **`to` 多候选**：`to` 支持场景名列表，数组元素同样按场景引用处理。
- **组合 `detect`**：`{"type":"And","all_of":[...]}` / `{"type":"Or","any_of":[...]}` 内的节点名同样按节点引用处理（跳转/悬停/补全）。

## 数据格式要点

`scene_jump_map.json` 由 `SceneJump` custom（`agent/custom/action/scene_jump.py`）使用：

- `scenes`：场景名 → `{ desc, detect(识别条件), parent(父场景,可选) }`。`detect` 支持节点名字符串，或组合写法 `{"type":"And","all_of":[节点名,...]}` / `{"type":"Or","any_of":[节点名,...]}`（用于区分共用同一父界面节点的多个子场景，列表元素只支持节点名）。`parent` 表示“处于子场景即视为处于父场景”；规划时子场景可使用父场景的出边，多场景同时命中时自动选择到目标成本最小的起点。
- `edges`：`{ from, to, cost, jump, via }`。`to` 可为字符串或列表（操作后有概率进入其中任意一个）；`jump` 可为空（表示等待自然跳转，不执行操作）；`via` 表示可能经过的中间场景（也可能略过）。

## 原理

Maa 支持扩展 [maa-support-extension](https://github.com/neko-para/maa-support-extension) 的
Pipeline 语义分析（节点索引 + 定义解析）只覆盖 `interface.json` 资源路径下的 `pipeline/**`，
无法覆盖 `agent/` 下的自定义数据文件；且其不导出公共 API，无法直接调用其内部能力。

本扩展**借用同样的实现思路**（解析 `assets/interface.json` 的 `resource[].path` 建立“节点名 →
定义位置”索引，再解析 `scene_jump_map.json` 中的引用），独立实现等价能力（见 `lib/sceneMap.js`），
不依赖 maa-support 内部实现。

## 使用

1. 本扩展位于 `.vscode/extensions/maak-scene-jump/`，属于工作区扩展，仅在本项目生效。
2. 重新加载 VS Code 窗口（`Developer: Reload Window`）；首次可能提示安装/信任工作区扩展。
3. 打开 `agent/custom/action/scene_jump_map.json`，即可对节点引用进行跳转/悬停/查找引用/补全。
4. 修改 pipeline 资源后索引会自动重建；也可用命令 `MaaK: 刷新 SceneJump 节点索引` 手动刷新。

## 开发 / 测试

纯逻辑（扫描/索引/引用分类）不依赖 VS Code，可直接用 Node 测试：

```sh
node .vscode/extensions/maak-scene-jump/lib/test.js
```

可选的 CLI 校验（无需本扩展）：

```sh
python tools/validate_scene_map.py
```

## 许可声明

本扩展的实现思路参考了 [maa-support-extension](https://github.com/neko-para/maa-support-extension)
（**MIT** 许可）。本扩展（maak-scene-jump）作为 MaaAssistantKedrgame 项目的一部分，
采用本项目的开源许可 **AGPL-3.0**（见仓库根目录 `LICENSE`）。
