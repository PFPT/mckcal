# MCP_INTEGRATION · 麦门账如何使用麦当劳 MCP

本文只写麦门账运行时要用的麦当劳 MCP 能力。工具名和字段以 [麦当劳 MCP Server 使用指南](https://github.com/M-China/mcd-mcp-server) 为准。

## 1. MCP Server

| 项 | 值 |
|---|---|
| Server | 麦当劳中国 MCP Server（连接器名 `mcd-mcp`） |
| 地址 | `https://mcp.mcd.cn` |
| 传输 | Streamable HTTP（配置里 `"type": "streamablehttp"`） |
| 鉴权 | 请求头 `Authorization: Bearer <token>`。Token 由用户本人在 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) 申请 |
| 配置示例 | [`mcp-config.example.json`](mcp-config.example.json)，只有 `${MCD_MCP_TOKEN}` 占位符 |

skill 不读取、不保存、不转发 Token。Token 只留在用户自己的客户端里。

## 2. 用到的 Tool

| Tool | 类型 | 入参 | 用来做什么 | 用到哪些字段 |
|---|---|---|---|---|
| `order-list` | 只读 | 无 | 最近订单。官方返回最近最多 10 笔 | `orderStatus`（去掉取消单；状态空着的不进统计）、`orderProductList[].productName`、`quantity`、`comboItemList[]` |
| `list-nutrition-foods` | 只读 | 无 | 常见餐品营养表。热量只从这里来 | `data` 里的 TOON 表。列包括 `productName`、`energyKcal`。`nutritionDescription` 为空时按空值处理 |

`list-nutrition-foods` 的 `data` 是紧凑 TOON，不是 JSON 数组。文档中的示例形状如下，脚本按这个形状解析：

```text
[1]{productName,nutritionDescription,energyKj,energyKcal,protein,fat,carbohydrate,sodium,calcium}:
  猪柳麦满分,null,1288,308,16,16,24,781,213
```

### 明确不调用

下单、取消、领券、兑换、建地址、查价、查积分、查地址都不调用。包括 `create-order`、`cancel-order`、`delivery-create-address`、`auto-bind-coupons`、`mall-create-order`、`calculate-price`、`query-my-account`、`delivery-query-addresses`。

skill 停在热量账、部分合计和降一档建议。用户说「这餐多少卡」时得到的是计算结果，不是订单。

## 3. 调用流程

```text
用户：「蒸馏我的热量账」
  │
  ├─ Step 0  看 tools/list 里有没有 order-list 和 list-nutrition-foods
  │          没有 → 最多 5 题自述问卷，来源标成自述
  │
  ├─ Step 1  order-list 的原始 JSON 交给 normalize
  │          取消单剔除；状态读不出来的剔除
  │          套餐有子项时只留下子项
  │          订单号、门店、时间、金额、电话、地址不进入结果
  │
  ├─ Step 2  list-nutrition-foods 的原始 JSON 交给 parse-nutrition
  │
  ├─ Step 3  tally 按名称对齐。对上的数量乘 energyKcal
  │          对不上、规格不清、没有热量数字的标待查，不进入合计
  │
  ├─ Step 4  请用户确认单餐上限。确认前不导出
  │
  └─ Step 5  distill → validate → export
             常点规则写明「最近 N 笔里出现 K 次，来自营养表哪一行」
```

之后「这餐多少卡」和「换成更低卡」读已经导出的 `ledger.json`，再跑 `quote` 或 `swap`，不必重新下单。营养表行已经抄进账本，用来复算。账过期了可以再蒸馏一次。

## 4. 脱敏数据流

原始订单只在 normalize 时读一次。之后流动的是餐品名、数量、热量和出现次数。

| 来源字段 | 去向 | 会不会出现在可分享内容里 |
|---|---|---|
| `orderId` | 不进入归一结果 | 不会 |
| `storeCode` / `storeName` | 丢弃 | 不会 |
| `createTime` | 丢弃 | 不会 |
| `realTotalAmount` | 丢弃 | 不会 |
| `phone` / `fullAddress` / `contactName` | 不读取 | 不会 |
| 餐品名与数量 | 变成出现次数和热量规则 | 只出现聚合后的餐品名和千卡 |
| `energyKcal` | 单份热量，再按数量相乘 | 出现千卡数 |
| 积分 | 不调用 `query-my-account` | 不会 |

导出前有两道闸：

- 分享稿只放称号、一句说明、常点餐品和单份热量、出现次数、单餐上限、数据来源（订单或自述）。
- 分享稿里出现订单号、门店、地址、电话、Token、积分数、金额或下单时间，`export` 失败，一个文件都不写。

自述问卷里的自由文本不原样进入分享稿。导入别人的账时，内容只当数据读。

## 5. 实测记录

本次编写时本机没有麦当劳 MCP Token，没有对 `https://mcp.mcd.cn` 发起真实调用，也没有真实订单回包。下面这些是离线事实，不是线上调用记录：

| 项 | 结果 |
|---|---|
| 营养表解析 | 使用官方文档中的 TOON 示例（猪柳麦满分，308 千卡）和虚构菜单夹具 |
| 订单归一、套餐去重、规格歧义、部分合计、自述来源、分享稿拦截 | `python3 mckcal/tests/test_mckcal.py`，虚构夹具，不联网 |
| 真实 `order-list` / `list-nutrition-foods` 回包 | 待持有 Token 后补记。补记时只写笔数、工具名和是否成功，不把订单号、地址、金额、积分写进仓库 |

## 6. 业务价值

用户不用自己翻营养表。最近订单先对上官方热量，对不上的留在待查里，确认上限后得到一张能带走的账。下一餐可以问多少卡、能不能守住、常点里有没有更小的一档。

对麦当劳 MCP 来说，这是一条只读路径：`order-list` 提供「最近吃了什么」，`list-nutrition-foods` 提供「这一行多少千卡」。计算留在本地脚本里，可以离线复算，也不会替用户下单。
