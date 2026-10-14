# 麦门账 · 账.skill（mckcal）

把你的麦当劳订单蒸馏成一张能带走的热量账。

对 AI 说「蒸馏我的热量账」。它只读最近的订单和官方营养表，对得上的才计入热量，对不上的标成待查。你确认自己的单餐上限之后，它导出一份可以交给任何 AI 的账，以及一张能发出去的账卡。

## 它能做什么

| 你说 | 它做 |
|---|---|
| 「蒸馏我的热量账」 | 只读最近订单和营养表，带笔数和营养表行名写出常点规则，等你确认单餐上限后导出 |
| 「这餐多少卡」 | 按营养表加总。有对不上的餐品时只给部分合计，不把它说成整单热量 |
| 「换成更低卡」 | 只在常点、且营养表里大一份和小一份都有数字时，建议降一档。例如大薯换成中薯 |
| 「今天这顿守得住吗」 | 整单都能算清时，才对照你确认过的单餐上限 |

它守住这些边界：只读，不下单、不领券、不建地址，不读积分和地址。热量只来自营养表对上的那一行。单餐上限只来自你的确认。输出是热量合计，不是营养或医疗建议。

## 适合谁用

- 想知道自己最近几单麦当劳大概多少千卡的人。
- 想把一张热量账交给别人的 AI，让它按自己的上限看下一餐的人。
- 还没有麦当劳 MCP Token 的人。最多 5 道自述题也能做账，账上会写明来源是自述。

## 安装

需要 Python 3.9 或更新版本。脚本只用标准库。开发和核对用的是腾讯 WorkBuddy，其他能加载 skill、也能调用命令的智能体同样可以用。

### 第一步：申请麦当劳 MCP Token

打开 [open.mcd.cn/mcp](https://open.mcd.cn/mcp)，用手机号登录，右上角「控制台」→「激活」→ 同意服务协议 → 复制 Token。图文步骤见[麦当劳 MCP Server 使用指南](https://github.com/M-China/mcd-mcp-server)。

没有 Token 时，skill 会改走自述问卷。

### 第二步：配置麦当劳 MCP

以腾讯 WorkBuddy 为例：左侧栏「专家 · 技能 · 连接器」→「连接器」→ 右上角「自定义连接器」→「配置 MCP」，填入 [`mcp-config.example.json`](mcp-config.example.json)，把 `${MCD_MCP_TOKEN}` 换成你自己的 Token，保存后启用 `mcd-mcp`。

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer ${MCD_MCP_TOKEN}" }
    }
  }
}
```

Token 只放在你自己的客户端里。这个 skill 不读取、不保存、不转发 Token。

### 第三步：安装 skill

```bash
git clone https://github.com/<你的用户名>/mckcal.git
cd mckcal
```

仓库最外层和里面的 skill 目录都叫 `mckcal`。要安装的是含 `SKILL.md` 的那一层。

- 腾讯 WorkBuddy：「专家 · 技能 · 连接器」→「技能」→「添加技能」→「上传技能」，选择里层的 `mckcal/` 文件夹。
- 用技能目录的智能体：在仓库根目录执行下面的命令。`mckcal` 后面不要加斜杠，否则 macOS 会把文件摊平。

```bash
mkdir -p ~/.workbuddy/skills && cp -R mckcal ~/.workbuddy/skills/
ls ~/.workbuddy/skills/mckcal/SKILL.md
```

### 第四步：检查

```bash
python3 mckcal/scripts/mckcal.py --help
python3 mckcal/tests/test_mckcal.py
```

测试使用虚构夹具，不需要 Token，也不联网。

## 使用示例

装好之后直接说：

```text
你：蒸馏我的热量账
AI：读到最近 N 笔有效订单。……（哪些对上了营养表，哪些待查）你的单餐上限是多少千卡？
你：800，就按这个
AI：（导出热量账和账卡）

你：巨无霸、大薯、可乐中杯，这餐多少卡
AI：（整单能算清才给整单热量，并对照你确认过的上限）

你：大薯换成更低卡
AI：（只有营养表里同时有大薯和中薯、而且大薯是常点时，才建议换成中薯）
```

下面用仓库里的虚构夹具走一遍。热量数字来自夹具，不是你的真实订单。

```bash
S=mckcal/scripts/mckcal.py
F=mckcal/tests/fixtures
OUT=$(mktemp -d)
python3 $S parse-nutrition --raw $F/nutrition_menu.json --out $OUT/foods.json
python3 $S normalize --raw $F/orders_habit.json --out $OUT/norm.json
python3 $S tally --orders $OUT/norm.json --foods $OUT/foods.json --out $OUT/tally.json
python3 $S distill --tally $OUT/tally.json --answers $F/answers_ceiling.json --out $OUT/ledger.json
python3 $S validate --ledger $OUT/ledger.json
python3 $S export --ledger $OUT/ledger.json --out $OUT/账
```

这条夹具的实际输出：

```text
[parse-nutrition] 8 行，跳过 0 行
[normalize] 原始 5 笔 → 纳入 5 笔，有效 3 笔，剔除取消 1 笔，状态不明 1 笔
[tally] 有效 3 笔，部分可算 0 笔，待查 0 项
[distill] 规则 2 条，来源 订单，上限 800
[validate] 通过
[export] 已写出 5 个文件
```

导出的账卡（`可分享/账卡.txt`）：

```text
【麦门账 · 巨无霸记账】

