import csv
import json
import re
from io import StringIO

HEADER_RE = re.compile(r"\[(\d+)\]\{([^}]+)\}:")
NUMERIC_FIELDS = {
    "energyKj",
    "energyKcal",
    "protein",
    "fat",
    "carbohydrate",
    "sodium",
    "calcium",
}


def parse_nutrition(payload):
    if isinstance(payload, str):
        stripped = payload.strip()
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError:
            return _from_toon(stripped)
    if isinstance(payload, list):
        return _from_rows(payload)
    if isinstance(payload, dict):
        foods = payload.get("foods")
        if isinstance(foods, list) and "data" not in payload:
            return _from_rows(foods)
        data = payload.get("data")
        if isinstance(data, str):
            return _from_toon(data)
        if isinstance(data, list):
            return _from_rows(data)
        if isinstance(data, dict) and isinstance(data.get("foods"), list):
            return _from_rows(data["foods"])
    raise ValueError("无法识别营养表")


def _from_toon(text):
    lines = text.splitlines()
    header_at = None
    columns = None
    for index, line in enumerate(lines):
        matched = HEADER_RE.search(line.strip())
        if matched:
            header_at = index
            columns = [part.strip() for part in matched.group(2).split(",")]
            break
    if not columns:
        raise ValueError("营养表缺少 TOON 表头")
    foods = []
    skipped = 0
    for line in lines[header_at + 1:]:
        raw = line.strip()
        if not raw:
            continue
        row = next(csv.reader(StringIO(raw)))
        if len(row) != len(columns):
            skipped += 1
            continue
        item = {}
        for key, value in zip(columns, row):
            item[key] = _coerce(key, value.strip())
        if not item.get("productName"):
            skipped += 1
            continue
        foods.append(item)
    return {"foods": foods, "skipped_rows": skipped}


def _from_rows(rows):
    foods = []
    skipped = 0
    for row in rows:
        if not isinstance(row, dict) or not row.get("productName"):
            skipped += 1
            continue
        item = dict(row)
        if "energyKcal" in item and not isinstance(item["energyKcal"], (int, float)):
            item["energyKcal"] = _coerce("energyKcal", str(item["energyKcal"]))
        elif item.get("energyKcal") is None:
            item["energyKcal"] = None
        foods.append(item)
    return {"foods": foods, "skipped_rows": skipped}


def _coerce(key, value):
    if value == "" or value.lower() == "null":
        return None
    if key in NUMERIC_FIELDS:
        try:
            number = float(value)
        except ValueError:
            return None
        if number.is_integer():
            return int(number)
        return number
    return value
