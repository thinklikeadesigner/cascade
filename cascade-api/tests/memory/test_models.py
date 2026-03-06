from cascade_api.memory.models import (
    MemoryRecord,
    SearchResult,
    MemoryLink,
    ExtractedMemory,
    Contradiction,
)


class TestMemoryRecord:
    def test_defaults(self):
        m = MemoryRecord(id="1", content="hello", memory_type="fact")
        assert m.tags == []
        assert m.confidence == 1.0
        assert m.decay_score == 1.0
        assert m.status == "active"
        assert m.embedding is None
        assert m.superseded_by is None
        assert m.source_id is None

    def test_all_fields(self):
        m = MemoryRecord(
            id="1",
            content="hello",
            memory_type="preference",
            tags=["ui"],
            confidence=0.8,
            decay_score=0.5,
            status="archived",
            embedding=[0.1, 0.2],
            superseded_by="2",
            source_id="conv-1",
        )
        assert m.tags == ["ui"]
        assert m.embedding == [0.1, 0.2]


class TestSearchResult:
    def test_fields(self):
        m = MemoryRecord(id="1", content="x", memory_type="fact")
        r = SearchResult(memory=m, similarity=0.9, rank_score=0.72)
        assert r.similarity == 0.9
        assert r.rank_score == 0.72


class TestMemoryLink:
    def test_fields(self):
        link = MemoryLink(id="1", source_id="a", target_id="b", link_type="supports")
        assert link.link_type == "supports"


class TestExtractedMemory:
    def test_defaults(self):
        e = ExtractedMemory(content="fact", memory_type="fact", tags=["x"])
        assert e.confidence == 1.0


class TestContradiction:
    def test_fields(self):
        c = Contradiction(
            new_fact="A", existing_memory_id="1", existing_content="B", explanation="conflicts"
        )
        assert c.explanation == "conflicts"
