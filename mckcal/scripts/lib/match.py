import re

SIZE_TOKENS = ("小杯", "中杯", "大杯", "小份", "中份", "大份", "小薯", "中薯", "大薯")
NEXT_SMALLER = {
    "大杯": "中杯",
    "中杯": "小杯",
    "大份": "中份",
    "中份": "小份",
    "大薯": "中薯",
    "中薯": "小薯",
}


def compact(name):
    if name is None:
        return ""
    return re.sub(r"\s+", "", str(name).replace("\u3000", " ")).strip()


def split_size(name):
    text = compact(name)
    sized = text[:-2] if text.endswith("套餐") else text
    found = [token for token in SIZE_TOKENS if token in sized]
    base = sized
    for token in found:
        base = base.replace(token, "")
    return {"compact": text, "base": base, "sizes": found}


def match_food(name, foods):
    query = split_size(name)
    if not query["compact"]:
        return {"ok": False, "reason": "empty_name"}
    prepared = []
    for food in foods:
        product = food.get("productName") or ""
        prepared.append({
            "parts": split_size(product),
            "kcal": food.get("energyKcal"),
            "name": product,
            "food": food,
        })
    exact = [item for item in prepared if item["parts"]["compact"] == query["compact"]]
    if len(exact) == 1:
        return _hit(exact[0])
    if len(exact) > 1:
        return {"ok": False, "reason": "ambiguous"}
    if query["compact"].endswith("套餐"):
        bare = query["compact"][:-2]
        bare_hits = [item for item in prepared if item["parts"]["compact"] == bare]
        if len(bare_hits) == 1:
            return _hit(bare_hits[0])
        if len(bare_hits) > 1:
            return {"ok": False, "reason": "ambiguous"}
    if len(query["sizes"]) > 1:
        return {"ok": False, "reason": "ambiguous_size"}
    if len(query["sizes"]) == 1:
        size = query["sizes"][0]
        sized = [
            item for item in prepared
            if item["parts"]["base"] == query["base"] and item["parts"]["sizes"] == [size]
        ]
        if len(sized) == 1:
            return _hit(sized[0])
        return {"ok": False, "reason": "size_unmatched"}
    candidates = [
        item for item in prepared
        if item["parts"]["base"] == query["base"] and query["base"]
    ]
    if len(candidates) == 1 and not candidates[0]["parts"]["sizes"]:
        return _hit(candidates[0])
    if candidates:
        return {"ok": False, "reason": "ambiguous_size"}
    return {"ok": False, "reason": "unmatched"}


def smaller_alternative(nutrition_name, foods):
    parts = split_size(nutrition_name)
    if len(parts["sizes"]) != 1:
        return None
    smaller = NEXT_SMALLER.get(parts["sizes"][0])
    if not smaller:
        return None
    hits = []
    for food in foods:
        food_parts = split_size(food.get("productName") or "")
        if food_parts["base"] == parts["base"] and food_parts["sizes"] == [smaller]:
            hits.append(food)
    if len(hits) != 1:
        return None
    if hits[0].get("energyKcal") is None:
        return None
    return hits[0]


def _hit(entry):
    if entry["kcal"] is None:
        return {"ok": False, "reason": "kcal_missing", "nutrition_name": entry["name"]}
    return {"ok": True, "name": entry["name"], "kcal": entry["kcal"], "reason": None}
