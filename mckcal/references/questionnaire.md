# 没有订单时的 5 个问题

工具没接上、用户没有 Token，或 `order-list` 失败时，改问这 5 题。一轮问完，不再追加。

1. 最近常点哪 1 到 3 个餐品？请写餐品名。
2. 每个大概出现过几次？
3. 规格说得清吗？中杯、大杯、中薯、大薯。说不清就留空。
4. 有没有明确不想再出现在替换建议里的餐品？
5. 你自己定的单餐上限是多少千卡？

答案写成：

```json
{
  "source": "self_report",
  "confirmed": true,
  "meal_ceiling_kcal": 600,
  "avoid": ["中薯"],
  "items": [
    {"name": "麦香鸡", "times": 4},
    {"name": "可乐", "times": 2}
  ]
}
```

然后：

```bash
python3 mckcal/scripts/mckcal.py tally --answers answers.json --foods foods.json --out tally.json
python3 mckcal/scripts/mckcal.py distill --tally tally.json --answers answers.json --out ledger.json
```

没有营养表时，先告诉用户热量对不上，不要凭记忆填千卡。营养表在、餐品名对上了，规则写成「自述「餐品」出现 K 次……来自营养表「餐品」」。规格说不清、营养表又有多档时，这一项待查。

分享稿的来源是「自述」。说明里写「来源是自述，不是订单。」不要写成最近 N 笔订单。
