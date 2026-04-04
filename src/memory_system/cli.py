from __future__ import annotations

import argparse
import json
from pathlib import Path

from memory_system.models import MemoryKind, MemoryTemperature, MemoryTier, SourceKind
from memory_system.service import MemoryService


DEFAULT_DB_PATH = Path("data/memory_store.json")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Personal memory system reference CLI.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="Path to the local JSON store.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Load demo data into the local store.")
    seed_parser.add_argument("--user", required=True, help="User identifier.")

    remember_parser = subparsers.add_parser("remember", help="Store a new memory record.")
    remember_parser.add_argument("--user", required=True)
    remember_parser.add_argument("--content", required=True)
    remember_parser.add_argument("--summary")
    remember_parser.add_argument("--kind", required=True, choices=[item.value for item in MemoryKind])
    remember_parser.add_argument("--tier", required=True, choices=[item.value for item in MemoryTier])
    remember_parser.add_argument("--source", required=True, choices=[item.value for item in SourceKind])
    remember_parser.add_argument("--temperature", default=MemoryTemperature.WARM.value, choices=[item.value for item in MemoryTemperature])
    remember_parser.add_argument("--importance", type=float, default=0.5)
    remember_parser.add_argument("--tag", action="append", default=[])

    profile_parser = subparsers.add_parser("profile", help="Update structured profile fields.")
    profile_parser.add_argument("--user", required=True)
    profile_parser.add_argument("--preference", action="append", default=[])
    profile_parser.add_argument("--goal", action="append", default=[])
    profile_parser.add_argument("--constraint", action="append", default=[])
    profile_parser.add_argument("--routine", action="append", default=[])
    profile_parser.add_argument("--person", action="append", default=[], help="Format: name:description")

    search_parser = subparsers.add_parser("search", help="Search relevant memories.")
    search_parser.add_argument("--user", required=True)
    search_parser.add_argument("--query", required=True)
    search_parser.add_argument("--limit", type=int, default=5)

    context_parser = subparsers.add_parser("context", help="Assemble prompt-ready context.")
    context_parser.add_argument("--user", required=True)
    context_parser.add_argument("--query", required=True)
    context_parser.add_argument("--limit", type=int, default=6)
    context_parser.add_argument("--format", choices=["json", "text"], default="text")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = MemoryService.from_path(args.db)

    if args.command == "seed":
        service.seed_demo(args.user)
        print(f"Seeded demo data for user={args.user} into {args.db}")
        return 0

    if args.command == "remember":
        record = service.remember(
            user_id=args.user,
            content=args.content,
            summary=args.summary,
            kind=MemoryKind(args.kind),
            tier=MemoryTier(args.tier),
            source=SourceKind(args.source),
            temperature=MemoryTemperature(args.temperature),
            importance=args.importance,
            tags=args.tag,
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "profile":
        people: dict[str, str] = {}
        for item in args.person:
            name, _, description = item.partition(":")
            if not name or not description:
                parser.error("--person must use name:description format")
            people[name.strip()] = description.strip()
        profile = service.update_profile(
            args.user,
            preferences=args.preference,
            goals=args.goal,
            constraints=args.constraint,
            routines=args.routine,
            people=people,
        )
        print(json.dumps(profile.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "search":
        results = service.search(user_id=args.user, query=args.query, limit=args.limit)
        print(json.dumps([item.to_dict() for item in results], ensure_ascii=False, indent=2))
        return 0

    if args.command == "context":
        if args.format == "json":
            packet = service.assemble_context(user_id=args.user, query=args.query, limit=args.limit)
            print(json.dumps(packet.to_dict(), ensure_ascii=False, indent=2))
            return 0
        print(service.render_context(user_id=args.user, query=args.query, limit=args.limit))
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 1
