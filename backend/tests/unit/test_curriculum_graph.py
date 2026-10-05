"""Deterministic curriculum-graph rules (FR-CUR-002, AC-006). Pure unit tests, no services."""

from __future__ import annotations

import math
import random
from decimal import Decimal

import pytest

from app.services.curriculum_graph import (
    EdgeIn,
    FlatUnit,
    TopicIn,
    VectorItem,
    break_cycles,
    build_flat_order,
    cosine_similarity,
    cross_subject_scope_allowed,
    find_cycle,
    find_duplicates,
    find_orphans,
    has_cycle,
    is_duplicate,
    normalize_id,
    select_edge_to_drop,
    validate_graph,
)


def e(key: str, a: str, b: str, conf: float | str) -> EdgeIn:
    return EdgeIn(edge_key=key, topic_id=a, prereq_topic_id=b, confidence=conf)


def test_acyclic_graph_untouched():
    result = break_cycles([e("1", "A", "B", 0.5), e("2", "B", "C", 0.5)])
    assert result.dropped == ()
    assert len(result.kept) == 2


def test_two_node_cycle_detected():
    cycle = find_cycle([e("1", "A", "B", 0.8), e("2", "B", "A", 0.4)])
    assert cycle is not None and {x.edge_key for x in cycle} == {"1", "2"}


def test_ac006_drops_0_4_edge_keeps_0_8_acyclic():
    result = break_cycles([e("ab", "A", "B", 0.8), e("ba", "B", "A", 0.4)])
    assert [d.edge.edge_key for d in result.dropped] == ["ba"]
    assert [k.edge_key for k in result.kept] == ["ab"]
    assert not has_cycle(result.kept)
    assert "cycle" in result.dropped[0].reason


def test_equal_confidence_drops_ascending_first():
    # A->B and B->A tie at 0.5; ascending normalized (topic_id, prereq_topic_id): ("a","b") < ("b","a")
    result = break_cycles([e("ba", "B", "A", 0.5), e("ab", "A", "B", 0.5)])
    assert [d.edge.edge_key for d in result.dropped] == ["ab"]


def test_tie_break_is_by_pair_not_input_order():
    edges = [e("3", "C", "A", 0.3), e("1", "A", "B", 0.3), e("2", "B", "C", 0.3)]
    for ordering in (edges, list(reversed(edges)), [edges[1], edges[2], edges[0]]):
        result = break_cycles(ordering)
        assert [d.edge.edge_key for d in result.dropped] == ["1"]  # ("a","b") is smallest


def test_normalization_is_case_insensitive_uuid_compare():
    assert normalize_id(" ABC-DEF ") == "abc-def"
    upper = e("u", "BBBB", "AAAA", 0.5)
    lower = e("l", "aaaa", "bbbb", 0.5)
    # normalized pairs: ("bbbb","aaaa") vs ("aaaa","bbbb") -> the second sorts first
    assert select_edge_to_drop([upper, lower]).edge_key == "l"


def test_lowest_confidence_wins_over_id_order():
    victim = select_edge_to_drop([e("1", "A", "B", 0.9), e("2", "B", "C", 0.1), e("3", "C", "A", 0.5)])
    assert victim.edge_key == "2"


def test_overlapping_cycles_repeat_until_acyclic():
    edges = [
        e("1", "A", "B", 0.9),
        e("2", "B", "A", 0.2),
        e("3", "B", "C", 0.9),
        e("4", "C", "B", 0.3),
        e("5", "C", "A", 0.8),
    ]
    result = break_cycles(edges)
    assert not has_cycle(result.kept)
    assert {d.edge.edge_key for d in result.dropped} >= {"2", "4"}


def test_self_loop():
    result = break_cycles([e("1", "A", "A", 0.7), e("2", "A", "B", 0.7)])
    assert [d.edge.edge_key for d in result.dropped] == ["1"]
    assert [k.edge_key for k in result.kept] == ["2"]


def test_decimal_confidences_compare_exactly():
    result = break_cycles([e("1", "A", "B", Decimal("0.800")), e("2", "B", "A", Decimal("0.799"))])
    assert [d.edge.edge_key for d in result.dropped] == ["2"]


def test_empty_edges():
    assert break_cycles([]).kept == ()
    assert find_cycle([]) is None


