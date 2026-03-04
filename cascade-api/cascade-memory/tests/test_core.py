import pytest
from cascade_memory.core import CoreMemory
from cascade_memory.stores.memory import InMemoryStore
from cascade_memory.errors import StoreLimitError, ConcurrencyError


@pytest.fixture
def core():
    store = InMemoryStore()
    return CoreMemory(store, limit=200)  # small limit for testing


class TestRead:
    async def test_empty(self, core):
        content, version = await core.read("t1")
        assert content == ""
        assert version == 0


class TestAppend:
    async def test_creates_section(self, core):
        v = await core.append("t1", "Preferences", "Likes dark mode")
        assert v == 1
        content, _ = await core.read("t1")
        assert "## Preferences" in content
        assert "Likes dark mode" in content

    async def test_appends_to_existing_section(self, core):
        await core.append("t1", "Preferences", "Likes dark mode")
        await core.append("t1", "Preferences", "Prefers vim")
        content, _ = await core.read("t1")
        assert content.count("## Preferences") == 1
        assert "Likes dark mode" in content
        assert "Prefers vim" in content

    async def test_multiple_sections(self, core):
        await core.append("t1", "Prefs", "A")
        await core.append("t1", "Goals", "B")
        content, _ = await core.read("t1")
        assert "## Prefs" in content
        assert "## Goals" in content

    async def test_size_limit(self, core):
        await core.append("t1", "S", "x" * 100)
        with pytest.raises(StoreLimitError):
            await core.append("t1", "S", "y" * 200)


class TestReplace:
    async def test_replaces_text(self, core):
        await core.append("t1", "Prefs", "morning person")
        v = await core.replace("t1", "morning person", "night owl")
        content, _ = await core.read("t1")
        assert "night owl" in content
        assert "morning person" not in content
        assert v >= 2

    async def test_replace_not_found(self, core):
        await core.append("t1", "Prefs", "hello")
        with pytest.raises(ValueError):
            await core.replace("t1", "nonexistent", "new")

    async def test_replace_size_limit(self, core):
        await core.append("t1", "S", "short")
        with pytest.raises(StoreLimitError):
            await core.replace("t1", "short", "x" * 300)


class TestOverwrite:
    async def test_overwrite(self, core):
        await core.append("t1", "S", "old")
        _, v = await core.read("t1")
        new_v = await core.overwrite("t1", "completely new", expected_version=v)
        content, _ = await core.read("t1")
        assert content == "completely new"
        assert new_v == v + 1

    async def test_overwrite_wrong_version(self, core):
        await core.append("t1", "S", "old")
        with pytest.raises(ConcurrencyError):
            await core.overwrite("t1", "new", expected_version=999)
