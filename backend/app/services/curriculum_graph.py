"""Deterministic curriculum-graph validation (FR-CUR-002, BUS-021/022, SRS Section 18).

PURE and LLM-free by design (`.claude/rules/deterministic-services.md`): no database, no
network, no `langchain*`/`anthropic`/`app.agents`/`app.prompts` imports (a static test
enforces this). The Curriculum Agent's output is only ever *input* to these functions.

Exact algorithms (never approximated):

* Cycle handling. An edge `(topic_id, prereq_topic_id, confidence)` means "topic_id requires
  prereq_topic_id". A DFS (nodes and edges visited in ascending normalized-id order, so the
  result is reproducible) finds a cycle; among the cycle's edges the one with the LOWEST
  confidence is dropped. Equal-confidence edges are sorted by the normalized
  `(topic_id, prereq_topic_id)` pair ascending and the first is dropped. This repeats until the
  graph is acyclic.
* Duplicates. Cosine similarity of two Topic vectors that share the same embedding
  configuration is a duplicate only when STRICTLY greater than the threshold (SRS initial 0.92; 0.72 for
  bge-m3 per ADR-0020).
  The similarity is rounded to 12 decimals first so float noise cannot move a value that is
  mathematically equal to the threshold across it.
* Orphans. A Topic with no Unit.
"""

from __future__ import annotations

import math
from collections.abc import Hashable, Iterable, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

SIMILARITY_ROUNDING_DECIMALS = 12


def normalize_id(value: object) -> str:
    """Case- and whitespace-insensitive id form used for every ordering/tie-break."""
    return str(value).strip().lower()


@dataclass(frozen=True)
class EdgeIn:
    """`edge_key` is the caller's handle (e.g. the edge row id) and never affects the result."""

    edge_key: Hashable
    topic_id: str
    prereq_topic_id: str
    confidence: Decimal | float | str

    @property
    def sort_key(self) -> tuple[str, str]:
        return (normalize_id(self.topic_id), normalize_id(self.prereq_topic_id))

    @property
    def conf(self) -> Decimal:
        return Decimal(str(self.confidence))


@dataclass(frozen=True)
class DroppedEdge:
    edge: EdgeIn
    cycle: tuple[str, ...]  # normalized topic ids around the cycle, in traversal order
    reason: str


@dataclass(frozen=True)
class CycleBreakResult:
    kept: tuple[EdgeIn, ...]
    dropped: tuple[DroppedEdge, ...]


def find_cycle(edges: Sequence[EdgeIn]) -> list[EdgeIn] | None:
    """First cycle found by an iterative DFS in ascending normalized-id order, or None."""
    outgoing: dict[str, list[EdgeIn]] = {}
    nodes: set[str] = set()
    for e in edges:
        a, b = normalize_id(e.topic_id), normalize_id(e.prereq_topic_id)
        nodes.update((a, b))
        outgoing.setdefault(a, []).append(e)
    for lst in outgoing.values():
        lst.sort(key=lambda e: e.sort_key)

    WHITE, GREY, BLACK = 0, 1, 2
    color = dict.fromkeys(nodes, WHITE)
    for start in sorted(nodes):
        if color[start] != WHITE:
            continue
        color[start] = GREY
        path_edges: list[EdgeIn] = []
        stack: list[tuple[str, int]] = [(start, 0)]
        while stack:
            node, idx = stack[-1]
            adj = outgoing.get(node, [])
            if idx >= len(adj):
                color[node] = BLACK
                stack.pop()
                if path_edges:
                    path_edges.pop()
                continue
            stack[-1] = (node, idx + 1)
            edge = adj[idx]
            nxt = normalize_id(edge.prereq_topic_id)
            if color[nxt] == GREY:
                # The cycle is the path from `nxt` to `node` plus this closing edge.
                chain = [normalize_id(e.topic_id) for e in path_edges] + [node]
                begin = chain.index(nxt)
                return path_edges[begin:] + [edge]
            if color[nxt] == WHITE:
                color[nxt] = GREY
                path_edges.append(edge)
                stack.append((nxt, 0))
    return None


def has_cycle(edges: Sequence[EdgeIn]) -> bool:
    return find_cycle(edges) is not None


def select_edge_to_drop(cycle_edges: Sequence[EdgeIn]) -> EdgeIn:
    """Lowest confidence; ties: normalized (topic_id, prereq_topic_id) ascending, first one."""
    lowest = min(e.conf for e in cycle_edges)
    tied = sorted((e for e in cycle_edges if e.conf == lowest), key=lambda e: e.sort_key)
    return tied[0]


