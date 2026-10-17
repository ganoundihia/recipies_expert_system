import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.engine.inference import combine_cf, forward_chain
from app.kb.models import Rule

cfs = st.floats(min_value=-0.99, max_value=0.99, allow_nan=False)


def rule(rule_id, conditions, conclusion, cf=1.0, enabled=True):
    return Rule.model_validate({"id": rule_id, "if": conditions, "then": conclusion, "cf": cf, "explain": {"en": "x"}, "enabled": enabled})


@given(cfs, cfs)
def test_combine_cf_is_commutative_and_bounded(a, b):
    assert combine_cf(a, b) == pytest.approx(combine_cf(b, a))
    assert -1 <= combine_cf(a, b) <= 1


def test_combine_cf_known_values():
    assert combine_cf(0.6, 0.5) == pytest.approx(0.8)
    assert combine_cf(-0.6, -0.5) == pytest.approx(-0.8)
    assert combine_cf(0.6, -0.3) == pytest.approx(0.3 / 0.7)


def test_variables_bind_across_conditions():
    rules = [rule("F1", [["forbid_allergen", "?a"], ["allergen", "?i", "?a"]], ["forbidden", "?i"])]
    memory = forward_chain([("forbid_allergen", "dairy"), ("allergen", "butter", "dairy"), ("allergen", "flour", "gluten")], rules)
    assert memory.holds(("forbidden", "butter"))
    assert not memory.holds(("forbidden", "flour"))


def test_chaining_and_cf_propagation():
    rules = [rule("A", [["craving", "?f"]], ["prefer", "?f"], cf=0.8), rule("B", [["prefer", "chocolate"]], ["prefer", "coffee"], cf=0.5)]
    memory = forward_chain([("craving", "chocolate")], rules)
    assert memory.cf(("prefer", "chocolate")) == pytest.approx(0.8)
    assert memory.cf(("prefer", "coffee")) == pytest.approx(0.4)  # 0.5 x weakest premise 0.8


def test_each_instantiation_fires_once_and_evidence_combines():
    rules = [rule("A", [["x"]], ["goal"], cf=0.5), rule("B", [["y"]], ["goal"], cf=0.5)]
    memory = forward_chain([("x",), ("y",)], rules)
    assert len(memory.firings) == 2
    assert memory.cf(("goal",)) == pytest.approx(0.75)


def test_negative_and_disabled_rules():
    rules = [rule("N", [["skill", "beginner"]], ["prefer", "hard"], cf=-0.7), rule("D", [["skill", "beginner"]], ["prefer", "easy"], enabled=False)]
    memory = forward_chain([("skill", "beginner")], rules)
    assert memory.cf(("prefer", "hard")) == pytest.approx(-0.7)
    assert memory.cf(("prefer", "easy")) == 0