最近 3 笔有效订单里「巨无霸」出现 3 次，单份热量 550 千卡，来自营养表「巨无霸」

来源：订单
单餐上限：800 千卡

把这张账交给你的 AI，跟它说「用这张账算这餐多少卡」。

本账只记录热量合计，不是营养或医疗建议。
```

同一套账上，再问两句：

```bash
python3 $S quote --ledger $OUT/ledger.json --basket $F/basket_partial.json
python3 $S quote --ledger $OUT/ledger.json --basket $F/basket_meal.json
```

`basket_partial.json` 里有「神秘新品」。它不在营养表里，所以 `full_meal_kcal` 是 `null`，已匹配部分是 550 千卡，并写明算不清、不判断是否守住上限。`basket_meal.json` 三项都能对上，整单 1120 千卡，高于确认过的 800，`within_ceiling` 为 `false`。

大薯这组夹具里，大薯出现 3 次，营养表同时有中薯：

```bash
python3 $S normalize --raw $F/orders_fries.json --out $OUT/fries-norm.json
python3 $S tally --orders $OUT/fries-norm.json --foods $OUT/foods.json --out $OUT/fries-tally.json
python3 $S distill --tally $OUT/fries-tally.json --answers $F/answers_ceiling.json --out $OUT/fries-ledger.json
python3 $S swap --ledger $OUT/fries-ledger.json --basket $F/basket_fries.json
```

建议是把大薯换成中薯，少 150 千卡。只出现过一次的餐品不会被当成常点来替换。

| 文件 | 能不能发给别人 |
|---|---|
| `可分享/热量账.md`、`可分享/share-card.json`、`可分享/账卡.txt` | 可以。只有称号、一句说明、常点餐品和热量、单餐上限、数据来源 |
| `ledger.json`、`报告.md` | 留在自己这里 |

## 诚实边界

- `order-list` 只返回最近最多 10 笔。文案只说「最近 N 笔」。
- 营养表没有的餐品、规格对不上的餐品，标待查，不编一个热量。
- 套餐如果带了子项，只加子项。父项名称即使也能对上营养表，也不再加一次。
- 常点规则至少要在最近有效订单里出现 2 次，并且能指回营养表的那一行。
- 单餐上限来自你的确认。订单热量的中位数只出现在私人报告里，不会被写成你的目标。
- 价格、库存、是否可售，本 skill 不查，也不编。

## 仓库里有什么

```text
README.md                  本文件
CONTEST_DECLARATION.md     参赛声明（官方原文，未改动）
MCP_INTEGRATION.md         用到的麦当劳 MCP 工具和数据流
mcp-config.example.json    MCP 配置示例，只有环境变量占位符
mckcal/                    skill 本体
├── SKILL.md
├── references/            匹配口径、问卷、隐私白名单、账本结构
├── scripts/               解析、归一、合计、蒸馏、校验、导出、报价、替换
└── tests/                 虚构夹具和离线测试
```

参加 WorkBuddy 专项奖励时，用 WorkBuddy 打开这个仓库走一轮真实开发或复核，再把对话导出成仓库根目录的 `workbuddy.md`。这个文件要是你自己会话里的导出，仓库里不会预先放一份。

## 报名

仓库公开之后，到 [mcd-developer-innovation-challenge](https://github.com/M-China/mcd-developer-innovation-challenge/issues) 发 Issue。标题自定。正文照下面抄，把用户名换成你的；「项目名称」「项目地址」「项目简介」各占一行，标签和内容之间不换行。

```text
【参赛申请】
项目名称：麦门账（账.skill / mckcal）
项目地址：https://github.com/<你的用户名>/mckcal
项目简介：把你的麦当劳订单蒸馏成一张能带走的热量账。对 AI 说「蒸馏我的热量账」，通过麦当劳官方 MCP 只读最近订单和餐品营养表，对得上的才计入热量，对不上的标待查；你确认单餐上限后生成可携带的账和账卡。没有账号也可走自述问卷，并标明来源是自述。之后说「这餐多少卡」「换成更低卡」「今天这顿守得住吗」。全程只读不下单，可分享内容不含订单号、地址、金额和积分数值。
```

## 声明与许可

本项目是麦当劳程序员节创意开发大赛的参赛作品，由参赛者独立开发，不是麦当劳官方产品。参赛声明见 [`CONTEST_DECLARATION.md`](CONTEST_DECLARATION.md)。

项目输出仅供参考，不构成营养、医疗或其他专业建议。餐品、价格和供应以麦当劳官方渠道的实时结果为准。

代码与文档以 [MIT License](LICENSE) 开源。
