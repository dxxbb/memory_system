from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from threading import RLock

from memory_system.models import MemoryRecord, ProfileState


class JsonMemoryRepository:
    """Small local-first repository for the reference implementation."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        if not self.path.exists():
            self._save({"profiles": {}, "memories": []})

    def get_profile(self, user_id: str) -> ProfileState:
        payload = self._load()
        stored = payload["profiles"].get(user_id)
        if stored is None:
            return ProfileState(user_id=user_id)
        return ProfileState.from_dict(stored)

    def save_profile(self, profile: ProfileState) -> None:
        payload = self._load()
        payload["profiles"][profile.user_id] = profile.to_dict()
        self._save(payload)

    def list_memories(self, user_id: str | None = None) -> list[MemoryRecord]:
        payload = self._load()
        items = [MemoryRecord.from_dict(item) for item in payload["memories"]]
        if user_id is None:
            return items
        return [item for item in items if item.user_id == user_id]

    def get_memory(self, memory_id: str) -> MemoryRecord | None:
        for item in self.list_memories():
            if item.id == memory_id:
                return item
        return None

    def get_memory_by_source_ref(self, user_id: str, source_ref: str) -> MemoryRecord | None:
        for item in self.list_memories(user_id):
            if item.source_ref == source_ref:
                return item
        return None

    def save_memory(self, record: MemoryRecord) -> None:
        payload = self._load()
        memories = payload["memories"]
        for index, item in enumerate(memories):
            if item["id"] == record.id:
                memories[index] = record.to_dict()
                break
        else:
            memories.append(record.to_dict())
        self._save(payload)

    def _load(self) -> dict:
        with self._lock:
            with self.path.open("r", encoding="utf-8") as handle:
                return json.load(handle)

    def _save(self, payload: dict) -> None:
        with self._lock:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f"{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)
            os.replace(temp_path, self.path)
