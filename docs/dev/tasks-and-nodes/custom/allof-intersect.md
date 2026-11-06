---
title: 组合识别取交集
---

# 组合识别取交集

Custom Recognition：`Common_AllOfIntersect`

文件：`agent/custom/recognition/common.py`

## 功能概述

把多个识别“同时命中”的部分取出来，并按顺序挑一个。

框架自带的 `And` 只能输出**一个**框（`box_index` 指定用哪个子识别的），无法表达「先按条件筛掉一部分命中，再取最靠上的那一个」。`Common_AllOfIntersect` 相当于一个**能列出全部交集候选**的 `And`：

1. 按 `all_of` 顺序执行每个子识别，拿到各自的**全部**命中框（`all_results`）；
2. 以**第一个子识别**的命中框作为候选；
3. 候选框必须与其余每个子识别的某个结果框重叠（交集面积占候选框面积 ≥ `min_overlap`），才算“同时命中”；
4. 通过的候选按 `order_by` 排序，`index` 取第几个，返回该候选在 `box_from` 指定的子识别上的框。

子识别的执行完全交给 MaaFramework：内联写法会被包成一个临时节点交给 `run_recognition`，由框架完成参数解析、默认值补全、阈值与连通域判定、调试图输出；识别器本身只做“收集框 → 求交 → 排序”。

## 快速使用

```jsonc
{
    "MyNode": {
        "recognition": {
            "type": "Custom",
            "param": {
                "custom_recognition": "Common_AllOfIntersect",
                "custom_recognition_param": {
                    "all_of": [
                        {
                            "type": "TemplateMatch",
                            "param": {
                                "template": "UI/Friend/sendgift.png",
                                "roi": [970, 110, 125, 595],
                                "green_mask": true
                            }
                        },
                        {
                            "type": "ColorMatch",
                            "param": {
                                "roi": [970, 110, 125, 595],
                                "lower": [235, 235, 80],
                                "upper": [255, 255, 115],
                                "connected": true,
                                "count": 600
                            }
                        }
                    ],
                    "order_by": "Vertical",
                    "index": 0
                }
            }
        }
    }
}
```

`all_of` 的每一项也可以是**已有节点名**，直接复用该节点的识别参数：

```jsonc
"all_of": ["UI_Friend_SendGift", "UI_Friend_SendGift_Gold"]
```

### 参数

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `all_of` | 必填（≥2 项） | 子识别列表。`string` = 已有 pipeline 节点名；`object` = `{type, param}` 内联定义，也可直接写节点体 `{recognition: {...}}` |
| `order_by` | `Vertical` | 候选排序方式：`Vertical`（最靠上优先，同高从左到右）/ `Horizontal` / `Area`（面积大优先）/ `Random`。作用对象是 `box_from` 指定的那个框 |
| `index` | `0` | 取第几个候选；支持负数（`-1` 为最后一个），超出范围视为未命中 |
| `box_from` | `0` | 返回第几个子识别的框。默认 `0`，即候选框本身（通常是模板框）；想看颜色块就设 `1` |
| `min_overlap` | `0` | 交集面积占候选框面积的最小比例。`0` 表示有任何重叠即可 |

子识别参数可只写关心的字段，其余取框架默认值（等价于 pipeline 省略字段）。子识别自身写的 `order_by` / `index` 不参与——本识别器取的是全部结果。

### 返回的 detail

| 字段 | 说明 |
| --- | --- |
| `candidates` | 全部通过筛选的候选，已排序；每个元素是按 `all_of` 顺序排列的框列表 |
| `index` | 选中的下标 |
| `order_by` | 实际使用的排序方式 |

## 与 `And` 的对比

| 场景 | `And` | `Common_AllOfIntersect` |
| --- | --- | --- |
| 判断“两个条件都命中” | ✅ 支持 | ✅ 支持（交集非空即命中） |
| 条件命中但**配对关系**不同（模板命中 5 行、颜色只命中第 3 行） | ❌ 只能给一个框，容易取到第 1 行 | ✅ 只保留与颜色块重叠的候选，默认取最靠上 |
| 取“最靠上 / 面积最大 / 第 N 个”交集 | ❌ 不支持排序与索引 | ✅ `order_by` + `index` |
| 需要子识别的全部命中框 | ❌ 只有子识别的 `detail` | ✅ `candidates` 里全部列出 |

## 注意事项

- `ColorMatch` 一类“区域型”子识别通常要 `connected: true`：否则整条 ROI 会被当成一个结果，任何模板框都与它重叠，交集退化为“全部通过”。
- 候选来源固定是**第一个**子识别；交换顺序会改变候选集合与 `candidates` 的结构。
- 内联定义会生成临时节点（名称形如 `__Common_AllOfIntersect_sub<节点名>_<序号>`），只在当前任务上下文生效；想完全避免临时节点、便于在调试器里单独观察识别框，就把子识别写成正式 pipeline 节点再用节点名引用。
- 子识别 `all_results` 的 `box` 在绑定层可能是 `Rect`，也可能是 `[x, y, w, h]`，本识别器均已兼容。
