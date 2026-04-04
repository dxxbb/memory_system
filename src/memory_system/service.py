from __future__ import annotations

import re
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from memory_system.models import ContextPacket, MemoryKind, MemoryRecord, MemoryTemperature, MemoryTier, ProfileState, SearchResult, SourceKind
from memory_system.storage import JsonMemoryRepository

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


class MemoryService:
    def __init__(self, repository: JsonMemoryRepository) -> None:
        self.repository = repository

    @classmethod
    def from_path(cls, path: str | Path) -> "MemoryService":
        return cls(JsonMemoryRepository(path))

    def update_profile(
        self,
        user_id: str,
        *,
        preferences: list[str] | None = None,
        goals: list[str] | None = None,
        constraints: list[str] | None = None,
        routines: list[str] | None = None,
        people: dict[str, str] | None = None,
    ) -> ProfileState:
        profile = self.repository.get_profile(user_id)
        profile.merge(
            preferences=preferences,
            goals=goals,
            constraints=constraints,
            routines=routines,
            people=people,
        )
        self.repository.save_profile(profile)
        return profile

    def remember(
        self,
        *,
        user_id: str,
        content: str,
        kind: MemoryKind,
        tier: MemoryTier,
        source: SourceKind,
        summary: str | None = None,
        temperature: MemoryTemperature = MemoryTemperature.WARM,
        tags: list[str] | None = None,
        importance: float = 0.5,
        metadata: dict | None = None,
        source_ref: str | None = None,
        related_ids: list[str] | None = None,
        supersedes: list[str] | None = None,
    ) -> MemoryRecord:
        existing = None
        if source_ref:
            existing = self.repository.get_memory_by_source_ref(user_id, source_ref)

        if existing is not None:
            existing.kind = kind
            existing.tier = tier
            existing.content = content.strip()
            existing.summary = (summary or content).strip()
            existing.source = source
            existing.temperature = temperature
            existing.tags = list(tags or [])
            existing.metadata = dict(metadata or {})
            existing.importance = max(0.0, min(1.0, importance))
            existing.related_ids = list(related_ids or [])
            existing.supersedes = list(supersedes or [])
            existing.updated_at = datetime.now(UTC)
            existing.valid_at = existing.valid_at or datetime.now(UTC)
            existing.invalid_at = None
            self.repository.save_memory(existing)
            self._invalidate_superseded(existing.supersedes)
            return existing

        record = MemoryRecord(
            id=uuid4().hex,
            user_id=user_id,
            kind=kind,
            tier=tier,
            content=content.strip(),
            summary=(summary or content).strip(),
            source=source,
            temperature=temperature,
            tags=list(tags or []),
            metadata=dict(metadata or {}),
            importance=max(0.0, min(1.0, importance)),
            source_ref=source_ref,
            related_ids=list(related_ids or []),
            supersedes=list(supersedes or []),
            valid_at=datetime.now(UTC),
        )
        self.repository.save_memory(record)
        self._invalidate_superseded(record.supersedes)
        return record

    def search(
        self,
        *,
        user_id: str,
        query: str,
        limit: int = 5,
        tiers: set[MemoryTier] | None = None,
        kinds: set[MemoryKind] | None = None,
        tags: set[str] | None = None,
        active_only: bool = True,
    ) -> list[SearchResult]:
        candidates = self.repository.list_memories(user_id)
        now = datetime.now(UTC)
        normalized_tags = {tag.casefold() for tag in tags or set()}
        results: list[SearchResult] = []
        for record in candidates:
            if active_only and not record.active:
                continue
            if tiers and record.tier not in tiers:
                continue
            if kinds and record.kind not in kinds:
                continue
            if normalized_tags and not normalized_tags.intersection(tag.casefold() for tag in record.tags):
                continue
            score, reasons = _score_record(query, record, now)
            if score <= 0:
                continue
            results.append(SearchResult(record=record, score=score, reasons=reasons))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:limit]

    def assemble_context(self, *, user_id: str, query: str, limit: int = 6) -> ContextPacket:
        profile = self.repository.get_profile(user_id)
        hot_memories = [
            item
            for item in self.repository.list_memories(user_id)
            if item.active and item.temperature is MemoryTemperature.HOT
        ]
        hot_memories.sort(key=lambda item: (_temperature_score(item.temperature), item.importance, item.updated_at), reverse=True)
        top_memories = self.search(user_id=user_id, query=query, limit=limit)

        procedures = [
            item
            for item in self.repository.list_memories(user_id)
            if item.active and item.tier is MemoryTier.PROCEDURAL
        ]
        procedures.sort(key=lambda item: (_temperature_score(item.temperature), item.importance, item.updated_at), reverse=True)

        recent_episodes = [
            item
            for item in self.repository.list_memories(user_id)
            if item.active and item.tier is MemoryTier.EPISODIC
        ]
        recent_episodes.sort(key=lambda item: item.updated_at, reverse=True)

        return ContextPacket(
            user_id=user_id,
            query=query,
            profile=profile,
            hot_memories=hot_memories[:5],
            top_memories=top_memories,
            recent_episodes=recent_episodes[:3],
            procedures=procedures[:3],
        )

    def render_context(self, *, user_id: str, query: str, limit: int = 6) -> str:
        packet = self.assemble_context(user_id=user_id, query=query, limit=limit)
        lines = [
            f"User: {packet.user_id}",
            f"Query: {packet.query}",
            "",
            "[Profile]",
        ]
        profile_lines = packet.profile.summary_lines() or ["No profile data yet."]
        lines.extend(profile_lines)
        lines.extend(["", "[Hot memories]"])
        if not packet.hot_memories:
            lines.append("No hot memories.")
        else:
            for item in packet.hot_memories:
                lines.append(f"- ({item.tier.value}/{item.kind.value}) {item.summary}")
        lines.extend(["", "[Relevant memories]"])
        if not packet.top_memories:
            lines.append("No relevant memories.")
        else:
            for item in packet.top_memories:
                lines.append(f"- ({item.record.tier.value}/{item.record.kind.value}) {item.record.summary}")
        lines.extend(["", "[Recent episodes]"])
        if not packet.recent_episodes:
            lines.append("No recent episodes.")
        else:
            for item in packet.recent_episodes:
                lines.append(f"- {item.summary}")
        lines.extend(["", "[Procedures]"])
        if not packet.procedures:
            lines.append("No procedures.")
        else:
            for item in packet.procedures:
                lines.append(f"- {item.summary}")
        return "\n".join(lines)

    def seed_demo(self, user_id: str) -> None:
        self.update_profile(
            user_id,
            preferences=["偏好简洁直接的回答", "优先本地优先和可审计系统", "旅行时偏好靠窗座位"],
            goals=["打造个人 memory 中枢", "把零散笔记和聊天沉淀成可复用上下文"],
            constraints=["敏感信息默认不出本地", "需要能人工编辑和删除记忆"],
            routines=["每晚做 10 分钟日复盘", "每周整理项目优先级"],
            people={"Alice": "合作者，擅长产品设计", "Bob": "朋友，常一起安排行程"},
        )
        demo_records = [
            {
                "content": "用户计划下周去东京出差，周三下午到达，想把酒店安排在地铁站附近。",
                "summary": "下周东京出差，酒店最好靠近地铁站。",
                "kind": MemoryKind.EPISODE,
                "tier": MemoryTier.EPISODIC,
                "source": SourceKind.CHAT,
                "source_ref": "demo:trip:tokyo",
                "temperature": MemoryTemperature.WARM,
                "tags": ["旅行", "东京", "出差"],
                "importance": 0.85,
            },
            {
                "content": "用户明确表示做个人 AI memory 时，不能只用向量库，必须保留结构化 profile。",
                "summary": "个人 memory 方案必须包含结构化 profile，不接受 vector-only。",
                "kind": MemoryKind.PREFERENCE,
                "tier": MemoryTier.SEMANTIC,
                "source": SourceKind.MANUAL,
                "source_ref": "demo:architecture:profile-required",
                "temperature": MemoryTemperature.HOT,
                "tags": ["memory", "架构", "profile"],
                "importance": 0.95,
            },
            {
                "content": "在整理个人知识时，优先把聊天、笔记、任务和日历统一成事件流，再生成长期记忆。",
                "summary": "先统一事件流，再生成长期记忆。",
                "kind": MemoryKind.PROCEDURE,
                "tier": MemoryTier.PROCEDURAL,
                "source": SourceKind.NOTE,
                "source_ref": "demo:procedure:event-stream-first",
                "temperature": MemoryTemperature.HOT,
                "tags": ["pipeline", "etl", "procedure"],
                "importance": 0.88,
            },
        ]
        for item in demo_records:
            self.remember(user_id=user_id, **item)

    def _invalidate_superseded(self, superseded_ids: list[str]) -> None:
        for memory_id in superseded_ids:
            existing = self.repository.get_memory(memory_id)
            if existing is None or not existing.active:
                continue
            existing.invalidate()
            self.repository.save_memory(existing)