def break_cycles(edges: Iterable[EdgeIn]) -> CycleBreakResult:
    """Drop one edge per detected cycle until the graph is acyclic (FR-CUR-002)."""
    remaining = list(edges)
    dropped: list[DroppedEdge] = []
    while True:
        cycle = find_cycle(remaining)
        if cycle is None:
            break
        victim = select_edge_to_drop(cycle)
        remaining = [e for e in remaining if e.edge_key != victim.edge_key]
        path = tuple(normalize_id(e.topic_id) for e in cycle)
        dropped.append(
            DroppedEdge(
                edge=victim,
                cycle=path,
                reason=(
                    f"Dropped lowest-confidence edge ({victim.conf}) to break the prerequisite "
                    f"cycle {' -> '.join(path)} -> {path[0]}."
                ),
            )
        )
    return CycleBreakResult(kept=tuple(remaining), dropped=tuple(dropped))


# ----------------------------------------------------------------------------- orphans


@dataclass(frozen=True)
class TopicIn:
    topic_id: str
    unit_id: str | None


def find_orphans(topics: Iterable[TopicIn]) -> list[str]:
    """Topics without a Unit (blocking until assigned or removed)."""
    return sorted((t.topic_id for t in topics if t.unit_id is None), key=normalize_id)


# --------------------------------------------------------------------------- duplicates


@dataclass(frozen=True)
class VectorItem:
    topic_id: str
    embedding_config_id: str
    vector: Sequence[float]


@dataclass(frozen=True)
class DuplicatePair:
    topic_id: str
    other_topic_id: str
    similarity: float
    embedding_config_id: str


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError("vectors must have the same dimension")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return round(float(dot / (na * nb)), SIMILARITY_ROUNDING_DECIMALS)


def is_duplicate(similarity: float, threshold: Decimal | float | str) -> bool:
    """Strictly greater than the threshold: a similarity equal to 0.92 is NOT a duplicate."""
    return Decimal(str(round(similarity, SIMILARITY_ROUNDING_DECIMALS))) > Decimal(str(threshold))


def find_duplicates(items: Sequence[VectorItem], threshold: Decimal | float | str) -> list[DuplicatePair]:
    """Pairs above the threshold, only between vectors with the SAME embedding configuration."""
    ordered = sorted(items, key=lambda i: normalize_id(i.topic_id))
    pairs: list[DuplicatePair] = []
    for i, a in enumerate(ordered):
        for b in ordered[i + 1 :]:
            if a.embedding_config_id != b.embedding_config_id:
                continue
            sim = cosine_similarity(a.vector, b.vector)
            if is_duplicate(sim, threshold):
                pairs.append(DuplicatePair(a.topic_id, b.topic_id, sim, a.embedding_config_id))
    return pairs


# --------------------------------------------------------------------- whole-graph check


@dataclass(frozen=True)
class GraphValidation:
    kept_edges: tuple[EdgeIn, ...]
    dropped: tuple[DroppedEdge, ...]
    orphans: tuple[str, ...]
    duplicates: tuple[DuplicatePair, ...]
    remaining_cycle: tuple[str, ...] | None
    blocking_reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons


def validate_graph(
    topics: Sequence[TopicIn],
    edges: Sequence[EdgeIn],
    vectors: Sequence[VectorItem],
    threshold: Decimal | float | str,
) -> GraphValidation:
    """Run cycle, orphan and duplicate checks. Blocking: orphans and any cycle that remains.
    Duplicates and dropped cycle edges are flagged for Teacher visibility but do not block."""
    result = break_cycles(edges)
    orphans = find_orphans(topics)
    duplicates = find_duplicates(vectors, threshold)
    residual = find_cycle(result.kept)
    reasons: list[str] = []
    if orphans:
        reasons.append(f"{len(orphans)} Topic(s) have no Unit; assign a Unit or remove them.")
    remaining_path: tuple[str, ...] | None = None
    if residual is not None:
        remaining_path = tuple(normalize_id(e.topic_id) for e in residual)
        reasons.append("A prerequisite cycle remains in the graph.")
    return GraphValidation(
        kept_edges=result.kept,
        dropped=result.dropped,
        orphans=tuple(orphans),
        duplicates=tuple(duplicates),
        remaining_cycle=remaining_path,
        blocking_reasons=tuple(reasons),
    )


# ---------------------------------------------------------------- scope and flat fallback


def cross_subject_scope_allowed(*, current_semester: int, target_semester: int, same_program: bool) -> bool:
    """Plan A-6: a cross-subject prerequisite must live in the same Program, strictly earlier."""
    return same_program and target_semester < current_semester


@dataclass(frozen=True)
class FlatUnit:
    unit_id: str
    name: str
    order_index: int


@dataclass(frozen=True)
class FlatTopicSpec:
    unit_id: str
    name: str
    order_index: int


def build_flat_order(units: Iterable[FlatUnit]) -> list[FlatTopicSpec]:
    """Flat syllabus-unit-order fallback (FR-CUR-004): one Topic per Unit in Unit order,
    never any prerequisite edge."""
    return [
        FlatTopicSpec(unit_id=u.unit_id, name=u.name, order_index=pos)
        for pos, u in enumerate(sorted(units, key=lambda u: u.order_index), start=1)
    ]
