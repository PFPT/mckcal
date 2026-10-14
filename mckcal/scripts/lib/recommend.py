from .match import match_food, smaller_alternative
from .normalize import parse_qty


def quote(ledger, basket):
    foods = ledger.get("nutrition_foods") or []
    lines = []
    pending = []
    matched = 0
    for entry in basket.get("items") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        qty = parse_qty(entry.get("quantity")) if "quantity" in entry else None
        if not name or qty is None:
            pending.append(name or "未命名")
            lines.append({
                "name": name,
                "status": "pending",
                "reason": "quantity_unclear",
                "kcal": None,
            })
            continue
        hit = match_food(name, foods)
        if not hit["ok"]:
            pending.append(name)
            lines.append({
                "name": name,
                "quantity": qty,
                "status": "pending",
                "reason": hit["reason"],
                "kcal": None,
            })
            continue
        kcal = hit["kcal"] * qty
        matched += kcal
        lines.append({
            "name": name,
            "quantity": qty,
            "status": "matched",
            "nutrition_name": hit["name"],
            "kcal_each": hit["kcal"],
            "kcal": kcal,
        })
    coverage = "partial" if pending or not lines else "complete"
    full = matched if coverage == "complete" else None
    within = None
    notes = []
    if coverage != "complete":
        notes.append("部分可算，未把部分合计说成整单热量")
        if ledger.get("ceiling_confirmed") is True:
            notes.append("算不清，不判断是否守住上限")
    elif ledger.get("ceiling_confirmed") is True and ledger.get("meal_ceiling_kcal") is not None:
        within = full <= ledger["meal_ceiling_kcal"]
    return {
        "lines": lines,
        "matched_kcal": matched,
        "coverage": coverage,
        "pending_names": pending,
        "full_meal_kcal": full,
        "within_ceiling": within,
        "ceiling_kcal": ledger.get("meal_ceiling_kcal") if ledger.get("ceiling_confirmed") is True else None,
        "note": "。".join(notes) if notes else None,
    }


def swap(ledger, basket):
    foods = ledger.get("nutrition_foods") or []
    frequent = {rule["name"] for rule in ledger.get("rules") or []}
    avoid = set()
    for name in ledger.get("avoid") or []:
        hit = match_food(name, foods)
        avoid.add(hit["name"] if hit["ok"] else name)
    suggestions = []
    seen = set()
    for entry in basket.get("items") or []:
        if not isinstance(entry, dict):
            continue
        name = str(entry.get("name") or "").strip()
        hit = match_food(name, foods)
        if not hit["ok"] or hit["name"] not in frequent or hit["name"] in avoid:
            continue
        alternative = smaller_alternative(hit["name"], foods)
        if not alternative:
            continue
        target = alternative.get("productName")
        target_kcal = alternative.get("energyKcal")
        if target in avoid or target_kcal is None or target_kcal >= hit["kcal"]:
            continue
        key = (hit["name"], target)
        if key in seen:
            continue
        seen.add(key)
        suggestions.append({
            "from": hit["name"],
            "to": target,
            "from_kcal": hit["kcal"],
            "to_kcal": target_kcal,
            "saved_kcal": hit["kcal"] - target_kcal,
            "reason": (
                f"常点「{hit['name']}」，营养表同时有「{target}」（{target_kcal} 千卡）"
                f"和「{hit['name']}」（{hit['kcal']} 千卡）"
            ),
        })
    return {"suggestions": suggestions}
