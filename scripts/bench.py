#!/usr/bin/env python3
"""
bench.py — evaluate dxy's personal OS context delivery.

Spawns `claude -p` sessions against the vault to answer each question
(using CLAUDE.md auto-discovery as SP), asks a judge `claude -p` session
to rate each answer, writes a markdown report, exits non-zero if pass
thresholds aren't met.

Usage:
  bench.py --label <change-label>
  bench.py --label <label> --dry-run   # no CLI calls; validates parsing
  bench.py --label <label> --tier identity

Uses the `claude` CLI so no separate API key is needed (CC's existing auth
is reused). Tools are disabled (`--tools ""`) for Phase 1 pure-recall test.
Vault path defaults to $PERSONAL_OS_VAULT or ~/dxy_OS.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


AGENT_MODEL = "sonnet"   # CLI alias → latest sonnet
JUDGE_MODEL = "opus"     # CLI alias → latest opus
CLI_TIMEOUT_SEC = 180


# --- ANSI colors -----------------------------------------------------------
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"


def color_for(rating: str) -> str:
    if rating == "PASS":
        return GREEN
    if rating == "PASS-REACH":
        return YELLOW
    return RED


# --- Data model ------------------------------------------------------------


@dataclass
class Question:
    tier: str
    id: str
    text: str
    expected: str
    source: str = ""


@dataclass
class Result:
    question: Question
    actual: str
    rating: str
    reason: str


# --- Parsing ---------------------------------------------------------------


def parse_questions(path: Path) -> list[Question]:
    """Parse questions.md.

    Expected format (minimum):
      ## Tier: <tier_name>
      ### Q<id>
      **问**：<question>
      **期望**：<expected>
      **来源**：<source>  (optional)
    """
    text = path.read_text(encoding="utf-8")
    # strip frontmatter
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4 :]

    questions: list[Question] = []
    current_tier: str | None = None
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        m = re.match(r"##\s+Tier:\s*([a-zA-Z-]+)", line)
        if m:
            current_tier = m.group(1)
            i += 1
            continue
        m = re.match(r"###\s+(Q[\w.]+)", line)
        if m and current_tier:
            qid = m.group(1)
            # collect fields until next ### or ## or EOF
            fields: dict[str, str] = {}
            key: str | None = None
            buf: list[str] = []
            j = i + 1
            while j < len(lines):
                nxt = lines[j]
                if re.match(r"##+\s+", nxt):
                    break
                mm = re.match(r"\*\*([^*]+)\*\*[:：]\s*(.*)", nxt)
                if mm:
                    if key is not None:
                        fields[key] = "\n".join(buf).strip()
                    key = mm.group(1).strip()
                    buf = [mm.group(2)]
                else:
                    buf.append(nxt)
                j += 1
            if key is not None:
                fields[key] = "\n".join(buf).strip()
            i = j

            text_q = fields.get("问", "").strip()
            expected = fields.get("期望", "").strip()
            source = fields.get("来源", "").strip()
            if text_q and expected:
                questions.append(
                    Question(
                        tier=current_tier,
                        id=qid,
                        text=text_q,
                        expected=expected,
                        source=source,
                    )
                )
            continue
        i += 1

    return questions


# --- CLI calls (claude -p) -------------------------------------------------


def _run_claude(
    prompt: str,
    *,
    cwd: Path,
    model: str,
    system_prompt: str | None = None,
) -> str:
    """Invoke `claude -p` and return the assistant's text reply."""
    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--tools", "",
        "--output-format", "json",
        "--no-session-persistence",
        "--permission-mode", "default",
    ]
    if system_prompt is not None:
        cmd.extend(["--system-prompt", system_prompt])
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT_SEC,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"claude -p failed (rc={proc.returncode}): {proc.stderr.strip()[:400]}"
        )
    try:
        obj = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude -p output not JSON: {e}; stdout={proc.stdout[:400]}")
    result = obj.get("result")
    if not isinstance(result, str):
        raise RuntimeError(f"claude -p output missing 'result' field: {obj}")
    return result.strip()


