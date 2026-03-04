"""CoreMemory — single markdown document per tenant, optimistically locked."""
from __future__ import annotations

import re

from cascade_memory.errors import StoreLimitError
from cascade_memory.protocols.store import MemoryStore


class CoreMemory:
    def __init__(self, store: MemoryStore, limit: int = 3000):
        self._store = store
        self._limit = limit

    async def read(self, tenant_id: str) -> tuple[str, int]:
        return await self._store.get_core(tenant_id)

    async def append(self, tenant_id: str, section: str, text: str) -> int:
        content, version = await self._store.get_core(tenant_id)
        header = f"## {section}"
        if header in content:
            # Find end of section (next ## or end of string)
            pattern = re.compile(rf"({re.escape(header)}.*?)(?=\n## |\Z)", re.DOTALL)
            match = pattern.search(content)
            if match:
                section_end = match.end()
                new_content = content[:section_end] + "\n" + text + content[section_end:]
            else:
                new_content = content + "\n" + text
        else:
            separator = "\n\n" if content else ""
            new_content = content + separator + header + "\n" + text

        if len(new_content) > self._limit:
            raise StoreLimitError(
                f"Core memory would exceed {self._limit} chars "
                f"({len(new_content)} chars). Move details to archival memory first."
            )
        return await self._store.upsert_core(tenant_id, new_content, version)

    async def replace(self, tenant_id: str, old: str, new: str) -> int:
        content, version = await self._store.get_core(tenant_id)
        if old not in content:
            raise ValueError(f"Text not found in core memory: {old!r}")
        new_content = content.replace(old, new, 1)
        if len(new_content) > self._limit:
            raise StoreLimitError(
                f"Core memory would exceed {self._limit} chars "
                f"({len(new_content)} chars)."
            )
        return await self._store.upsert_core(tenant_id, new_content, version)

    async def overwrite(self, tenant_id: str, content: str, expected_version: int) -> int:
        if len(content) > self._limit:
            raise StoreLimitError(
                f"Core memory would exceed {self._limit} chars ({len(content)} chars)."
            )
        return await self._store.upsert_core(tenant_id, content, expected_version)
