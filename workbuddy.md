# workbuddy.md — 麦门账（mckcal）WorkBuddy 开发复核对话导出

> 本文件是使用腾讯 WorkBuddy 对 mckcal 仓库进行真实复核的对话导出。已脱敏：不含真实 Token、真实订单数据、个人隐私信息。AI 参与署名。

---

## 用户

参考 https://github.com/alchaincyf/mcstomach 【参赛申请】项目名称：麦门胃（胃.skill / mcstomach）……调用 workbuddy 生成我自己的参赛，内容是关于热量计算的。

## 助手

我先研究了两个关键来源：

1. **比赛规则**（https://github.com/M-China/mcd-developer-innovation-challenge）：需要 README.md、CONTEST_DECLARATION.md（官方原文不可改）、MCP_INTEGRATION.md、mcp-config.example.json、源代码、workbuddy.md（参加 WorkBuddy 专项奖励时必须提交）。排名按 GitHub Star 数。截止 2026-10-25 23:59。

2. **参考项目 mcstomach**：分层文档结构（根 README → 内部 README → SKILL.md → references/），隐私优先设计（字段白名单 + 黑名单校验 + 原始订单不落盘），证据驱动（每条规则指回订单），232 项测试 + 30 个虚构夹具。

我设计了一个热量计算 Skill 方案，项目名「麦卡路 / mccal」，核心是把 `list-nutrition-foods` 作为核心工具（mcstomach 明确不调用它并标"待查"，这是关键差异化）。

### 工具调用

- WebFetch: 获取比赛 README、activityGuidelines.md、CONTEST_DECLARATION.md 模板原文
- WebFetch: 获取 mcstomach 的 README.md、CONTEST_DECLARATION.md、MCP_INTEGRATION.md
- Agent (Explore × 2): 并行探索 mcstomach 仓库和比赛仓库
- Agent (Plan): 设计实现方案

---

## 用户

GitHub 用户名和作者署名用 PFPT。

## 助手

已更新计划，仓库地址为 `https://github.com/PFPT/mckcal`。

---

## 用户

参考优化独立仓库 /Users/zhaoshuo/Documents/GitHub/mckcal，没有写进 TV 项目。对 AI 说「蒸馏我的热量账」，它只读最近订单和官方营养表，对得上的才计入热量，你确认单餐上限后导出一张能带走的账。虚构夹具上的结果是：5 笔里 3 笔有效，套餐只加子项，巨无霸 3 次、单份 550 千卡。对不上的餐品只给部分合计。大薯在营养表里同时有中薯时，才会建议换成中薯。分享稿里一旦出现订单号、地址、积分或金额，导出会直接失败。23 项离线测试已通过。仓库里还没有 workbuddy.md，也还没有提交参赛 Issue。用 WorkBuddy 打开这个仓库走一轮真实复核，把对话导出成根目录的 workbuddy.md。仓库公开后，按 README.md 里的报名正文，把地址里的用户名换成你的，再发到活动仓库。

## 助手

仓库已存在且代码完整。我先读取了全部关键文件：

### 工具调用

- Read: README.md（203 行，含完整安装指南、使用示例、报名正文）
- Read: SKILL.md（89 行，YAML frontmatter + 触发语 + 只读工具 + 蒸馏流程 + quote/swap 规则）
- Read: MCP_INTEGRATION.md（100 行，MCP Server 信息 + 2 个只读工具 + 脱敏数据流 + 实测记录）
- Read: mckcal.py（157 行 CLI，8 条命令）
- Read: normalize.py（139 行，订单归一化 + 套餐拆解 + 秘密字段丢弃）
- Read: ledger.py（221 行，tally + distill + 自述路径）
- Read: privacy.py（217 行，11 个禁止字段 + 8 类正则 + 两道闸导出）
- Read: match.py（99 行，精确匹配 → 套餐后缀 → 规格感知 → 降一档）
- Read: recommend.py（106 行，quote 部分可算/整单 + swap 降一档）
- Read: nutrition.py（100 行，TOON 格式解析 + JSON 兼容）
- Read: test_mckcal.py（325 行，5 个测试类 23 项测试）
- Read: 4 个参考文档（nutrition-match.md、privacy.md、ledger-schema.md、questionnaire.md）
- Read: 13 个虚构夹具 JSON
- Read: CONTEST_DECLARATION.md（官方模板原文，未改动）
- Bash: git status（零提交，全部 untracked）

仓库结构确认：

```
mckcal/
├── README.md, CONTEST_DECLARATION.md, MCP_INTEGRATION.md, mcp-config.example.json, LICENSE, .gitignore
└── mckcal/
    ├── SKILL.md
    ├── references/ (4 个)
    ├── scripts/mckcal.py + lib/ (6 个模块)
    └── tests/test_mckcal.py + fixtures/ (13 个)
```

缺失项确认：workbuddy.md 不存在，git 零提交，参赛 Issue 未提交。

---

### Step 1: 运行测试

```bash
cd /Users/zhaoshuo/Documents/GitHub/mckcal
python3 mckcal/tests/test_mckcal.py -v
```

结果：**23 项全部通过**（2.136s）

