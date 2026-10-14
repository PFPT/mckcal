---
name: mckcal
description: 麦门账。用户说「蒸馏我的热量账」「算我的热量」「这餐多少卡」「换成更低卡」「今天这顿守得住吗」时使用。只读麦当劳最近订单和营养表，蒸馏成可携带的热量账。不下单。
---

# 麦门账

把最近的麦当劳订单蒸馏成一张热量账。热量只来自 `list-nutrition-foods` 对上的行。对不上就标待查。单餐上限只来自用户亲口确认。

## 触发

- 蒸馏我的热量账、算我的热量、记一笔热量账
- 这餐多少卡、这单多少千卡
- 换成更低卡、有没有更小一档
- 今天这顿守得住吗、超了多少

没接上 MCP，或用户明确说没有订单时，走 [`references/questionnaire.md`](references/questionnaire.md)。来源写成自述。

## 只调用这些工具

- `order-list`
- `list-nutrition-foods`

不调用 `create-order`、`cancel-order`、`delivery-create-address`、`auto-bind-coupons`、`mall-create-order`、`calculate-price`、`query-my-account`、`delivery-query-addresses`。

Token 只存在于用户自己的 MCP 配置里。不要把 Token、订单号、地址、电话、金额、积分写进仓库或分享稿。

## 蒸馏

1. 确认两个工具都在。缺一个就改走问卷，不要编一份订单。
2. 把两个工具的原始 JSON 存到临时文件。
3. 在仓库根目录，或 skill 目录的上一级，运行：

```bash
S=mckcal/scripts/mckcal.py
python3 $S parse-nutrition --raw /tmp/mckcal-nutrition.json --out /tmp/mckcal-foods.json
python3 $S normalize --raw /tmp/mckcal-orders.json --out /tmp/mckcal-norm.json
python3 $S tally --orders /tmp/mckcal-norm.json --foods /tmp/mckcal-foods.json --out /tmp/mckcal-tally.json
```

skill 已经单独安装时，把 `S` 换成该 skill 目录下的 `scripts/mckcal.py`。

4. 把常点证据和待查餐品念给用户。问一句：你自己的单餐上限是多少千卡？用户给出数字并确认之后，把答案写成：

```json
{"source": "orders", "confirmed": true, "meal_ceiling_kcal": 800}
```

5. 再跑：

```bash
python3 $S distill --tally /tmp/mckcal-tally.json --answers /tmp/mckcal-answers.json --out /tmp/mckcal-ledger.json
python3 $S validate --ledger /tmp/mckcal-ledger.json
python3 $S export --ledger /tmp/mckcal-ledger.json --out /tmp/mckcal-账
```

6. `validate` 或 `export` 失败时，把失败原因告诉用户，不要改分享稿去绕过。
7. 把 `可分享/` 交给用户。`ledger.json` 和 `报告.md` 留在本地。

匹配、套餐和规格的口径在 [`references/nutrition-match.md`](references/nutrition-match.md)。分享稿能写什么在 [`references/privacy.md`](references/privacy.md)。字段形状在 [`references/ledger-schema.md`](references/ledger-schema.md)。

## 这餐多少卡

用户列出餐品后，写成 `{"items":[{"name":"巨无霸","quantity":1}]}`，运行：

```bash
python3 $S quote --ledger /tmp/mckcal-ledger.json --basket /tmp/mckcal-basket.json
```

- `coverage` 为 `complete` 时，`full_meal_kcal` 才是整单热量。
- `coverage` 为 `partial` 时，只报 `matched_kcal`，并列出 `pending_names`。不要把部分合计说成整单。
- `within_ceiling` 为 `null` 时，说算不清，不判断是否守住上限。
- 为 `true` 或 `false` 时，才对照 `ceiling_kcal` 回答守得住或守不住。

## 换成更低卡

```bash
python3 $S swap --ledger /tmp/mckcal-ledger.json --basket /tmp/mckcal-basket.json
```

`suggestions` 为空就告诉用户：这一项不是常点，或者营养表里没有更小的一档。不要另外推荐一张更低热量的菜单。

## 说话方式

- 只说「最近 N 笔」。N 是有效订单数，不是用户的全部历史。
- 每条常点都带证据：最近 N 笔里出现 K 次，单份热量来自营养表的哪一行。
- 自述账的第一句写明来源是自述，不是订单。
- 不根据订单猜测体重、减脂目标或疾病饮食。
