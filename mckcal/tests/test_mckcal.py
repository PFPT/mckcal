import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(SCRIPTS))

from lib.ledger import distill, tally, tally_self_report
from lib.normalize import normalize
from lib.nutrition import parse_nutrition
from lib.privacy import export_ledger, validate
from lib.recommend import quote, swap


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def menu():
    return parse_nutrition(load("nutrition_menu.json"))["foods"]


def ledger_from(orders_name, answers_name):
    normalized = normalize(load(orders_name))
    tallied = tally(normalized, menu())
    ledger = distill(tallied, load(answers_name))
    return normalized, tallied, ledger


class NutritionTest(unittest.TestCase):
    def test_official_toon_sample(self):
        parsed = parse_nutrition(load("nutrition_official.json"))
        self.assertEqual(parsed["skipped_rows"], 0)
        food = parsed["foods"][0]
        self.assertEqual(food["productName"], "猪柳麦满分")
        self.assertEqual(food["energyKcal"], 308)
        self.assertIsNone(food["nutritionDescription"])
        self.assertNotIn("2026-01-23", json.dumps(parsed, ensure_ascii=False))

    def test_menu_row_count(self):
        parsed = parse_nutrition(load("nutrition_menu.json"))
        self.assertEqual(len(parsed["foods"]), 8)
        self.assertEqual(parsed["foods"][0]["energyKcal"], 550)

    def test_skipped_short_row(self):
        parsed = parse_nutrition("[2]{productName,energyKcal}:\n  巨无霸,550\n  坏行\n")
        self.assertEqual(len(parsed["foods"]), 1)
        self.assertEqual(parsed["skipped_rows"], 1)


class NormalizeTest(unittest.TestCase):
    def test_habit_drops_cancel_unknown_and_secrets(self):
        normalized, _, _ = ledger_from("orders_habit.json", "answers_ceiling.json")
        self.assertEqual(normalized["fetched_count"], 5)
        self.assertEqual(normalized["valid_count"], 3)
        self.assertEqual(normalized["excluded_canceled"], 1)
        self.assertEqual(normalized["excluded_status_unknown"], 1)
        blob = json.dumps(normalized, ensure_ascii=False)
        for secret in ("OID-SHOULD-DROP", "测试门店不应出现", "STORE-1", "2026-10-01", "42.5", "13800138000", "某某小区"):
            self.assertNotIn(secret, blob)
        names = [line["name"] for line in normalized["orders"][0]["lines"]]
        self.assertEqual(names, ["巨无霸", "大薯", "可乐中杯"])

    def test_combo_does_not_add_parent_kcal(self):
        _, tallied, _ = ledger_from("orders_habit.json", "answers_ceiling.json")
        first = tallied["orders"][0]
        self.assertEqual(first["coverage"], "complete")
        self.assertEqual(first["matched_kcal"], 1120)
        self.assertNotIn("巨无霸套餐", [line["name"] for line in first["lines"]])

    def test_parent_quantity_scales_children_only(self):
        payload = {
            "orders": [{
                "orderStatus": "已完成",
                "orderProductList": [{
                    "productName": "巨无霸套餐",
                    "quantity": 2,
                    "comboItemList": [
                        {"productName": "巨无霸", "quantity": 1},
                        {"productName": "大薯", "quantity": 1},
                        {"productName": "可乐中杯", "quantity": 1},
                    ],
                }],
            }]
        }
        tallied = tally(normalize(payload), menu())
        self.assertEqual(tallied["orders"][0]["matched_kcal"], 2240)
        self.assertNotIn("巨无霸套餐", [line["name"] for line in tallied["orders"][0]["lines"]])

    def test_size_ambiguity_and_missing_size(self):
        _, tallied, _ = ledger_from("orders_size.json", "answers_ceiling.json")
        reasons = {line["name"]: line["reason"] for line in tallied["orders"][0]["lines"]}
        self.assertEqual(reasons["可乐"], "ambiguous_size")
        self.assertEqual(reasons["可乐小杯"], "size_unmatched")
        matched = [line for line in tallied["orders"][0]["lines"] if line["status"] == "matched"]
        self.assertEqual(matched[0]["nutrition_name"], "可乐中杯")
        self.assertEqual(matched[0]["kcal"], 140)
        self.assertEqual(tallied["orders"][0]["coverage"], "partial")

    def test_partial_sum_excludes_unknown_item(self):
        _, tallied, _ = ledger_from("orders_partial.json", "answers_ceiling.json")
        order = tallied["orders"][0]
        self.assertEqual(order["coverage"], "partial")
        self.assertEqual(order["matched_kcal"], 550)
        self.assertEqual(order["pending_names"], ["神秘新品"])

    def test_window_keeps_first_ten(self):
        orders = []
        for _ in range(10):
            orders.append({
                "orderStatus": "已完成",
                "orderProductList": [{"productName": "巨无霸", "quantity": 1}],
            })
        orders.append({
            "orderStatus": "已完成",
            "orderProductList": [{"productName": "板烧鸡腿堡", "quantity": 1}],
        })
        normalized = normalize(orders)
        self.assertTrue(normalized["window_limited"])
        self.assertEqual(normalized["used_count"], 10)
        self.assertEqual(normalized["valid_count"], 10)
        self.assertNotIn("板烧鸡腿堡", json.dumps(normalized, ensure_ascii=False))

    def test_missing_quantity_and_kcal_stay_pending(self):
        payload = {
            "orders": [{
                "orderStatus": "已完成",
                "orderProductList": [
                    {"productName": "巨无霸"},
                    {"productName": "空气汉堡", "quantity": 1},
                ],
            }]
        }
        foods = menu() + [{"productName": "空气汉堡", "energyKcal": None}]
        tallied = tally(normalize(payload), foods)
        reasons = {line["name"]: line for line in tallied["orders"][0]["lines"]}
        self.assertEqual(reasons["巨无霸"]["reason"], "quantity_unclear")
        self.assertIsNone(reasons["巨无霸"]["kcal"])
        self.assertEqual(reasons["空气汉堡"]["reason"], "kcal_missing")
        self.assertIsNone(reasons["空气汉堡"]["kcal"])

    def test_space_and_combo_suffix(self):
        payload = {
            "orders": [{
                "orderStatus": "已完成",
                "orderProductList": [
                    {"productName": "大 薯", "quantity": 1},
                    {"productName": "麦香鸡套餐", "quantity": 1},
                ],
            }]
        }
        tallied = tally(normalize(payload), menu())
        by_name = {line["nutrition_name"]: line["kcal"] for line in tallied["orders"][0]["lines"]}
        self.assertEqual(by_name["大薯"], 430)
        self.assertEqual(by_name["麦香鸡"], 400)

    def test_cancelled_english_status(self):
        payload = {
            "orders": [{
                "orderStatus": "Cancelled",
                "orderProductList": [{"productName": "巨无霸", "quantity": 1}],
            }]
        }
        normalized = normalize(payload)
        self.assertEqual(normalized["valid_count"], 0)
        self.assertEqual(normalized["excluded_canceled"], 1)