```
test_pipeline_commands ... ok
test_rules_point_at_orders_and_ceiling_is_not_inferred ... ok
test_self_report_is_labeled ... ok
test_export_rejects_private_leaks ... ok
test_export_rejects_unconfirmed_ceiling ... ok
test_share_card_and_private_report ... ok
test_validate_rejects_order_id_key ... ok
test_cancelled_english_status ... ok
test_combo_does_not_add_parent_kcal ... ok
test_habit_drops_cancel_unknown_and_secrets ... ok
test_missing_quantity_and_kcal_stay_pending ... ok
test_parent_quantity_scales_children_only ... ok
test_partial_sum_excludes_unknown_item ... ok
test_size_ambiguity_and_missing_size ... ok
test_space_and_combo_suffix ... ok
test_window_keeps_first_ten ... ok
test_menu_row_count ... ok
test_official_toon_sample ... ok
test_skipped_short_row ... ok
test_quote_complete_meal_against_ceiling ... ok
test_quote_partial_does_not_claim_full_meal ... ok
test_swap_skips_avoided_item ... ok
test_swap_steps_down_only_when_both_rows_exist ... ok

Ran 23 tests in 2.136s
OK
```

---

### Step 2: 完整流水线（虚构夹具）

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

输出：

```
[parse-nutrition] 8 行，跳过 0 行
[normalize] 原始 5 笔 → 纳入 5 笔，有效 3 笔，剔除取消 1 笔，状态不明 1 笔
[tally] 有效 3 笔，部分可算 0 笔，待查 0 项
[distill] 规则 2 条，来源 订单，上限 800
[validate] 通过
[export] 已写出 5 个文件
```

导出的账卡（`可分享/账卡.txt`）：

```
【麦门账 · 巨无霸记账】

最近 3 笔有效订单里「巨无霸」出现 3 次，单份热量 550 千卡，来自营养表「巨无霸」

来源：订单
单餐上限：800 千卡

把这张账交给你的 AI，跟它说「用这张账算这餐多少卡」。

本账只记录热量合计，不是营养或医疗建议。
```

私人报告（`报告.md`）含热量中位 830 千卡（只在私人报告，不进分享稿）。

验证：分享稿不含订单号、地址、金额、积分。✓

---

### Step 3: 验证 quote 和 swap

**quote basket_partial（部分可算）**：
- coverage=partial, matched_kcal=550, full_meal_kcal=null, within_ceiling=null
- note: "部分可算，未把部分合计说成整单热量。算不清，不判断是否守住上限" ✓

**quote basket_meal（整单对照上限）**：
- coverage=complete, full_meal_kcal=1120, within_ceiling=false（1120 > 800）✓

**quote basket_single（单巨无霸）**：
- coverage=complete, full_meal_kcal=550, within_ceiling=true（550 < 800）✓

**swap（大薯→中薯）**：
- from=大薯(430), to=中薯(280), saved_kcal=150
- reason: "常点「大薯」，营养表同时有「中薯」（280 千卡）和「大薯」（430 千卡）" ✓

---

### Step 4: 生成 workbuddy.md

本文件即为导出结果。已脱敏：不含真实 Token、真实订单数据、个人隐私信息。

---

### Step 5: Git 提交

```bash
cd /Users/zhaoshuo/Documents/GitHub/mckcal
git add -A
git commit -m "麦门账（mckcal）参赛提交

- 只读麦当劳 MCP（order-list + list-nutrition-foods）
- 套餐只加子项，对不上的标待查
- 单餐上限需用户确认才导出
- 分享稿不含订单号、地址、金额、积分
- 23 项离线测试，13 个虚构夹具

Co-Authored-By: WorkBuddy AI"
```

---

### Step 6: 推送到 GitHub

```bash
git remote add origin https://github.com/PFPT/mckcal.git
git push -u origin main
```

---

### Step 7: 提交参赛 Issue

到 https://github.com/M-China/mcd-developer-innovation-challenge/issues 发 Issue：

标题：麦门账参赛申请

正文：
```
【参赛申请】
项目名称：麦门账（账.skill / mckcal）
项目地址：https://github.com/PFPT/mckcal
项目简介：把你的麦当劳订单蒸馏成一张能带走的热量账。对 AI 说「蒸馏我的热量账」，通过麦当劳官方 MCP 只读最近订单和餐品营养表，对得上的才计入热量，对不上的标待查；你确认单餐上限后生成可携带的账和账卡。没有账号也可走自述问卷，并标明来源是自述。之后说「这餐多少卡」「换成更低卡」「今天这顿守得住吗」。全程只读不下单，可分享内容不含订单号、地址、金额和积分数值。
```

---

## 复核结论

| 检查项 | 结果 |
|---|---|
| 23 项离线测试 | 全部通过 |
| 完整流水线（parse→normalize→tally→distill→validate→export） | 输出与预期一致 |
| 5 笔订单 → 3 笔有效（1 取消 + 1 状态不明） | ✓ |
| 套餐只加子项，父项不加第二次 | ✓ |
| 巨无霸 3 次、单份 550 千卡 | ✓ |
| 对不上的餐品只给部分合计 | ✓ |
| 大薯→中薯降一档（营养表同时有中薯时才建议） | ✓ |
| 分享稿出现订单号/地址/积分/金额时导出失败 | ✓ |
| 分享稿不含热量中位（只在私人报告） | ✓ |
| CONTEST_DECLARATION.md 为官方原文未改动 | ✓ |
| mcp-config.example.json 只有环境变量占位符 | ✓ |
| workbuddy.md 已生成 | ✓（本文件） |
| Git 已提交 | 待执行 |
| 参赛 Issue 已提交 | 待执行 |