def _tokenize(text: str) -> set[str]:
    return {match.group(0).casefold() for match in TOKEN_PATTERN.finditer(text)}


def _recency_score(updated_at: datetime, now: datetime) -> float:
    age_seconds = max(0.0, (now - updated_at.astimezone(UTC)).total_seconds())
    age_days = age_seconds / 86400.0
    if age_days <= 1:
        return 1.0
    if age_days >= 90:
        return 0.0
    return max(0.0, 1.0 - (age_days / 90.0))


def _score_record(query: str, record: MemoryRecord, now: datetime) -> tuple[float, list[str]]:
    query_tokens = _tokenize(query)
    record_tokens = _tokenize(record.searchable_text)
    reasons: list[str] = []

    overlap = 0.0
    if query_tokens:
        matched = query_tokens.intersection(record_tokens)
        overlap = len(matched) / len(query_tokens)
        if matched:
            reasons.append("token overlap: " + ", ".join(sorted(matched)))

    recency = _recency_score(record.updated_at, now)
    if recency >= 0.8:
        reasons.append("recent")

    importance = max(0.0, min(1.0, record.importance))
    if importance >= 0.8:
        reasons.append("high importance")

    temperature = _temperature_score(record.temperature)
    if record.temperature is MemoryTemperature.HOT:
        reasons.append("hot memory")

    base_score = (overlap * 0.5) + (importance * 0.2) + (recency * 0.1) + (temperature * 0.2)
    if query_tokens and overlap == 0:
        return 0.0, []
    return base_score, reasons


def _temperature_score(temperature: MemoryTemperature) -> float:
    if temperature is MemoryTemperature.HOT:
        return 1.0
    if temperature is MemoryTemperature.WARM:
        return 0.5
    return 0.0