class DistillTest(unittest.TestCase):
    def test_rules_point_at_orders_and_ceiling_is_not_inferred(self):
        _, tallied, ledger = ledger_from("orders_habit.json", "answers_plain.json")
        self.assertEqual(ledger["typical_matched_kcal"], 830)
        self.assertIsNone(ledger["meal_ceiling_kcal"])
        self.assertFalse(ledger["ceiling_confirmed"])
        self.assertEqual([rule["name"] for rule in ledger["rules"]], ["巨无霸", "可乐中杯"])
        self.assertEqual(ledger["rules"][0]["times"], 3)
        self.assertEqual(ledger["rules"][0]["kcal_each"], 550)
        self.assertIn("最近 3 笔有效订单", ledger["rules"][0]["evidence"])
        self.assertIn("营养表「巨无霸」", ledger["rules"][0]["evidence"])
        self.assertNotIn("大薯", [rule["name"] for rule in ledger["rules"]])
        self.assertEqual(tallied["valid_count"], 3)

    def test_self_report_is_labeled(self):
        foods = menu()
        answers = load("answers_self.json")
        ledger = distill(tally_self_report(answers, foods), answers)
        self.assertEqual(ledger["source_label"], "自述")
        self.assertEqual(ledger["title"], "自述热量账")
        self.assertEqual(len(ledger["rules"]), 1)
        self.assertIn("自述「麦香鸡」出现 4 次", ledger["rules"][0]["evidence"])
        self.assertNotIn("最近", ledger["rules"][0]["evidence"])
        self.assertIn("可乐", ledger["pending_names"])
        self.assertEqual(ledger["meal_ceiling_kcal"], 600)


