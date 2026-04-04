from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from memory_system.models import MemoryKind, MemoryTemperature, MemoryTier, SourceKind
from memory_system.service import MemoryService


class MemorySystemTests(unittest.TestCase):
    def _service(self, root: Path) -> MemoryService:
        return MemoryService.from_path(root / "memory_store.json")

    def test_search_prefers_more_relevant_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self._service(Path(temp_dir))
            service.remember(
                user_id="demo",
                content="用户下周去东京出差，偏好靠窗座位。",
                summary="东京出差，靠窗座位。",
                kind=MemoryKind.EPISODE,
                tier=MemoryTier.EPISODIC,
                source=SourceKind.CHAT,
                importance=0.8,
                tags=["东京", "旅行"],
            )
            service.remember(
                user_id="demo",
                content="用户正在整理 Python 项目结构。",
                summary="整理 Python 项目结构。",
                kind=MemoryKind.FACT,
                tier=MemoryTier.SEMANTIC,
                source=SourceKind.NOTE,
                importance=0.9,
                tags=["python", "项目"],
            )

            results = service.search(user_id="demo", query="东京 座位", limit=2)

            self.assertEqual(len(results), 1)
            self.assertIn("东京", results[0].record.summary)

    def test_context_includes_profile_and_procedure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self._service(Path(temp_dir))
            service.update_profile(
                "demo",
                goals=["打造个人 memory 中枢"],
                preferences=["偏好结构化 profile"],
            )
            service.remember(
                user_id="demo",
                content="先统一聊天、笔记和任务事件，再生成长期记忆。",
                summary="先统一事件流，再生成长期记忆。",
                kind=MemoryKind.PROCEDURE,
                tier=MemoryTier.PROCEDURAL,
                source=SourceKind.NOTE,
                temperature=MemoryTemperature.HOT,
                importance=0.85,
            )

            rendered = service.render_context(user_id="demo", query="memory 中枢")

            self.assertIn("打造个人 memory 中枢", rendered)
            self.assertIn("[Hot memories]", rendered)
            self.assertIn("先统一事件流", rendered)

    def test_repository_persists_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service = self._service(root)
            service.remember(
                user_id="demo",
                content="用户偏好可审计系统。",
                summary="偏好可审计系统。",
                kind=MemoryKind.PREFERENCE,
                tier=MemoryTier.SEMANTIC,
                source=SourceKind.MANUAL,
                temperature=MemoryTemperature.HOT,
                importance=0.9,
            )

            reloaded = self._service(root)
            results = reloaded.search(user_id="demo", query="可审计", limit=5)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].record.kind, MemoryKind.PREFERENCE)
            self.assertEqual(results[0].record.temperature, MemoryTemperature.HOT)

    def test_hot_memory_is_always_in_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self._service(Path(temp_dir))
            service.remember(
                user_id="demo",
                content="用户明确要求所有输出保持简洁直接。",
                summary="输出保持简洁直接。",
                kind=MemoryKind.PREFERENCE,
                tier=MemoryTier.SEMANTIC,
                source=SourceKind.MANUAL,
                temperature=MemoryTemperature.HOT,
                importance=0.95,
            )

            packet = service.assemble_context(user_id="demo", query="完全无关的问题")

            self.assertEqual(len(packet.hot_memories), 1)
            self.assertEqual(packet.hot_memories[0].temperature, MemoryTemperature.HOT)

    def test_seed_demo_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            service = self._service(Path(temp_dir))

            service.seed_demo("demo")
            service.seed_demo("demo")

            memories = service.repository.list_memories("demo")

            self.assertEqual(len(memories), 3)


if __name__ == "__main__":
    unittest.main()
