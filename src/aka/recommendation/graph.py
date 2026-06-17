"""Static topic-graph recommender. Matches retrieved section paths against the
keys in recommendation.yaml and returns the related topics, de-duplicated and
order-preserving. Swap for an analytics/graph-backed impl later — same interface.
"""

from __future__ import annotations

from aka.domain.models import Chunk


class StaticGraphRecommender:
    def __init__(self, topic_graph: dict[str, list[str]]) -> None:
        # Normalise keys for case-insensitive substring matching.
        self._graph = {k.lower(): v for k, v in topic_graph.items()}

    def recommend(self, question: str, matched_chunks: list[Chunk]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        haystacks = [c.section_path.lower() for c in matched_chunks]
        for key, related in self._graph.items():
            if any(key in hay for hay in haystacks):
                for topic in related:
                    if topic not in seen:
                        seen.add(topic)
                        out.append(topic)
        return out[:5]