class ExportTest(unittest.TestCase):
    def test_share_card_and_private_report(self):
        _, _, ledger = ledger_from("orders_habit.json", "answers_ceiling.json")
        checked = validate(ledger)
        self.assertTrue(checked["ok"], checked["errors"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "账"
            result = export_ledger(ledger, out)
            self.assertTrue(result["ok"], result)
            share = (out / "可分享" / "热量账.md").read_text(encoding="utf-8")
            report = (out / "报告.md").read_text(encoding="utf-8")
            self.assertIn("来源：订单", share)
            self.assertIn("单餐上限：800 千卡", share)
            self.assertIn("巨无霸", share)
            self.assertIn("550", share)
            self.assertNotIn("中位", share)
            self.assertNotIn("OID-SHOULD-DROP", share)
            self.assertNotIn("测试门店不应出现", share)
            self.assertNotIn("13800138000", report)
            self.assertIn("中位", report)
            self.assertIn("830", report)

    def test_export_rejects_unconfirmed_ceiling(self):
        _, _, ledger = ledger_from("orders_habit.json", "answers_plain.json")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "账"
            result = export_ledger(ledger, out)
            self.assertFalse(result["ok"])
            self.assertIn("单餐上限还没确认", result["errors"])
            self.assertFalse(out.exists())

    def test_export_rejects_private_leaks(self):
        _, _, ledger = ledger_from("orders_habit.json", "answers_ceiling.json")
        poisons = {
            "订单号": "订单号 88888888",
            "地址": "某某小区1号楼",
            "积分": "积分 88",
            "金额": "35元",
        }
        for label, title in poisons.items():
            poisoned = dict(ledger)
            poisoned["title"] = title
            poisoned["blurb"] = ledger["blurb"]
            with tempfile.TemporaryDirectory() as tmp:
                out = Path(tmp) / "账"
                result = export_ledger(poisoned, out)
                self.assertFalse(result["ok"], label)
                self.assertIn(label, result["hits"])
                self.assertFalse(out.exists())

    def test_validate_rejects_order_id_key(self):
        _, _, ledger = ledger_from("orders_habit.json", "answers_ceiling.json")
        leaked = dict(ledger)
        leaked["orderId"] = "OID-LEAK"
        checked = validate(leaked)
        self.assertFalse(checked["ok"])


class RecommendTest(unittest.TestCase):
    def test_quote_partial_does_not_claim_full_meal(self):
        _, _, ledger = ledger_from("orders_habit.json", "answers_ceiling.json")
        result = quote(ledger, load("basket_partial.json"))
        self.assertEqual(result["matched_kcal"], 550)
        self.assertIsNone(result["full_meal_kcal"])
        self.assertIsNone(result["within_ceiling"])
        self.assertIn("部分可算", result["note"])
        self.assertIn("算不清", result["note"])
        self.assertEqual(result["pending_names"], ["神秘新品"])

    def test_quote_complete_meal_against_ceiling(self):
        _, _, ledger = ledger_from("orders_habit.json", "answers_ceiling.json")
        over = quote(ledger, load("basket_meal.json"))
        under = quote(ledger, load("basket_single.json"))
        self.assertEqual(over["full_meal_kcal"], 1120)
        self.assertFalse(over["within_ceiling"])
        self.assertEqual(under["full_meal_kcal"], 550)
        self.assertTrue(under["within_ceiling"])

    def test_swap_steps_down_only_when_both_rows_exist(self):
        _, _, ledger = ledger_from("orders_fries.json", "answers_ceiling.json")
        result = swap(ledger, load("basket_fries.json"))
        self.assertEqual(len(result["suggestions"]), 1)
        suggestion = result["suggestions"][0]
        self.assertEqual(suggestion["from"], "大薯")
        self.assertEqual(suggestion["to"], "中薯")
        self.assertEqual(suggestion["saved_kcal"], 150)
        rare = ledger_from("orders_habit.json", "answers_ceiling.json")[2]
        self.assertEqual(swap(rare, load("basket_fries.json"))["suggestions"], [])
        foods = [food for food in ledger["nutrition_foods"] if food["productName"] != "中薯"]
        ledger["nutrition_foods"] = foods
        self.assertEqual(swap(ledger, load("basket_fries.json"))["suggestions"], [])

    def test_swap_skips_avoided_item(self):
        _, _, ledger = ledger_from("orders_fries.json", "answers_ceiling.json")
        ledger["avoid"] = ["中薯"]
        self.assertEqual(swap(ledger, load("basket_fries.json"))["suggestions"], [])


class CliTest(unittest.TestCase):
    def test_pipeline_commands(self):
        script = SCRIPTS / "mckcal.py"
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            steps = [
                ["parse-nutrition", "--raw", str(FIXTURES / "nutrition_menu.json"), "--out", str(base / "foods.json")],
                ["normalize", "--raw", str(FIXTURES / "orders_habit.json"), "--out", str(base / "norm.json")],
                ["tally", "--orders", str(base / "norm.json"), "--foods", str(base / "foods.json"), "--out", str(base / "tally.json")],
                ["distill", "--tally", str(base / "tally.json"), "--answers", str(FIXTURES / "answers_ceiling.json"), "--out", str(base / "ledger.json")],
                ["validate", "--ledger", str(base / "ledger.json")],
                ["export", "--ledger", str(base / "ledger.json"), "--out", str(base / "out")],
            ]
            for step in steps:
                completed = subprocess.run([sys.executable, str(script), *step], check=False, capture_output=True, text=True)
                self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
            validate_run = subprocess.run(
                [sys.executable, str(script), "validate", "--ledger", str(base / "ledger.json")],
                check=False, capture_output=True, text=True,
            )
            self.assertIn("[validate] 通过", validate_run.stdout)
            self.assertTrue((base / "out" / "可分享" / "热量账.md").exists())


if __name__ == "__main__":
    unittest.main()
