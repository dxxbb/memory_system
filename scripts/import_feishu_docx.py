#!/usr/bin/env python3
"""One-off: fetch a Feishu docx via lark-cli and render to markdown.

Usage: feishu_docx_to_md.py <doc_id> > out.md
"""
import json
import subprocess
import sys

HEADING_TYPES = {3: 1, 4: 2, 5: 3, 6: 4, 7: 5, 8: 6, 9: 6, 10: 6, 11: 6}

_DOC_CACHE: dict[str, dict[str, dict]] = {}


def fetch_blocks(doc_id: str) -> list[dict]:
    out = subprocess.check_output(
        [
            "lark-cli", "api", "GET",
            f"/open-apis/docx/v1/documents/{doc_id}/blocks",
            "--params", '{"page_size":500}',
            "--page-all",
        ],
        stderr=subprocess.DEVNULL,
    ).decode()
    items: list[dict] = []
    for chunk in out.split("\n"):
        if not chunk.strip().startswith("{"):
            continue
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if obj.get("code") == 0 and "data" in obj:
            items.extend(obj["data"].get("items", []))
    if not items:
        obj = json.loads(out[out.find("{"):])
        items = obj["data"]["items"]
    return items


def render_elements(elements: list[dict]) -> str:
    parts: list[str] = []
    for el in elements:
        if "text_run" in el:
            tr = el["text_run"]
            txt = tr.get("content", "")
            s = tr.get("text_element_style", {}) or {}
            if link := s.get("link", {}).get("url"):
                txt = f"[{txt}]({link})"
            if s.get("inline_code"):
                txt = f"`{txt}`"
            if s.get("bold"):
                txt = f"**{txt}**"
            if s.get("italic"):
                txt = f"*{txt}*"
            if s.get("strikethrough"):
                txt = f"~~{txt}~~"
            parts.append(txt)
        elif "mention_doc" in el:
            m = el["mention_doc"]
            parts.append(f"[{m.get('title','')}]({m.get('url','')})")
        elif "mention_user" in el:
            parts.append(f"@{el['mention_user'].get('user_id','')}")
        elif "equation" in el:
            parts.append(f"$${el['equation'].get('content','')}$$")
        elif "reminder" in el:
            pass
        else:
            parts.append("")
    return "".join(parts)


def _doc_index(doc_id: str) -> dict[str, dict]:
    if doc_id not in _DOC_CACHE:
        blocks = fetch_blocks(doc_id)
        _DOC_CACHE[doc_id] = {b["block_id"]: b for b in blocks}
    return _DOC_CACHE[doc_id]


def render(blocks: list[dict], doc_id: str | None = None) -> str:
    by_id = {b["block_id"]: b for b in blocks}
    if doc_id:
        _DOC_CACHE[doc_id] = by_id
    root = next((b for b in blocks if not b.get("parent_id")), blocks[0])

    lines: list[str] = []
    visited: set[tuple[str, str]] = set()

    def walk(block_id: str, index: dict[str, dict], depth: int, list_depth: int):
        b = index.get(block_id)
        if not b:
            return
        bt = b["block_type"]
        is_list = bt in (12, 13)
        is_toggle = bt == 15
        if bt == 1:  # page title
            title = render_elements(b.get("page", {}).get("elements", []))
            lines.append(f"# {title}\n")
        elif bt == 2:  # text
            text = render_elements(b.get("text", {}).get("elements", []))
            lines.append(text)
        elif bt in HEADING_TYPES:
            level = HEADING_TYPES[bt]
            key = {3: "heading1", 4: "heading2", 5: "heading3", 6: "heading4",
                   7: "heading5", 8: "heading6", 9: "heading7", 10: "heading8", 11: "heading9"}[bt]
            text = render_elements(b.get(key, {}).get("elements", []))
            lines.append(f"{'#' * level} {text}")
        elif bt == 12:  # bullet
            text = render_elements(b.get("bullet", {}).get("elements", []))
            lines.append(f"{'  ' * list_depth}- {text}")
        elif bt == 13:  # ordered
            text = render_elements(b.get("ordered", {}).get("elements", []))
            lines.append(f"{'  ' * list_depth}1. {text}")
        elif bt == 14:  # code
            code_blk = b.get("code", {})
            text = render_elements(code_blk.get("elements", []))
            lines.append(f"```\n{text}\n```")
        elif bt == 15:  # quote
            text = render_elements(b.get("quote", {}).get("elements", []))
            lines.append(f"> {text}")
        elif bt == 17:  # todo
            todo = b.get("todo", {})
            text = render_elements(todo.get("elements", []))
            done = todo.get("style", {}).get("done", False)
            box = "[x]" if done else "[ ]"
            lines.append(f"{'  ' * list_depth}- {box} {text}")
        elif bt == 19:  # callout
            pass  # container, children render below
        elif bt == 21:  # divider
            lines.append("---")
        elif bt == 22:  # file
            lines.append(f"[file: {b.get('file',{}).get('name','')}]")
        elif bt == 27:  # image
            lines.append("[image]")
        elif bt == 31:  # sheet
            lines.append(f"[sheet: token={b.get('sheet',{}).get('token','')}]")
        elif bt == 32:  # table
            lines.append("[table]")
        elif bt == 34:  # view (embedded)
            lines.append(f"[embed: {b.get('view',{}).get('view_type','')}]")
        elif bt == 30:  # mindnote
            lines.append("[mindnote]")
        elif bt == 43:  # board (whiteboard embed)
            token = b.get("board", {}).get("token", "")
            lines.append(f"[board: token={token}]")
        elif bt == 49:  # source_synced — source of a sync; render children only
            pass
        elif bt == 50:  # reference_synced — inline content from another doc
            rs = b.get("reference_synced", {})
            src_doc = rs.get("source_document_id")
            src_block = rs.get("source_block_id")
            key = (src_doc or "", src_block or "")
            if not src_doc or not src_block:
                lines.append("[synced block: missing reference]")
            elif key in visited:
                lines.append("[synced block: cycle skipped]")
            else:
                visited.add(key)
                try:
                    src_index = _doc_index(src_doc)
                except Exception as e:
                    lines.append(f"[synced block: fetch failed {e}]")
                else:
                    walk(src_block, src_index, depth, list_depth)
        else:
            lines.append(f"[unsupported block_type={bt}]")

        child_list_depth = list_depth + 1 if (is_list or is_toggle) else list_depth
        for cid in b.get("children", []) or []:
            walk(cid, index, depth + 1, child_list_depth)

    walk(root["block_id"], by_id, 0, 0)
    md = "\n\n".join(l for l in lines if l.strip() != "" or l == "")
    md = "\n".join(l.rstrip() for l in md.split("\n"))
    while "\n\n\n" in md:
        md = md.replace("\n\n\n", "\n\n")
    return md.strip() + "\n"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: feishu_docx_to_md.py <doc_id>", file=sys.stderr)
        return 2
    doc_id = sys.argv[1]
    blocks = fetch_blocks(doc_id)
    sys.stdout.write(render(blocks, doc_id))
    return 0


if __name__ == "__main__":
    sys.exit(main())
