MAX_ORDERS = 10


def normalize(payload):
    raw_orders = extract_orders(payload)
    fetched = len(raw_orders)
    used = raw_orders[:MAX_ORDERS]
    valid_orders = []
    canceled = 0
    unknown = 0
    empty = 0
    for order in used:
        if not isinstance(order, dict):
            unknown += 1
            continue
        kind = classify_status(order.get("orderStatus"))
        if kind == "canceled":
            canceled += 1
            continue
        if kind == "unknown":
            unknown += 1
            continue
        products = order.get("orderProductList") or order.get("products") or []
        lines = []
        for product in products:
            if isinstance(product, dict):
                lines.extend(expand_product(product))
        if not lines:
            empty += 1
            continue
        valid_orders.append({"lines": lines})
    return {
        "fetched_count": fetched,
        "used_count": len(used),
        "window_limited": fetched > MAX_ORDERS,
        "valid_count": len(valid_orders),
        "excluded_canceled": canceled,
        "excluded_status_unknown": unknown,
        "excluded_empty": empty,
        "orders": valid_orders,
    }


def extract_orders(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if isinstance(payload.get("orders"), list):
            return payload["orders"]
        data = payload.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("orders", "orderList", "list"):
                if isinstance(data.get(key), list):
                    return data[key]
    raise ValueError("无法识别订单")


def classify_status(status):
    if not isinstance(status, str):
        return "unknown"
    text = status.strip()
    if not text:
        return "unknown"
    if "取消" in text or "cancel" in text.lower():
        return "canceled"
    return "valid"


def expand_product(product):
    name = product_name(product)
    children_raw = product.get("comboItemList")
    if children_raw is None:
        children_raw = product.get("comboItems") or []
    children = [child for child in children_raw if isinstance(child, dict) and product_name(child)]
    if children:
        parent_qty = _known_qty(product)
        lines = []
        for child in children:
            child_qty = _known_qty(child)
            child_name = product_name(child)
            if parent_qty is None or child_qty is None:
                lines.append({
                    "name": child_name,
                    "quantity": None,
                    "role": "combo_child",
                    "pending_reason": "quantity_unclear",
                })
            else:
                lines.append({
                    "name": child_name,
                    "quantity": parent_qty * child_qty,
                    "role": "combo_child",
                })
        return lines
    if not name:
        return []
    qty = _known_qty(product)
    if qty is None:
        return [{
            "name": name,
            "quantity": None,
            "role": "item",
            "pending_reason": "quantity_unclear",
        }]
    return [{"name": name, "quantity": qty, "role": "item"}]


def _known_qty(item):
    if "quantity" not in item:
        return None
    return parse_qty(item.get("quantity"))


def product_name(item):
    if not isinstance(item, dict):
        return ""
    return str(item.get("productName") or item.get("name") or "").strip()


def parse_qty(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if number <= 0:
        return None
    if number.is_integer():
        return int(number)
    return number
