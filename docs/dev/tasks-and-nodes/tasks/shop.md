---
title: 自动购物
---

# 自动购物

任务入口：`Shop`

任务文件：`assets/resource/tasks/Shop.json`

Pipeline 入口文件：`assets/resource/pipeline/Shop.json`

入口节点：`Shop_Main`

## 功能概述

自动购物先从任意界面跳转到高账商店（专属商店），再按任务选项里勾选的商品逐个购买。

高账商店的商品分免费与收费两类，玩家通常只买其中一部分，因此本任务以**商品名**为单位选择目标：选项把商品名写进 `Shop_Buy` 节点的 `attach`，由 [高账商店购物管理器](../custom/shop-manager-VIP.md)（`Shop_VIP_Manager`）在当前页面按名字匹配格子、进入详情、设置数量并完成购买。

售罄、货币不足、数量加减、关闭详情、获得物品弹窗、翻页都由场景节点承担，动作只做流程控制与判断。

## 主要节点

### 入口与跳转

- `Shop_Main`：任务入口。`next` 指向跳转节点，`focus` 提示「正在前往高账商店……」。
- `Shop_Do:JumpToVipShop`：通用 `SceneJump`（`target: "VIP_Shop"`）从任意界面跳转到高账商店，`post_delay` 1s 等界面稳定。

### 购买

- `Shop_Buy`：Custom 动作 `Shop_VIP_Manager`。买哪些商品由选项写入该节点的 `attach`（每个商品一个键）；未注入任何商品时直接失败退出，不会回落到“买全部”。
- `Shop_Finish`：任务完成通知节点。

### 依赖的场景节点

| 节点 | 文件 | 作用 |
| --- | --- | --- |
| `UI_Shop_Sold` | `pipeline/Scene/UI/Shop.json` | 售罄标识模板匹配（`UI/Shop/sold.png`） |
| `UI_Shop_Confirm:Money` | 同上 | 货币不足（价格显示红色） |
| `SceneDo_Shop_Swipe_Next` / `_Last` | `pipeline/Scene/Do/Shop.json` | 右划 / 回划一页 |
| `SceneDo_Shop_Detail_Click_Max` / `_Min` / `_Plus` / `_Minus` | 同上 | 详情页数量控制 |
| `SceneDo_Shop_CloseInfo` | 同上 | 点击「点击空白区域关闭弹窗」关闭详情 |
| `SceneDo_GetItem` | `pipeline/Scene/Do/Common.json` | 获得物品 / 结算弹窗（与活动商店共用） |

## 选项

文件：`assets/resource/tasks/Shop.json`

商品分两组，每组一个「全选」开关；开关选「否」时才挂出该组的逐项多选。

| 选项 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `Shop_FreeAll` | switch | 是 | 免费物品全选。选「是」时把这 5 件都写进 `Shop_Buy.attach`；选「否」挂出 `Shop_FreeItems` |
| `Shop_FreeItems` | checkbox | 全不勾 | 免费物品逐项选择 |
| `Shop_PaidAll` | switch | 否 | 收费物品全选（会消耗货币）。选「否」挂出 `Shop_PaidItems` |
| `Shop_PaidItems` | checkbox | 全不勾 | 收费物品逐项选择 |

每个 case 的 `pipeline_override` 形如：

```jsonc
{
    "Shop_Buy": {
        "attach": { "军用单兵口粮": "MAX" }
    }
}
```

`attach` 在 `pipeline_override` 里是按顶层键合并的，所以勾几件就叠加几个键；值除了 `"MAX"`，还可以是 `1`/`2`…（买几份）、`0`（不买），详见 [参数说明](../custom/shop-manager-VIP.md#参数)。

当前商品（组内顺序与游戏内一致：先列后行）：

| 组 | 商品 |
| --- | --- |
| 免费 | 军用单兵口粮、淡海糖果、第二版能元、训练用器材、载具研发公式 |
| 收费 | 定期发射计划、高级考核材料组合包、中级考核材料组合包、低级考核材料组合包、技能升级材料组合包 |

## 起点与结束状态

- 起点：任意界面，`Shop_Do:JumpToVipShop` 会负责跳转。
- 结束：高账商店商品页。货币不足、目标全部买完/售罄时按成功结束；有目标未买到时按失败结束并列出商品名。

## 注意事项

- 一组商品都不勾（`attach` 里没有商品键）时任务直接失败，这是刻意设计——高账商店的收费商品会消耗货币，不能默认买全店。
- 「收费物品全选」默认关闭；需要买收费商品时自行开启，或逐项勾选。
- 被屏幕边缘裁掉一部分的商品格子不可购买，任务会先右划、翻不动时回划一页尝试让它完整露出。
- 售罄标识若超出 `UI_Shop_Sold` 的 ROI 或屏幕边界（例如最右侧被裁的列），匹配不到；该列商品既不可购买也不会被标为售罄。
- 购买数量只支持「页面默认值 / MAX / MIN / 逐次 ±」，不能精确跳到任意份数。

## 验收清单

1. 跳转：从主界面、商店其它页、战斗中界面分别启动，都能到达高账商店。
2. 默认选项（免费全选）跑一遍：5 件免费物品买齐，收费物品不被购买。
3. 逐项多选：关闭两组全选后各勾 1~2 件，只买勾选的商品。
4. 收费全选：货币充足时全部买下；货币不足时正确停止并按成功结束。
5. 售罄跳过：目标已售罄时不报错、不重复点击，任务正常结束。
6. 极端排版：满页 5 列、只剩 3 列可购买、只剩 1 件可购买，三种情况都能买到目标。
7. 翻页与还原：目标在下一页时能翻页买到，结束后商店回到起始位置。

## 维护重点

- 游戏内商品名称变化时，需要同步更新 `tasks/Shop.json` 对应 case 的 `attach` 键与 `locales/interface/zh_cn.json` 的文案。
- 商店卡片尺寸/间距变化时，需要同步 `vip_shop.py` 的 `CELL_W`、`CELL_H`、`LEFT_RIGHT_DIST`、`BOTTOM_BORDER_Y`，以及场景节点里数量按钮、售罄模板的 ROI。
- 新增商品时，在对应组的 checkbox 里加 case，并把「全选」case 的 `attach` 一起补上，避免“全选买不到新商品”。