def test_result_always_acyclic_property():
    rng = random.Random(20261004)
    for _ in range(200):
        n = rng.randint(2, 8)
        nodes = [f"T{i}" for i in range(n)]
        edges = []
        used = set()
        for k in range(rng.randint(1, 20)):
            a, b = rng.choice(nodes), rng.choice(nodes)
            if (a, b) in used:
                continue
            used.add((a, b))
            edges.append(e(f"e{k}", a, b, rng.choice([0.1, 0.2, 0.5, 0.5, 0.9])))
        result = break_cycles(edges)
        assert not has_cycle(result.kept)
        assert len(result.kept) + len(result.dropped) == len(edges)
        # determinism: shuffled input yields the identical set of dropped edges
        shuffled = edges[:]
        rng.shuffle(shuffled)
        again = break_cycles(shuffled)
        assert {d.edge.edge_key for d in again.dropped} == {d.edge.edge_key for d in result.dropped}


def test_deterministic_for_same_input_order():
    edges = [e("1", "A", "B", 0.5), e("2", "B", "C", 0.5), e("3", "C", "A", 0.5), e("4", "B", "A", 0.5)]
    first = break_cycles(edges)
    second = break_cycles(list(edges))
    assert [d.edge.edge_key for d in first.dropped] == [d.edge.edge_key for d in second.dropped]


def test_orphan_topic_flagged_blocking():
    topics = [TopicIn("b", "u1"), TopicIn("a", None)]
    assert find_orphans(topics) == ["a"]
    verdict = validate_graph(topics, [], [], Decimal("0.92"))
    assert verdict.orphans == ("a",)
    assert not verdict.passed
    assert any("no Unit" in r for r in verdict.blocking_reasons)


def test_validate_graph_passes_clean_graph_and_dropped_edge_does_not_block():
    topics = [TopicIn("A", "u1"), TopicIn("B", "u1")]
    verdict = validate_graph(topics, [e("1", "A", "B", 0.8), e("2", "B", "A", 0.4)], [], Decimal("0.92"))
    assert verdict.passed
    assert len(verdict.dropped) == 1 and verdict.remaining_cycle is None


def unit(angle_cos: float) -> list[float]:
    """Unit vector whose cosine similarity to [1, 0] is `angle_cos`."""
    return [angle_cos, math.sqrt(1 - angle_cos * angle_cos)]


def test_duplicate_flagged_only_strictly_above_0_92():
    base = VectorItem("a", "cfg", [1.0, 0.0])
    above = VectorItem("b", "cfg", unit(0.93))
    below_vec = unit(0.91)
    below = VectorItem("c", "cfg", [below_vec[0], -below_vec[1]])
    pairs = find_duplicates([base, above, below], Decimal("0.92"))
    assert [(p.topic_id, p.other_topic_id) for p in pairs] == [("a", "b")]


def test_0_92_exact_not_flagged():
    assert is_duplicate(0.92, Decimal("0.92")) is False
    assert is_duplicate(0.9200000000001, Decimal("0.92")) is False  # float noise below 12 places
    assert is_duplicate(0.921, Decimal("0.92")) is True
    base = VectorItem("a", "cfg", [1.0, 0.0])
    exact = VectorItem("b", "cfg", unit(0.92))
    assert find_duplicates([base, exact], Decimal("0.92")) == []


def test_different_embedding_configs_never_compared():
    a = VectorItem("a", "cfg1", [1.0, 0.0])
    b = VectorItem("b", "cfg2", [1.0, 0.0])
    assert find_duplicates([a, b], Decimal("0.92")) == []


def test_cosine_similarity_edge_cases():
    assert cosine_similarity([0.0, 0.0], [1.0, 0.0]) == 0.0
    assert cosine_similarity([2.0, 0.0], [1.0, 0.0]) == 1.0
    with pytest.raises(ValueError):
        cosine_similarity([1.0], [1.0, 2.0])


def test_threshold_change_changes_result():
    a = VectorItem("a", "cfg", [1.0, 0.0])
    b = VectorItem("b", "cfg", unit(0.95))
    assert find_duplicates([a, b], Decimal("0.92"))
    assert not find_duplicates([a, b], Decimal("0.96"))


def test_flat_order_builder_unit_order_and_no_edges():
    specs = build_flat_order([FlatUnit("u2", "Trees", 2), FlatUnit("u1", "Basics", 1)])
    assert [(s.unit_id, s.order_index) for s in specs] == [("u1", 1), ("u2", 2)]
    assert build_flat_order([]) == []


def test_cross_subject_scope_rule():
    assert cross_subject_scope_allowed(current_semester=3, target_semester=2, same_program=True)
    assert not cross_subject_scope_allowed(current_semester=3, target_semester=3, same_program=True)
    assert not cross_subject_scope_allowed(current_semester=3, target_semester=4, same_program=True)
    assert not cross_subject_scope_allowed(current_semester=3, target_semester=1, same_program=False)
