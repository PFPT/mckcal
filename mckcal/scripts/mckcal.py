import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from lib.ledger import distill, tally, tally_self_report
from lib.normalize import normalize
from lib.nutrition import parse_nutrition
from lib.privacy import export_ledger, validate
from lib.recommend import quote, swap


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mckcal")
    sub = parser.add_subparsers(dest="command", required=True)

    parse_cmd = sub.add_parser("parse-nutrition")
    parse_cmd.add_argument("--raw", required=True)
    parse_cmd.add_argument("--out", required=True)
    parse_cmd.set_defaults(func=cmd_parse)

    normalize_cmd = sub.add_parser("normalize")
    normalize_cmd.add_argument("--raw", required=True)
    normalize_cmd.add_argument("--out", required=True)
    normalize_cmd.set_defaults(func=cmd_normalize)

    tally_cmd = sub.add_parser("tally")
    tally_cmd.add_argument("--foods", required=True)
    tally_cmd.add_argument("--orders")
    tally_cmd.add_argument("--answers")
    tally_cmd.add_argument("--out", required=True)
    tally_cmd.set_defaults(func=cmd_tally)

    distill_cmd = sub.add_parser("distill")
    distill_cmd.add_argument("--tally", required=True)
    distill_cmd.add_argument("--answers", required=True)
    distill_cmd.add_argument("--out", required=True)
    distill_cmd.set_defaults(func=cmd_distill)

    validate_cmd = sub.add_parser("validate")
    validate_cmd.add_argument("--ledger", required=True)
    validate_cmd.set_defaults(func=cmd_validate)

    export_cmd = sub.add_parser("export")
    export_cmd.add_argument("--ledger", required=True)
    export_cmd.add_argument("--out", required=True)
    export_cmd.set_defaults(func=cmd_export)

    quote_cmd = sub.add_parser("quote")
    quote_cmd.add_argument("--ledger", required=True)
    quote_cmd.add_argument("--basket", required=True)
    quote_cmd.set_defaults(func=cmd_quote)

    swap_cmd = sub.add_parser("swap")
    swap_cmd.add_argument("--ledger", required=True)
    swap_cmd.add_argument("--basket", required=True)
    swap_cmd.set_defaults(func=cmd_swap)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"[mckcal] {exc}", file=sys.stderr)
        return 2


def cmd_parse(args):
    result = parse_nutrition(load_input(args.raw))
    dump(args.out, result)
    print(f"[parse-nutrition] {len(result['foods'])} 行，跳过 {result['skipped_rows']} 行")
    return 0


def cmd_normalize(args):
    result = normalize(load_input(args.raw))
    dump(args.out, result)
    print(
        f"[normalize] 原始 {result['fetched_count']} 笔 → 纳入 {result['used_count']} 笔，"
        f"有效 {result['valid_count']} 笔，剔除取消 {result['excluded_canceled']} 笔，"
        f"状态不明 {result['excluded_status_unknown']} 笔"
    )
    return 0


def cmd_tally(args):
    if bool(args.orders) == bool(args.answers):
        raise ValueError("tally 需要且只需要 --orders 或 --answers")
    foods = parse_nutrition(load_input(args.foods))["foods"]
    if args.answers:
        result = tally_self_report(load_input(args.answers), foods)
        print(f"[tally] 自述可匹配 {len(result['items'])} 项，待查 {len(result['pending_names'])} 项")
    else:
        result = tally(load_input(args.orders), foods)
        partial = sum(1 for order in result["orders"] if order["coverage"] == "partial")
        print(f"[tally] 有效 {result['valid_count']} 笔，部分可算 {partial} 笔，待查 {len(result['pending_names'])} 项")
    dump(args.out, result)
    return 0


def cmd_distill(args):
    result = distill(load_input(args.tally), load_input(args.answers))
    dump(args.out, result)
    ceiling = result["meal_ceiling_kcal"] if result["ceiling_confirmed"] else "待确认"
    print(f"[distill] 规则 {len(result['rules'])} 条，来源 {result['source_label']}，上限 {ceiling}")
    return 0


def cmd_validate(args):
    result = validate(load_input(args.ledger))
    if result["ok"]:
        print("[validate] 通过")
        return 0
    print("[validate] 未通过")
    for error in result["errors"]:
        print(error)
    return 1


def cmd_export(args):
    result = export_ledger(load_input(args.ledger), args.out)
    if not result["ok"]:
        detail = "、".join(result["hits"] + result["errors"])
        print(f"[export] 未写出：{detail}")
        return 1
    print(f"[export] 已写出 {len(result['files'])} 个文件")
    return 0


def cmd_quote(args):
    result = quote(load_input(args.ledger), load_input(args.basket))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_swap(args):
    result = swap(load_input(args.ledger), load_input(args.basket))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def load_input(path):
    raw = Path(path).read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def dump(path, obj):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
