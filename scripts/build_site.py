#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SITE_DIR = REPO_ROOT / "site"
DIAGRAMS_DIR = SITE_DIR / "diagrams"
CONTENT_PATH = SITE_DIR / "content.md"
OUTPUT_PATH = SITE_DIR / "index.html"


def slugify(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def parse_markdown_sections(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current_section: str | None = None
    current_field: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        if current_section and current_field:
            sections.setdefault(current_section, {})[current_field] = "\n".join(buffer).strip()
        buffer = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        if line.startswith("# "):
            flush()
            current_section = slugify(line[2:])
            current_field = None
            continue
        if line.startswith("## "):
            flush()
            current_field = slugify(line[3:])
            continue
        buffer.append(line)

    flush()
    return sections


def load_json(name: str) -> dict:
    return json.loads((DIAGRAMS_DIR / name).read_text(encoding="utf-8"))


def render_inline(text: str) -> str:
    pieces: list[str] = []
    index = 0
    length = len(text)

    while index < length:
        if text.startswith("**", index):
            end = text.find("**", index + 2)
            if end != -1:
                pieces.append(f"<strong>{render_inline(text[index + 2:end])}</strong>")
                index = end + 2
                continue
        if text.startswith("`", index):
            end = text.find("`", index + 1)
            if end != -1:
                pieces.append(f"<code>{html.escape(text[index + 1:end])}</code>")
                index = end + 1
                continue
        pieces.append(html.escape(text[index]))
        index += 1

    return "".join(pieces)


def render_paragraphs(text: str) -> str:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", text.strip()) if block.strip()]
    return "".join(f"<p>{render_inline(block)}</p>" for block in blocks)


def parse_list_block(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def parse_link_item(text: str) -> tuple[str, str]:
    label, href = [part.strip() for part in text.split("|", 1)]
    return label, href


def render_nav(items: list[str]) -> str:
    links = []
    for item in items:
        label, href = parse_link_item(item)
        links.append(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')
    return "\n".join(links)


def render_hero_strip(items: list[dict]) -> str:
    parts: list[str] = []
    for item in items:
        if item["kind"] == "node":
            parts.append(
                f"""
            <div class="hero-node {html.escape(item['class_name'])}">
              <h2>{html.escape(item['title'])}</h2>
              <p>{html.escape(item['subtitle'])}</p>
            </div>
            """.strip()
            )
        else:
            parts.append(f'<div class="hero-arrow">{html.escape(item["label"])}</div>')
    return "\n".join(parts)


def render_chip_cloud(items: list[str]) -> str:
    return "\n".join(f"<span>{html.escape(item)}</span>" for item in items)


def render_projection_grid(items: list[dict]) -> str:
    cards: list[str] = []
    for item in items:
        cards.append(
            f"""
            <div class="diagram-box projection-box">
              <h3>{html.escape(item['title'])}</h3>
              <p>{render_inline(item['subtitle'])}</p>
            </div>
            """.strip()
        )
    return "\n".join(cards)


def render_routing_table(data: dict) -> str:
    cells: list[str] = []
    for heading in data["columns"]:
        cells.append(f'<div class="routing-head">{html.escape(heading)}</div>')
    for row in data["rows"]:
        first, *rest = row
        cells.append(f'<div class="routing-cell strong">{html.escape(first)}</div>')
        for index, value in enumerate(rest, start=1):
            class_name = "routing-cell"
            if value == "可能不过夜，不进 Store":
                class_name += " muted"
            cells.append(f'<div class="{class_name}">{html.escape(value)}</div>')
    return "\n".join(cells)


def render_runtime_lanes(lanes: list[dict]) -> str:
    rendered: list[str] = []
    for lane in lanes:
        steps: list[str] = []
        for step_index, step in enumerate(lane["steps"]):
            steps.append(
                f"""
                <div class="flow-step">
                  <span>{html.escape(step['index'])}</span>
                  <div>
                    <h4>{html.escape(step['title'])}</h4>
                    <p>{html.escape(step['body'])}</p>
                  </div>
                </div>
                """.strip()
            )
            if step_index < len(lane["steps"]) - 1:
                steps.append('<div class="lane-arrow"></div>')
        rendered.append(
            f"""
            <div class="flow-lane {html.escape(lane['class_name'])}-lane">
              <div class="lane-head">
                <h3>{html.escape(lane['title'])}</h3>
                <p>{html.escape(lane['subtitle'])}</p>
              </div>
              {' '.join(steps)}
            </div>
            """.strip()
        )
    return "\n".join(rendered)


def render_platform_cards(cards: list[dict]) -> str:
    rendered: list[str] = []
    for card in cards:
        rendered.append(
            f"""
            <div class="platform-card {html.escape(card['class_name'])}">
              <h3>{html.escape(card['title'])}</h3>
              <p class="platform-entry">{render_inline(card['entry'])}</p>
              <p class="platform-note">{html.escape(card['note'])}</p>
            </div>
            """.strip()
        )
    return "\n".join(rendered)


def render_example_segments(segments: list[dict]) -> str:
    rendered: list[str] = []
    for segment in segments:
        if segment["kind"] == "bridge":
            rendered.append(f'<div class="example-bridge">{html.escape(segment["label"])}</div>')
            continue
        codes = "\n".join(f"<code>{html.escape(code)}</code>" for code in segment["codes"])
        rendered.append(
            f"""
            <div class="example-column">
              <div class="example-head">{html.escape(segment['head'])}</div>
              <h3>{html.escape(segment['title'])}</h3>
              {codes}
              <p>{html.escape(segment['body'])}</p>
            </div>
            """.strip()
        )
    return "\n".join(rendered)


def render_build_tracks(tracks: list[dict]) -> str:
    rendered: list[str] = []
    for track in tracks:
        rendered.append(
            f"""
            <div class="build-track">
              <h3>{html.escape(track['title'])}</h3>
              <p>{html.escape(track['body'])}</p>
            </div>
            """.strip()
        )
    return "\n".join(rendered)


def build_page() -> str:
    content = parse_markdown_sections(CONTENT_PATH)
    system_map = load_json("system-map.json")
    routing = load_json("routing.json")
    runtime = load_json("runtime.json")
    platforms = load_json("platforms.json")
    example = load_json("example.json")
    build = load_json("build.json")

    nav_links = render_nav(parse_list_block(content["nav"]["items"]))
    primary_label, primary_href = parse_link_item(content["hero"]["primary_cta"])
    secondary_label, secondary_href = parse_link_item(content["hero"]["secondary_cta"])

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Personal Memory System</title>
    <meta
      name="description"
      content="Capture, Store, Projections. A visual architecture page for the Personal Memory System."
    />
    <link rel="icon" href="./favicon.svg" type="image/svg+xml" />
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <!-- Generated from site/content.md and site/diagrams/*.json by scripts/build_site.py -->
    <div class="page-shell">
      <header class="hero">
        <nav class="topbar">
          <div class="brand">
            <span class="brand-mark">PMS</span>
            <span class="brand-copy">Personal Memory System</span>
          </div>
          <div class="topbar-links">
            {nav_links}
          </div>
        </nav>

        <div class="hero-card">
          <div class="hero-copy">
            <p class="eyebrow">{html.escape(content["hero"]["eyebrow"])}</p>
            <h1>{html.escape(content["hero"]["title"])}</h1>
            <p class="hero-text">{render_inline(content["hero"]["lead"])}</p>
            <div class="hero-actions">
              <a class="button button-primary" href="{html.escape(primary_href)}">{html.escape(primary_label)}</a>
              <a class="button button-secondary" href="{html.escape(secondary_href)}">{html.escape(secondary_label)}</a>
            </div>
          </div>

          <div class="hero-strip">
            {render_hero_strip(system_map["hero_strip"])}
          </div>
        </div>
      </header>

      <main>
        <section id="system" class="section">
          <div class="section-heading">
            <p class="eyebrow">{html.escape(content["system"]["eyebrow"])}</p>
            <h2>{html.escape(content["system"]["title"])}</h2>
            {render_paragraphs(content["system"]["lead"])}
          </div>

          <div class="diagram-frame system-map">
            <div class="system-column">
              <div class="diagram-box capture-box">
                <div class="diagram-title">
                  <span class="diagram-index">{html.escape(system_map["capture"]["index"])}</span>
                  <h3>{html.escape(system_map["capture"]["title"])}</h3>
                </div>
                <p class="diagram-copy">{html.escape(system_map["capture"]["copy"])}</p>
                <div class="chip-cloud">
                  {render_chip_cloud(system_map["capture"]["chips"])}
                </div>
              </div>
            </div>

            <div class="flow-bridge">
              <span>{html.escape(system_map["bridges"][0])}</span>
            </div>

            <div class="system-column">
              <div class="diagram-box store-box">
                <div class="diagram-title">
                  <span class="diagram-index">{html.escape(system_map["store"]["index"])}</span>
                  <h3>{html.escape(system_map["store"]["title"])}</h3>
                </div>
                <p class="diagram-copy">{html.escape(system_map["store"]["copy"])}</p>
                <div class="chip-cloud">
                  {render_chip_cloud(system_map["store"]["chips"])}
                </div>
              </div>
            </div>

            <div class="flow-bridge">
              <span>{html.escape(system_map["bridges"][1])}</span>
            </div>

            <div class="system-column">
              <div class="projection-grid">
                {render_projection_grid(system_map["projections"])}
              </div>
            </div>
          </div>

          <div class="feedback-band">
            <div class="feedback-label">{html.escape(content["system"]["feedback_label"])}</div>
            {render_paragraphs(content["system"]["feedback_text"])}
          </div>
        </section>

        <section id="routing" class="section">
          <div class="section-heading">
            <p class="eyebrow">{html.escape(content["routing"]["eyebrow"])}</p>
            <h2>{html.escape(content["routing"]["title"])}</h2>
            {render_paragraphs(content["routing"]["lead"])}
          </div>

          <div class="diagram-frame">
            <div class="routing-table">
              {render_routing_table(routing)}
            </div>
          </div>
        </section>

        <section id="runtime" class="section">
          <div class="section-heading">
            <p class="eyebrow">{html.escape(content["runtime"]["eyebrow"])}</p>
            <h2>{html.escape(content["runtime"]["title"])}</h2>
            {render_paragraphs(content["runtime"]["lead"])}
          </div>

          <div class="runtime-grid">
            {render_runtime_lanes(runtime["lanes"])}
          </div>
        </section>

        <section id="platforms" class="section">
          <div class="section-heading">
            <p class="eyebrow">{html.escape(content["platforms"]["eyebrow"])}</p>
            <h2>{html.escape(content["platforms"]["title"])}</h2>
            {render_paragraphs(content["platforms"]["lead"])}
          </div>

          <div class="diagram-frame platform-map">
            <div class="platform-center">
              <h3>{html.escape(platforms["center"]["title"])}</h3>
              <p>{html.escape(platforms["center"]["subtitle"])}</p>
            </div>
            {render_platform_cards(platforms["cards"])}
          </div>
        </section>

        <section id="example" class="section">
          <div class="section-heading">
            <p class="eyebrow">{html.escape(content["example"]["eyebrow"])}</p>
            <h2>{html.escape(content["example"]["title"])}</h2>
            {render_paragraphs(content["example"]["lead"])}
          </div>

          <div class="example-map">
            {render_example_segments(example["segments"])}
          </div>
        </section>

        <section id="build" class="section">
          <div class="section-heading">
            <p class="eyebrow">{html.escape(content["build"]["eyebrow"])}</p>
            <h2>{html.escape(content["build"]["title"])}</h2>
            {render_paragraphs(content["build"]["lead"])}
          </div>

          <div class="build-rails">
            {render_build_tracks(build["tracks"])}
          </div>
        </section>
      </main>
    </div>
  </body>
</html>
"""


def main() -> None:
    OUTPUT_PATH.write_text(build_page(), encoding="utf-8")
    print(f"Built {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
