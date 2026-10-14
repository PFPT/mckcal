# 账本字段

`distill` 写出的 `ledger.json` 是后面 `validate`、`export`、`quote`、`swap` 的输入。

| 字段 | 含义 |
|---|---|
| `source` | `orders` 或 `self_report` |
| `source_label` | 订单，或自述 |
| `valid_count` | 有效订单数。自述时为 `null` |
| `meal_ceiling_kcal` | 用户确认过的单餐上限。没确认就是 `null` |
| `ceiling_confirmed` | 只有用户确认并且上限是正数时为 `true` |
| `typical_matched_kcal` | 完全可算订单的热量中位。只进私人报告 |
| `title` | 称号。订单账用出现次数最多的常点，自述账用「自述热量账」 |
| `blurb` | 一句说明，必须能指回证据 |
| `rules` | 常点。每条有 `name`、`kcal_each`、`times`、`evidence` |
| `pending_names` | 待查餐品 |
| `nutrition_foods` | 营养表的名称和 `energyKcal`，供之后复算 |
| `orders` | 分单明细：每行 `status` 为 `matched` 或 `pending`，以及 `matched_kcal`、`coverage` |
| `avoid` | 用户不想出现在替换建议里的餐品。不放进分享稿 |
| `window_limited` | 输入超过 10 笔时为 `true` |
| `excluded_canceled` | 剔除的取消单数 |
| `excluded_status_unknown` | 状态读不出来的单数 |

`quote` 的结果：

| 字段 | 含义 |
|---|---|
| `matched_kcal` | 已经对上的部分合计 |
| `full_meal_kcal` | 整单都能对上时才有数字 |
| `coverage` | `complete` 或 `partial` |
| `pending_names` | 这餐里对不上的名称 |
| `within_ceiling` | 整单可算并且上限已确认时，才是 `true` 或 `false` |
| `note` | 部分可算，或算不清、不判断是否守住上限 |

`swap` 的 `suggestions` 每一条有 `from`、`to`、`from_kcal`、`to_kcal`、`saved_kcal`、`reason`。
