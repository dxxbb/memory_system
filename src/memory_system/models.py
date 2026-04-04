from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utc_now() -> datetime:
    return datetime.now(UTC)


def _isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat()


def _from_isoformat(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


class MemoryKind(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    EPISODE = "episode"
    PROCEDURE = "procedure"
    TASK = "task"


class MemoryTier(StrEnum):
    WORKING = "working"
    PROFILE = "profile"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class MemoryTemperature(StrEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"


class SourceKind(StrEnum):
    CHAT = "chat"
    NOTE = "note"
    CALENDAR = "calendar"
    TASK = "task"
    FILE = "file"
    MANUAL = "manual"
    IMPORT = "import"


@dataclass(slots=True)
class ProfileState:
    user_id: str
    preferences: list[str] = field(default_factory=list)
    goals: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    routines: list[str] = field(default_factory=list)
    people: dict[str, str] = field(default_factory=dict)
    updated_at: datetime = field(default_factory=utc_now)

    def merge(
        self,
        *,
        preferences: list[str] | None = None,
        goals: list[str] | None = None,
        constraints: list[str] | None = None,
        routines: list[str] | None = None,
        people: dict[str, str] | None = None,
    ) -> None:
        _append_unique(self.preferences, preferences or [])
        _append_unique(self.goals, goals or [])
        _append_unique(self.constraints, constraints or [])
        _append_unique(self.routines, routines or [])
        if people:
            self.people.update(people)
        self.updated_at = utc_now()

    def summary_lines(self) -> list[str]:
        sections: list[str] = []
        if self.preferences:
            sections.append("Preferences: " + "; ".join(self.preferences))
        if self.goals:
            sections.append("Goals: " + "; ".join(self.goals))
        if self.constraints:
            sections.append("Constraints: " + "; ".join(self.constraints))
        if self.routines:
            sections.append("Routines: " + "; ".join(self.routines))
        if self.people:
            people_lines = [f"{name}: {value}" for name, value in sorted(self.people.items())]
            sections.append("People: " + "; ".join(people_lines))
        return sections

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["updated_at"] = _isoformat(self.updated_at)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProfileState":
        return cls(
            user_id=payload["user_id"],
            preferences=list(payload.get("preferences", [])),
            goals=list(payload.get("goals", [])),
            constraints=list(payload.get("constraints", [])),
            routines=list(payload.get("routines", [])),
            people=dict(payload.get("people", {})),
            updated_at=_from_isoformat(payload.get("updated_at")) or utc_now(),
        )


@dataclass(slots=True)
class MemoryRecord:
    id: str
    user_id: str
    kind: MemoryKind
    tier: MemoryTier
    content: str
    summary: str
    source: SourceKind
    temperature: MemoryTemperature = MemoryTemperature.WARM
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    source_ref: str | None = None
    related_ids: list[str] = field(default_factory=list)
    supersedes: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    valid_at: datetime | None = None
    invalid_at: datetime | None = None

    @property
    def active(self) -> bool:
        return self.invalid_at is None

    @property
    def searchable_text(self) -> str:
        fields = [self.summary, self.content, *self.tags]
        return " ".join(part for part in fields if part)

    def invalidate(self) -> None:
        self.invalid_at = utc_now()
        self.updated_at = utc_now()

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["kind"] = self.kind.value
        payload["tier"] = self.tier.value
        payload["source"] = self.source.value
        payload["temperature"] = self.temperature.value
        payload["created_at"] = _isoformat(self.created_at)
        payload["updated_at"] = _isoformat(self.updated_at)
        payload["valid_at"] = _isoformat(self.valid_at)
        payload["invalid_at"] = _isoformat(self.invalid_at)
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "MemoryRecord":
        return cls(
            id=payload["id"],
            user_id=payload["user_id"],
            kind=MemoryKind(payload["kind"]),
            tier=MemoryTier(payload["tier"]),
            content=payload["content"],
            summary=payload["summary"],
            source=SourceKind(payload["source"]),
            temperature=MemoryTemperature(payload.get("temperature", MemoryTemperature.WARM.value)),
            tags=list(payload.get("tags", [])),
            metadata=dict(payload.get("metadata", {})),
            importance=float(payload.get("importance", 0.5)),
            source_ref=payload.get("source_ref"),
            related_ids=list(payload.get("related_ids", [])),
            supersedes=list(payload.get("supersedes", [])),
            created_at=_from_isoformat(payload.get("created_at")) or utc_now(),
            updated_at=_from_isoformat(payload.get("updated_at")) or utc_now(),
            valid_at=_from_isoformat(payload.get("valid_at")),
            invalid_at=_from_isoformat(payload.get("invalid_at")),
        )


@dataclass(slots=True)
class SearchResult:
    record: MemoryRecord
    score: float
    reasons: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "score": round(self.score, 4),
            "reasons": list(self.reasons),
        }


@dataclass(slots=True)
class ContextPacket:
    user_id: str
    query: str
    profile: ProfileState
    hot_memories: list[MemoryRecord]
    top_memories: list[SearchResult]
    recent_episodes: list[MemoryRecord]
    procedures: list[MemoryRecord]
    generated_at: datetime = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "query": self.query,
            "profile": self.profile.to_dict(),
            "hot_memories": [item.to_dict() for item in self.hot_memories],
            "top_memories": [item.to_dict() for item in self.top_memories],
            "recent_episodes": [item.to_dict() for item in self.recent_episodes],
            "procedures": [item.to_dict() for item in self.procedures],
            "generated_at": _isoformat(self.generated_at),
        }


def _append_unique(target: list[str], items: list[str]) -> None:
    seen = {value.casefold() for value in target}
    for item in items:
        key = item.casefold()
        if key in seen:
            continue
        target.append(item)
        seen.add(key)