def run_agent(vault: Path, question: str) -> str:
    # Agent: run from vault cwd so CLAUDE.md auto-discovery loads the real SP.
    return _run_claude(question, cwd=vault, model=AGENT_MODEL)


def run_judge(
    vault: Path,
    judge_prompt: str,
    q: Question,
    actual: str,
) -> tuple[str, str]:
    user = (
        f"Question: {q.text}\n\n"
        f"Expected answer: {q.expected}\n\n"
        f"Source: {q.source or '(n/a)'}\n\n"
        f"Tier: {q.tier}\n\n"
        f"Actual answer from agent:\n{actual}\n"
    )
    # Judge: explicit --system-prompt overrides CLAUDE.md auto-discovery so
    # the rubric isn't contaminated by project context.
    text = _run_claude(
        user,
        cwd=vault,
        model=JUDGE_MODEL,
        system_prompt=judge_prompt,
    )
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return "FAIL-WRONG", f"judge output not JSON: {text[:200]}"
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        return "FAIL-WRONG", f"judge JSON parse error: {e}"
    rating = str(obj.get("rating", "FAIL-WRONG"))
    reason = str(obj.get("reason", ""))
    return rating, reason


# --- Thresholds ------------------------------------------------------------


TIER_THRESHOLDS = {
    "identity": 1.00,      # 100% PASS/PASS-REACH, no FAIL-FORGOT
    "preferences": 1.00,
    "project": 0.90,
    "knowledge": 0.80,
    "reach-path": 0.80,
    "noise": 1.00,         # 0 FAIL-NOISE allowed
}


def is_pass_rating(rating: str, tier: str) -> bool:
    if tier == "noise":
        return rating != "FAIL-NOISE"
    return rating in ("PASS", "PASS-REACH")


def tier_pass_ratio(results: list[Result], tier: str) -> tuple[int, int, float]:
    subset = [r for r in results if r.question.tier == tier]
    if not subset:
        return 0, 0, 1.0
    passed = sum(1 for r in subset if is_pass_rating(r.rating, tier))
    return passed, len(subset), passed / len(subset)


def evaluate_thresholds(results: list[Result]) -> tuple[bool, list[str]]:
    """Return (overall_pass, failure_messages)."""
    failures: list[str] = []
    hard_fail = False

    for tier, thresh in TIER_THRESHOLDS.items():
        p, total, ratio = tier_pass_ratio(results, tier)
        if total == 0:
            continue
        if ratio < thresh:
            msg = f"{tier}: {p}/{total} ({ratio:.0%}) < threshold {thresh:.0%}"
            failures.append(msg)
            if tier in ("identity", "preferences"):
                forgot = [
                    r
                    for r in results
                    if r.question.tier == tier and r.rating == "FAIL-FORGOT"
                ]
                if forgot:
                    hard_fail = True
                    failures.append(
                        f"  HARD FAIL: {len(forgot)} FAIL-FORGOT in {tier}"
                    )
    return (len(failures) == 0), failures


# --- Report writing --------------------------------------------------------


