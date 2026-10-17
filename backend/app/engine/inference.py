"""Forward-chaining inference engine with pattern variables and MYCIN-style certainty factors."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from app.kb.models import Rule

Fact = tuple[str, ...]
Bindings = dict[str, str]


def combine_cf(a: float, b: float) -> float:
    """Combine two certainty factors for the same conclusion (MYCIN parallel combination)."""
    if a >= 0 and b >= 0:
        return a + b * (1 - a)
    if a < 0 and b < 0:
        return a + b * (1 + a)
    denominator = 1 - min(abs(a), abs(b))
    return 0.0 if denominator == 0 else (a + b) / denominator


def combine_all(values: Iterable[float]) -> float:
    total = 0.0
    for value in values:
        total = combine_cf(total, value)
    return total


@dataclass(frozen=True)
class Firing:
    """One rule instantiation that fired, kept for the explanation trace."""

    rule_id: str
    conclusion: Fact
    cf: float
    bindings: tuple[tuple[str, str], ...]

    def explain(self, rule: Rule, lang: str, label=lambda value: value) -> str:
        text = rule.explain.get(lang)
        for name, value in self.bindings:
            text = text.replace(name, label(value))
        return text


@dataclass
class WorkingMemory:
    facts: dict[Fact, float] = field(default_factory=dict)
    firings: list[Firing] = field(default_factory=list)

    def cf(self, fact: Fact) -> float:
        return self.facts.get(fact, 0.0)

    def holds(self, fact: Fact, threshold: float = 0.2) -> bool:
        return self.cf(fact) >= threshold

    def query(self, *pattern: str) -> Iterator[tuple[Fact, float]]:
        for fact, cf in self.facts.items():
            if _unify(pattern, fact, {}) is not None:
                yield fact, cf

    def values(self, predicate: str) -> dict[str, float]:
        """Map of the first argument to its CF for every fact of the given predicate."""
        return {fact[1]: cf for fact, cf in self.facts.items() if fact[0] == predicate and len(fact) > 1}


def _unify(pattern: tuple[str, ...] | list[str], fact: Fact, bindings: Bindings) -> Bindings | None:
    if len(pattern) != len(fact):
        return None
    result = dict(bindings)
    for term, value in zip(pattern, fact, strict=True):
        if term.startswith("?"):
            if result.setdefault(term, value) != value:
                return None
        elif term != value:
            return None
    return result


def _matches(conditions: list[list[str]], memory: WorkingMemory, bindings: Bindings, cf: float) -> Iterator[tuple[Bindings, float]]:
    if not conditions:
        yield bindings, cf
        return
    first, rest = conditions[0], conditions[1:]
    for fact, fact_cf in list(memory.facts.items()):
        if fact_cf <= 0:
            continue
        extended = _unify(first, fact, bindings)
        if extended is not None:
            yield from _matches(rest, memory, extended, min(cf, fact_cf))


def forward_chain(facts: Iterable[Fact] | dict[Fact, float], rules: list[Rule], max_iterations: int = 50) -> WorkingMemory:
    """Fire every enabled rule instantiation once, until no new instantiation applies.

    A conclusion's CF is the rule CF times the weakest premise; conclusions reached
    by several instantiations are combined with :func:`combine_cf`.
    """
    memory = WorkingMemory(dict(facts) if isinstance(facts, dict) else {fact: 1.0 for fact in facts})
    fired: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    for _ in range(max_iterations):
        new_firing = False
        for rule in rules:
            if not rule.enabled:
                continue
            for bindings, premise_cf in list(_matches(rule.if_, memory, {}, 1.0)):
                key = (rule.id, tuple(sorted(bindings.items())))
                if key in fired:
                    continue
                fired.add(key)
                conclusion = tuple(bindings.get(term, term) for term in rule.then)
                cf = rule.cf * premise_cf
                memory.facts[conclusion] = combine_cf(memory.facts.get(conclusion, 0.0), cf)
                memory.firings.append(Firing(rule.id, conclusion, cf, key[1]))
                new_firing = True
        if not new_firing:
            break
    return memory
