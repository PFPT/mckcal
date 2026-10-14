import json
import re
from pathlib import Path

DISCLAIMER = "本账只记录热量合计，不是营养或医疗建议。"
FORBIDDEN_KEYS = {
    "orderId",
    "orderNo",
    "storeName",
    "storeCode",
    "createTime",
    "realTotalAmount",
    "phone",
    "fullAddress",
    "address",
    "accumulativePoint",
    "contactName",
}
PATTERNS = (
    ("订单号", re.compile(r"订单号|orderId", re.I)),
    ("门店", re.compile(r"门店|storeName|storeCode", re.I)),
    ("地址", re.compile(r"地址|小区|号楼|单元|街道")),
    ("电话", re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")),
    ("Token", re.compile(r"Bearer|\bToken\b|MCP_TOKEN", re.I)),
    ("积分", re.compile(r"积分\s*\d|accumulativePoint", re.I)),
    ("金额", re.compile(r"[¥￥]\s*\d|\d+(?:\.\d+)?\s*元|金额")),
    ("下单时间", re.compile(r"\d{4}-\d{2}-\d{2}|\d{2}:\d{2}:\d{2}|下单时间")),
)


def validate(ledger):
    errors = []
    forbidden = _forbidden_keys(ledger)
    if forbidden:
        errors.append("账本含有应丢弃的字段：" + "、".join(sorted(set(forbidden))))
    if ledger.get("source") not in ("orders", "self_report"):
        errors.append("来源无法识别")
    if ledger.get("meal_ceiling_kcal") is not None and ledger.get("ceiling_confirmed") is not True:
        errors.append("上限不是本人确认的")
    for rule in ledger.get("rules") or []:
        evidence = rule.get("evidence") or ""
        name = rule.get("name") or ""
        kcal = rule.get("kcal_each")
        if name not in evidence or "营养表" not in evidence or str(kcal) not in evidence:
            errors.append(f"规则缺少证据：{name}")
        if ledger.get("source") == "orders" and "最近" not in evidence:
            errors.append(f"订单规则没有指回笔数：{name}")
        if ledger.get("source") == "self_report" and evidence and "自述" not in evidence:
            errors.append(f"自述规则没有标明来源：{name}")
    hits = scan(share_blob(ledger))
    if hits:
        errors.append("分享稿命中限制：" + "、".join(hits))
    return {"ok": not errors, "errors": errors}


def export_ledger(ledger, out_dir):
    if ledger.get("ceiling_confirmed") is not True or ledger.get("meal_ceiling_kcal") is None:
        return {"ok": False, "hits": [], "errors": ["单餐上限还没确认"]}
    blob = share_blob(ledger)
    hits = scan(blob)
    if hits:
        return {"ok": False, "hits": hits, "errors": []}
    forbidden = _forbidden_keys(ledger)
    if forbidden:
        return {"ok": False, "hits": [], "errors": ["账本含有应丢弃的字段：" + "、".join(sorted(set(forbidden)))]}
    root = Path(out_dir)
    share = root / "可分享"
    share.mkdir(parents=True, exist_ok=True)
    card = share_card(ledger)
    files = {
        root / "ledger.json": json.dumps(ledger, ensure_ascii=False, indent=2) + "\n",
        root / "报告.md": render_private_report(ledger),
        share / "热量账.md": render_markdown(ledger),
        share / "share-card.json": json.dumps(card, ensure_ascii=False, indent=2) + "\n",
        share / "账卡.txt": render_certificate(ledger),
    }
    for path, text in files.items():
        path.write_text(text, encoding="utf-8")
    return {"ok": True, "hits": [], "errors": [], "files": [str(path) for path in files]}


def scan(text):
    hits = []
    for label, pattern in PATTERNS:
        if pattern.search(text):
            hits.append(label)
    return hits


def share_card(ledger):
    return {
        "title": ledger.get("title"),
        "blurb": ledger.get("blurb"),
        "source": ledger.get("source_label"),
        "meal_ceiling_kcal": ledger.get("meal_ceiling_kcal"),
        "items": [
            {"name": rule["name"], "kcal_each": rule["kcal_each"], "times": rule["times"]}
            for rule in ledger.get("rules") or []
        ],
        "disclaimer": DISCLAIMER,
    }


def share_blob(ledger):
    card = share_card(ledger)
    return "\n".join([
        render_markdown(ledger),
        json.dumps(card, ensure_ascii=False, indent=2),
        render_certificate(ledger),
    ])


def render_markdown(ledger):
    lines = [
        f"# 麦门账 · {ledger.get('title')}",
        "",
        ledger.get("blurb") or "",
        "",
        f"来源：{ledger.get('source_label')}",
        _ceiling_line(ledger),
        "",
        "常点：",
    ]
    rules = ledger.get("rules") or []
    if rules:
        for rule in rules:
            if ledger.get("source") == "self_report":
                lines.append(f"- {rule['name']}：单份 {rule['kcal_each']} 千卡，自述出现 {rule['times']} 次")
            else:
                lines.append(f"- {rule['name']}：单份 {rule['kcal_each']} 千卡，最近有效订单里出现 {rule['times']} 次")
    else:
        lines.append("- 还没有能写下来的常点")
    lines.extend(["", DISCLAIMER, ""])
    return "\n".join(lines)


def render_certificate(ledger):
    return "\n".join([
        f"【麦门账 · {ledger.get('title')}】",
        "",
        ledger.get("blurb") or "",
        "",
        f"来源：{ledger.get('source_label')}",
        _ceiling_line(ledger),
        "",
        "把这张账交给你的 AI，跟它说「用这张账算这餐多少卡」。",
        "",
        DISCLAIMER,
        "",
    ])


def render_private_report(ledger):
    lines = [
        f"# 热量账报告 · {ledger.get('title')}",
        "",
        f"来源：{ledger.get('source_label')}",
        _ceiling_line(ledger),
        "",
        "订单号、门店、地址、电话、金额、积分和下单时间不写入本账。",
        "",
    ]
    if ledger.get("source") == "self_report":
        lines.append("这张账来自自述，没有读取订单。")
    else:
        lines.append("读取窗口最多 10 笔。")
        lines.append(
            f"读到 {ledger.get('fetched_count')} 笔，纳入统计 {ledger.get('valid_count')} 笔有效订单。"
        )
        lines.append(
            f"剔除取消 {ledger.get('excluded_canceled')} 笔，状态不明 {ledger.get('excluded_status_unknown')} 笔，空单 {ledger.get('excluded_empty')} 笔。"
        )
        if ledger.get("window_limited"):
            lines.append("输入超过 10 笔，只取前 10 笔。")
    if ledger.get("typical_matched_kcal") is not None:
        lines.append(f"完全可算订单的热量中位：{ledger['typical_matched_kcal']} 千卡。")
    lines.extend(["", "## 常点", ""])
    for rule in ledger.get("rules") or []:
        lines.append(f"- {rule['evidence']}")
    if not ledger.get("rules"):
        lines.append("- 没有常点规则")
    lines.extend(["", "## 待查", ""])
    pending = ledger.get("pending_names") or []
    if pending:
        for name in pending:
            lines.append(f"- {name}")
    else:
        lines.append("- 无")
    lines.extend(["", "## 分单", ""])
    for index, order in enumerate(ledger.get("orders") or [], start=1):
        pending_text = "、".join(order.get("pending_names") or []) or "无"
        lines.append(
            f"- 第 {index} 单：{order.get('coverage')}，已匹配 {order.get('matched_kcal')} 千卡，待查 {pending_text}"
        )
    lines.extend(["", DISCLAIMER, ""])
    return "\n".join(lines)


def _ceiling_line(ledger):
    if ledger.get("ceiling_confirmed") is True and ledger.get("meal_ceiling_kcal") is not None:
        return f"单餐上限：{ledger['meal_ceiling_kcal']} 千卡"
    return "单餐上限：待确认"


def _forbidden_keys(value, found=None):
    if found is None:
        found = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_KEYS:
                found.append(key)
            _forbidden_keys(item, found)
    elif isinstance(value, list):
        for item in value:
            _forbidden_keys(item, found)
    return found