def write_report(
    results: list[Result],
    report_path: Path,
    label: str,
    sp_rel_path: str,
    agent_model: str,
    judge_model: str,
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now().replace(microsecond=0).isoformat()

    lines = [
        "---",
        "kind: system",
        "---",
        "",
        f"# Bench Report · {label}",
        "",
        f"- Date: {now}",
        f"- SP tested: `{sp_rel_path}`",
        f"- Agent model: `{agent_model}`",
        f"- Judge model: `{judge_model}`",
        f"- Total questions: {len(results)}",
        "",
        "## Summary by tier",
        "",
        "| Tier | Passed | Total | Ratio | Threshold | Status |",
        "|---|---|---|---|---|---|",
    ]
    overall_pass, failures = evaluate_thresholds(results)
    for tier, thresh in TIER_THRESHOLDS.items():
        p, total, ratio = tier_pass_ratio(results, tier)
        if total == 0:
            continue
        ok = "✅" if ratio >= thresh else "❌"
        lines.append(
            f"| {tier} | {p} | {total} | {ratio:.0%} | {thresh:.0%} | {ok} |"
        )
    lines.append("")
    lines.append(f"**Overall**: {'PASS' if overall_pass else 'FAIL'}")
    if failures:
        lines.append("")
        lines.append("### Failures")
        for f in failures:
            lines.append(f"- {f}")
    lines.append("")

    lines.append("## Per-question")
    lines.append("")
    for r in results:
        lines.append(f"### {r.question.id}  [{r.question.tier}]  **{r.rating}**")
        lines.append(f"- **问**: {r.question.text}")
        lines.append(f"- **期望**: {r.question.expected}")
        if r.question.source:
            lines.append(f"- **来源**: {r.question.source}")
        lines.append(f"- **实际答案**:\n\n```\n{r.actual}\n```")
        lines.append(f"- **Judge reason**: {r.reason}")
        lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")


# --- Main ------------------------------------------------------------------


def vault_root() -> Path:
    env = os.environ.get("PERSONAL_OS_VAULT")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.home() / "dxy_OS").resolve()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", help="vault root (default $PERSONAL_OS_VAULT or ~/dxy_OS)")
    ap.add_argument("--label", required=True, help="change label (e.g. kb-sp-integration)")
    ap.add_argument("--sp", default="01 assist/SP/output/claude code/CLAUDE.md",
                    help="path (relative to vault) to the SP file to test against")
    ap.add_argument("--questions", default="06 system/bench/questions.md")
    ap.add_argument("--judge-prompt", default="06 system/bench/judge-prompt.md")
    ap.add_argument("--dry-run", action="store_true",
                    help="parse and list questions only; no API calls")
    ap.add_argument("--tier", help="only run questions in this tier")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve() if args.vault else vault_root()
    if not vault.is_dir():
        sys.stderr.write(f"vault not found: {vault}\n")
        return 2

    sp_path = vault / args.sp
    if not sp_path.exists():
        sys.stderr.write(f"sp file not found: {sp_path}\n")
        return 2

    questions_path = vault / args.questions
    judge_prompt_path = vault / args.judge_prompt

    sp_size = sp_path.stat().st_size
    judge_prompt_text = judge_prompt_path.read_text(encoding="utf-8")
    questions = parse_questions(questions_path)
    if args.tier:
        questions = [q for q in questions if q.tier == args.tier]
    if not questions:
        sys.stderr.write("no questions parsed\n")
        return 2

    print(f"{BOLD}Bench run: {args.label}{RESET}")
    print(f"  SP (via CLAUDE.md auto-discovery from vault): {args.sp} ({sp_size} bytes)")
    print(f"  Questions: {len(questions)}")
    print()

    if args.dry_run:
        for q in questions:
            print(f"  [{q.tier}] {q.id}: {q.text[:80]}")
        return 0

    results: list[Result] = []
    for q in questions:
        print(f"  [{q.tier}] {q.id}: {q.text[:70]}")
        try:
            actual = run_agent(vault, q.text)
            rating, reason = run_judge(vault, judge_prompt_text, q, actual)
        except Exception as e:  # noqa: BLE001
            actual = ""
            rating = "FAIL-WRONG"
            reason = f"cli error: {e}"
        results.append(Result(question=q, actual=actual, rating=rating, reason=reason))
        c = color_for(rating)
        print(f"    {c}{rating:<14}{RESET} {reason}")

    # Report
    date = dt.date.today().isoformat()
    report_rel = Path("system") / "bench" / "reports" / f"{date}-{args.label}.md"
    report_path = vault / report_rel
    write_report(results, report_path, args.label, args.sp, AGENT_MODEL, JUDGE_MODEL)

    print()
    overall_pass, failures = evaluate_thresholds(results)
    print(f"{BOLD}Overall: {GREEN if overall_pass else RED}{'PASS' if overall_pass else 'FAIL'}{RESET}")
    if failures:
        for f in failures:
            print(f"  {RED}{f}{RESET}")
    print(f"Report: {report_rel}")

    return 0 if overall_pass else 1


if __name__ == "__main__":
    sys.exit(main())
