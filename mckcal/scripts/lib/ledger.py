from .match import match_food

def tally(normalized, foods, source="orders"):
    items_map = {}
    orders_out = []
    pending_names = []
    for order in normalized.get("orders") or []:
        lines_out = []
        order_pending = []
        matched_kcal = 0
        seen = set()
        for line in order.get("lines") or []:
            recorded, line_kcal, key = _tally_line(line, foods)
            lines_out.append(recorded)
            if recorded["status"] != "matched":
                order_pending.append(recorded["name"])
                continue
            matched_kcal += line_kcal
            slot = items_map.setdefault(key, {
                "nutrition_name": recorded["nutrition_name"],
                "kcal_each": recorded["kcal_each"],
                "order_count": 0,
                "total_quantity": 0,
            })
            slot["total_quantity"] += recorded["quantity"]
            seen.add(key)
        for key in seen:
            items_map[key]["order_count"] += 1
        pending_names.extend(order_pending)
        orders_out.append({
            "lines": lines_out,
            "matched_kcal": matched_kcal,
            "coverage": "partial" if order_pending else "complete",
            "pending_names": order_pending,
        })
    return _pack(source, normalized, items_map, orders_out, pending_names, foods)


def tally_self_report(answers, foods):
    items = []
    pending_names = []
    for entry in answers.get("items") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        times = entry.get("times")
        if not name or isinstance(times, bool) or not isinstance(times, int) or times < 1:
            if name:
                pending_names.append(name)
            continue
        hit = match_food(name, foods)
        if not hit["ok"]:
            pending_names.append(name)
            continue
        items.append({
            "nutrition_name": hit["name"],
            "kcal_each": hit["kcal"],
            "order_count": times,
            "total_quantity": times,
        })
    return _pack("self_report", {}, {item["nutrition_name"]: item for item in items}, [], pending_names, foods)


def distill(tally_data, answers):
    source = answers.get("source") or tally_data.get("source") or "orders"
    if source not in ("orders", "self_report"):
        source = "orders"
    ceiling, ceiling_confirmed = _ceiling(answers)
    rules = []
    valid_count = tally_data.get("valid_count")
    for item in tally_data.get("items") or []:
        times = item.get("order_count") or 0
        kcal = _whole(item.get("kcal_each"))
        name = item.get("nutrition_name")
        if not name or kcal is None:
            continue
        if source == "orders" and times < 2:
            continue
        if source == "self_report" and times < 1:
            continue
        if source == "self_report":
            evidence = f"自述「{name}」出现 {times} 次，单份热量 {kcal} 千卡，来自营养表「{name}」"
        else:
            evidence = f"最近 {valid_count} 笔有效订单里「{name}」出现 {times} 次，单份热量 {kcal} 千卡，来自营养表「{name}」"
        rules.append({
            "name": name,
            "kcal_each": kcal,
            "times": times,
            "evidence": evidence,
        })
    rules.sort(key=lambda rule: (-rule["times"], -rule["kcal_each"], rule["name"]))
    title, blurb = _title(source, rules, valid_count)
    complete = [
        order["matched_kcal"]
        for order in tally_data.get("orders") or []
        if order.get("coverage") == "complete"
    ]
    return {
        "source": source,
        "source_label": "自述" if source == "self_report" else "订单",
        "valid_count": valid_count,
        "meal_ceiling_kcal": ceiling,
        "ceiling_confirmed": ceiling_confirmed,
        "typical_matched_kcal": _median(complete) if source == "orders" else None,
        "title": title,
        "blurb": blurb,
        "rules": rules,
        "pending_names": list(dict.fromkeys(tally_data.get("pending_names") or [])),
        "nutrition_foods": tally_data.get("nutrition_foods") or [],
        "orders": tally_data.get("orders") or [],
        "excluded_canceled": tally_data.get("excluded_canceled", 0),
        "excluded_status_unknown": tally_data.get("excluded_status_unknown", 0),
        "excluded_empty": tally_data.get("excluded_empty", 0),
        "window_limited": bool(tally_data.get("window_limited")),
        "fetched_count": tally_data.get("fetched_count"),
        "avoid": _avoid(answers),
    }


def _tally_line(line, foods):
    name = line.get("name") or ""
    if line.get("quantity") is None or line.get("pending_reason"):
        recorded = {
            "name": name,
            "quantity": line.get("quantity"),
            "status": "pending",
            "reason": line.get("pending_reason") or "quantity_unclear",
            "kcal": None,
            "nutrition_name": None,
        }
        return recorded, 0, None
    hit = match_food(name, foods)
    if not hit["ok"]:
        recorded = {
            "name": name,
            "quantity": line["quantity"],
            "status": "pending",
            "reason": hit["reason"],
            "kcal": None,
            "nutrition_name": hit.get("nutrition_name"),
        }
        return recorded, 0, None
    line_kcal = hit["kcal"] * line["quantity"]
    recorded = {
        "name": name,
        "quantity": line["quantity"],
        "status": "matched",
        "reason": None,
        "kcal": line_kcal,
        "kcal_each": hit["kcal"],
        "nutrition_name": hit["name"],
    }
    return recorded, line_kcal, hit["name"]


def _pack(source, normalized, items_map, orders_out, pending_names, foods):
    return {
        "source": source,
        "valid_count": normalized.get("valid_count", len(orders_out)) if source == "orders" else None,
        "excluded_canceled": normalized.get("excluded_canceled", 0),
        "excluded_status_unknown": normalized.get("excluded_status_unknown", 0),
        "excluded_empty": normalized.get("excluded_empty", 0),
        "window_limited": normalized.get("window_limited", False),
        "fetched_count": normalized.get("fetched_count"),
        "used_count": normalized.get("used_count"),
        "items": list(items_map.values()),
        "orders": orders_out,
        "pending_names": pending_names,
        "nutrition_foods": [
            {"productName": food.get("productName"), "energyKcal": food.get("energyKcal")}
            for food in foods
            if food.get("productName")
        ],
    }


def _ceiling(answers):
    if answers.get("confirmed") is not True:
        return None, False
    raw = answers.get("meal_ceiling_kcal")
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw <= 0:
        return None, False
    return _whole(raw), True


def _avoid(answers):
    names = []
    for item in answers.get("avoid") or []:
        text = str(item).strip()
        if text and text not in names:
            names.append(text)
    return names


def _title(source, rules, valid_count):
    if source == "self_report":
        if rules:
            return "自述热量账", "来源是自述，不是订单。" + rules[0]["evidence"]
        return "自述热量账", "来源是自述，不是订单。能对上营养表的常点还不够，先不写规则。"
    if rules:
        return f"{rules[0]['name']}记账", rules[0]["evidence"]
    shown = valid_count if isinstance(valid_count, int) else 0
    return "样本还不够的账", f"最近 {shown} 笔有效订单里，没有餐品出现达到 2 次，先不写常点规则。"


def _median(values):
    if not values:
        return None
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[mid]
    average = (ordered[mid - 1] + ordered[mid]) / 2
    return _whole(average)


def _whole(number):
    if isinstance(number, float) and number.is_integer():
        return int(number)
    return number

