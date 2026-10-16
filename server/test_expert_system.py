import itertools
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

from expert_system import CHOICES, RECOMMENDATION_RULES, forward_chain, recommend

SCRIPT = Path(__file__).with_name("expert_system.py")
RECIPE_BOOK = Path(__file__).parent.parent / "client" / "clientrecepies" / "src" / "pages" / "display" / "Display.js"


class RecommendTest(unittest.TestCase):
    def test_every_combination_yields_a_unique_recipe(self):
        recipes = set()
        for flour, fat, flavor in itertools.product(*CHOICES.values()):
            result = recommend({"flour": flour, "fat": fat, "flavor": flavor})
            self.assertIsNotNone(result["recipe"], (flour, fat, flavor))
            recipes.add(result["recipe"])
        self.assertEqual(len(recipes), 36)

    def test_known_recommendation_and_trace(self):
        result = recommend({"flour": "all_purpose_flour", "fat": "butter", "flavor": "lemon_orange_extract"})
        self.assertEqual(result["recipe"], "Lemon_butter_cookies")
        # Three classification rules, then one recommendation rule.
        self.assertEqual(len(result["trace"]), 4)
        self.assertTrue(result["trace"][-1].endswith("-> Lemon_butter_cookies"))

    def test_invalid_choice_is_rejected(self):
        with self.assertRaises(ValueError):
            recommend({"flour": "rice_flour", "fat": "butter", "flavor": "vanilla"})

    def test_missing_choice_is_rejected(self):
        with self.assertRaises(ValueError):
            recommend({"flour": "semolina", "fat": "butter"})

    def test_forward_chain_without_matching_facts_derives_nothing(self):
        memory, trace = forward_chain(set())
        self.assertEqual(memory, set())
        self.assertEqual(trace, [])


class RecipeBookTest(unittest.TestCase):
    def test_client_recipe_book_covers_every_inferable_recipe(self):
        book = set(re.findall(r"^  (\w+): \{$", RECIPE_BOOK.read_text(encoding="utf-8"), re.MULTILINE))
        inferable = {rule.conclusion[1] for rule in RECOMMENDATION_RULES}
        self.assertEqual(inferable - book, set())


class CommandLineTest(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)

    def test_outputs_json_recipe(self):
        completed = self.run_script(json.dumps({"flour": "bread_flour", "fat": "margarine", "flavor": "coffee_extract"}))
        self.assertEqual(completed.returncode, 0)
        self.assertEqual(json.loads(completed.stdout)["recipe"], "Coffee_Bread_margarine")

    def test_reports_invalid_json(self):
        completed = self.run_script("not json")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("error", json.loads(completed.stdout))


if __name__ == "__main__":
    unittest.main()
