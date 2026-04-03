#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pretty reader for Reddit JSONL produced by scrape_reddit.py.

Features:
- Renders posts and nested comments as an ASCII tree (└─, ├─, │)
- Optional colors and wrapping
- Maximum comment depth control
- Interactive viewing (default): show one post at a time, press Tab to switch

Usage:
  # Interactive (default):
  python pretty_read.py claudecode_last10h.jsonl

  # Show all posts (non-interactive, original behavior):
  python pretty_read.py claudecode_last10h.jsonl --show-all --wrap 100
"""
import argparse
import copy
import json
import os
import select
import sys
import textwrap
import shutil
import termios
import threading
import tty
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
CYAN = "\x1b[36m"
YELLOW = "\x1b[33m"
GREEN = "\x1b[32m"
MAGENTA = "\x1b[35m"


def supports_color(stream) -> bool:
    if not stream.isatty():
        return False
    if os.environ.get("NO_COLOR"):
        return False
    return True


def c(text: str, style: str, enabled: bool) -> str:
    if not enabled:
        return text
    return f"{style}{text}{RESET}"


def wrap_lines(text: str, width: int) -> List[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = text.split("\n")
    lines: List[str] = []
    for p in paragraphs:
        if not p:
            lines.append("")
            continue
        lines.extend(textwrap.wrap(p, width=width, replace_whitespace=False, drop_whitespace=False))
    return lines



def build_comment_tree(comments: List[Dict[str, Any]], submission_fullname: str):
    nodes: Dict[str, Dict[str, Any]] = {}
    children: Dict[Optional[str], List[str]] = {}

    def add_child(pid: Optional[str], cid: str):
        if pid not in children:
            children[pid] = []
        children[pid].append(cid)

    for com in comments:
        fid = com.get("fullname") or ("t1_" + com.get("id", ""))
        nodes[fid] = com
        add_child(com.get("parent_id"), fid)

    roots = children.get(submission_fullname, [])
    return nodes, children, roots


def render_post(record: Dict[str, Any], args) -> str:
    post = record.get("post", {})
    comments = record.get("comments", [])

    title = post.get("title", "(no title)")
    author = post.get("author") or "[deleted]"
    score = post.get("score", 0)
    n_comments = post.get("num_comments", len(comments))
    created_iso = post.get("created_iso", "")
    permalink = post.get("permalink", "")
    selftext = (post.get("selftext") or "").strip()

    lines: List[str] = []
    lines.append(c(title, BOLD, args.colors))
    meta = f"by u/{author} | score {score} | comments {n_comments} | {created_iso}"
    lines.append(c(meta, DIM, args.colors))
    if permalink:
        lines.append(c(permalink, CYAN, args.colors))

    if selftext:
        for ln in wrap_lines(selftext, args.wrap):
            lines.append(ln)

    # Comments
    if comments:
        nodes, children, roots = build_comment_tree(comments, post.get("fullname"))
        if roots:
            lines.append("")
            lines.append(c("Comments:", BOLD, args.colors))
            for i, fid in enumerate(roots):
                is_last = i == len(roots) - 1
                lines.extend(render_comment(nodes, children, fid, prefix="", is_last=is_last, args=args, depth=0))
    else:
        lines.append("")
        lines.append(c("(no comments)", DIM, args.colors))

    return "\n".join(lines)


def render_comment(nodes: Dict[str, Any], children: Dict[Optional[str], List[str]], fid: str, *, prefix: str, is_last: bool, args, depth: int) -> List[str]:
    out: List[str] = []
    node = nodes.get(fid, {})
    if args.max_depth is not None and depth >= args.max_depth:
        return out

    branch = "└─" if is_last else "├─"
    author = node.get("author") or "[deleted]"
    score = node.get("score", 0)
    created_iso = node.get("created_iso", "")
    is_submitter = node.get("is_submitter", False)

    head = f"{branch} [ +{score} ] u/{author}{' (OP)' if is_submitter else ''} — {created_iso}"
    out.append(prefix + c(head, YELLOW if is_submitter else GREEN, args.colors))

    body = (node.get("body") or "").strip()
    if body:
        wrapped = wrap_lines(body, max(20, args.wrap - len(prefix) - 2))
        for w in wrapped:
            out.append(prefix + ("  " if is_last else "│ ") + w)

    # Children
    kids = children.get(fid, [])
    if kids:
        new_prefix = prefix + ("  " if is_last else "│ ")
        for i, kfid in enumerate(kids):
            k_last = i == len(kids) - 1
            out.extend(
                render_comment(
                    nodes,
                    children,
                    kfid,
                    prefix=new_prefix,
                    is_last=k_last,
                    args=args,
                    depth=depth + 1,
                )
            )

    return out


def translate_record(record: Dict[str, Any], max_workers: int = 8, on_progress=None) -> Dict[str, Any]:
    import deepseek_client

    translated = copy.deepcopy(record)
    refs: Dict[str, List[tuple]] = {}

    post = translated.get("post", {})
    title = post.get("title") or ""
    if title.strip():
        refs.setdefault(title, []).append(("post", "title"))
    selftext = post.get("selftext") or ""
    if selftext.strip():
        refs.setdefault(selftext, []).append(("post", "selftext"))

    comments = translated.get("comments", [])
    for i, com in enumerate(comments):
        body = com.get("body") or ""
        if body.strip():
            refs.setdefault(body, []).append(("comment", i, "body"))

    if not refs:
        return translated

    out: Dict[str, str] = {}
    total = len(refs)
    done = 0
    if on_progress is not None:
        on_progress(done, total)
    with ThreadPoolExecutor(max_workers=max_workers) as exe:
        fut_map = {}
        for text in refs:
            fut_map[exe.submit(deepseek_client.translate, text)] = text
        for fut in as_completed(fut_map):
            src = fut_map[fut]
            out[src] = fut.result().strip()
            done += 1
            if on_progress is not None:
                on_progress(done, total)

    for src, targets in refs.items():
        dst = out[src]
        for t in targets:
            if t[0] == "post":
                post[t[1]] = dst
            else:
                comments[t[1]][t[2]] = dst
    return translated


def read_key(timeout: float) -> Optional[str]:
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ready, _, _ = select.select([sys.stdin], [], [], timeout)
        if not ready:
            return None
        return sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_browse(records: List[Dict[str, Any]], args) -> int:
    """Simple interactive loop: print one post, initially truncated; press y to show the rest. No fullscreen.

    Keys:
    - t: toggle translation for current post (first press starts translation)
    - y: show the remaining lines of the current post
    - Tab/Space/Enter: next post
    - q or Esc: quit
    """
    if not records:
        print("(no posts)")
        return 0

    # If not a TTY, fall back to show-all (useful when piping output)
    if not sys.stdout.isatty() or not sys.stdin.isatty():
        for idx, rec in enumerate(records, start=1):
            print(c(f"\n=== Post #{idx} ===", MAGENTA, args.colors))
            print(render_post(rec, args))
        return 0

    n = len(records)
    idx = 0
    translated_records: Dict[int, Dict[str, Any]] = {}
    translated_view: Dict[int, bool] = {}
    translating: Dict[int, bool] = {}
    translation_error: Dict[int, str] = {}
    translation_progress: Dict[int, Dict[str, int]] = {}
    state_lock = threading.Lock()

    while True:
        if sys.stdout.isatty():
            print("\x1b[2J\x1b[H", end="")

        with state_lock:
            show_translated = translated_view.get(idx, False)
            current_translated = translated_records.get(idx)
            current_translating = translating.get(idx, False)
            current_error = translation_error.get(idx)
            current_progress = translation_progress.get(idx, {"done": 0, "total": 0})

        # Print header for current post
        if show_translated and current_translated is not None:
            print(c(f"\n=== Post {idx+1}/{n} [CN] ===", MAGENTA, args.colors))
            rec = current_translated
        else:
            print(c(f"\n=== Post {idx+1}/{n} ===", MAGENTA, args.colors))
            rec = records[idx]

        # Prepare content lines
        s = render_post(rec, args)
        lines = s.splitlines()

        # Decide how many lines to show initially based on terminal height
        try:
            sz = shutil.get_terminal_size(fallback=(80, 24))
            rows = getattr(sz, "lines", 24)
        except Exception:
            rows = 24
        page_len = max(10, rows - 6)  # leave some room for prompts

        printed = 0
        truncated = False
        if len(lines) <= page_len:
            for ln in lines:
                print(ln)
            printed = len(lines)
        else:
            for i in range(page_len):
                print(lines[i])
            printed = page_len
            truncated = True
            remaining = len(lines) - printed
            print(c(f"\n-- {remaining} more lines -- Press y to show the rest; t to translate; Tab/Space/Enter for next; q to quit --", DIM, args.colors))

        if current_translating:
            done = current_progress.get("done", 0)
            total = current_progress.get("total", 0)
            if total > 0:
                pct = int(done * 100 / total)
                print(c(f"-- translating current post... {done}/{total} ({pct}%) --", DIM, args.colors))
            else:
                print(c("-- translating current post... --", DIM, args.colors))
        if current_error:
            print(c(f"-- translation failed: {current_error} --", DIM, args.colors))
        if current_translated is not None and not current_translating:
            if show_translated:
                print(c("-- translated view, press t for original --", DIM, args.colors))
            else:
                print(c("-- translation ready, press t to view --", DIM, args.colors))
        if not truncated:
            print(c("-- Press t to translate; Tab/Space/Enter for next; q to quit --", DIM, args.colors))

        # Inner loop for current post: allow 'y' to expand or move on
        while True:
            sys.stdout.flush()
            ch = read_key(0.12)
            with state_lock:
                active = translating.get(idx, False)
                ready = translated_records.get(idx) is not None
                failed = translation_error.get(idx) is not None
                progress = translation_progress.get(idx, {"done": 0, "total": 0})
            if (
                active != current_translating
                or ready != (current_translated is not None)
                or failed != (current_error is not None)
                or progress.get("done", 0) != current_progress.get("done", 0)
                or progress.get("total", 0) != current_progress.get("total", 0)
            ):
                break
            if ch is None:
                continue
            if ch in ("q", "\x1b"):  # q or ESC
                return 0
            # Advance to next post
            if ch in ("\t", " ", "\r", "\n"):
                idx = (idx + 1) % n
                break
            if ch in ("t", "T"):
                with state_lock:
                    if idx in translated_records:
                        translated_view[idx] = not translated_view.get(idx, False)
                        continue
                    if translating.get(idx, False):
                        continue
                    translating[idx] = True
                    translation_error.pop(idx, None)
                    translation_progress[idx] = {"done": 0, "total": 0}

                def run_translate(post_idx: int):
                    try:
                        def on_progress(done: int, total: int):
                            with state_lock:
                                translation_progress[post_idx] = {"done": done, "total": total}

                        translated = translate_record(records[post_idx], 8, on_progress)
                        with state_lock:
                            translated_records[post_idx] = translated
                            translated_view[post_idx] = True
                    except Exception as e:
                        with state_lock:
                            translation_error[post_idx] = str(e)
                    finally:
                        with state_lock:
                            translating[post_idx] = False

                th = threading.Thread(target=run_translate, args=(idx,), daemon=True)
                th.start()
                break
            # Show remaining lines for current post
            if ch in ("y", "Y"):
                if truncated:
                    for i in range(printed, len(lines)):
                        print(lines[i])
                    printed = len(lines)
                    truncated = False
                    print(c("\n-- end of post -- Press t to translate; Tab/Space/Enter for next; q to quit --", DIM, args.colors))
                # stay in inner loop waiting for next key
                continue
            # Ignore other keys
            continue


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(
        description="Pretty print Reddit JSONL (posts + comments) as a tree"
    )
    ap.add_argument(
        "infile",
        nargs="?",
        default="claudecode_last10h.jsonl",
        help="Path to JSONL file produced by scrape_reddit.py",
    )
    ap.add_argument("--wrap", type=int, default=100, help="Wrap width for text")
    ap.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Max comment depth to render (None = no limit)",
    )
    ap.add_argument("--no-colors", dest="colors", action="store_false", help="Disable ANSI colors")
    ap.add_argument(
        "--colors", dest="colors", action="store_true", help="Force-enable ANSI colors if supported"
    )
    ap.add_argument(
        "--show-all",
        action="store_true",
        help="Show all posts sequentially (non-interactive). Default shows one at a time and lets you switch with Tab.",
    )
    ap.set_defaults(colors=supports_color(sys.stdout))
    args = ap.parse_args(argv)

    if not os.path.exists(args.infile):
        print(f"File not found: {args.infile}", file=sys.stderr)
        return 2

    # Load all records first so we can either show-all or browse interactively
    records: List[Dict[str, Any]] = []
    with open(args.infile, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"Skipping line {idx}: JSON decode error: {e}",
                    file=sys.stderr,
                )
                continue
            records.append(rec)

    if args.show_all:
        for idx, rec in enumerate(records, start=1):
            print(c(f"\n=== Post #{idx} ===", MAGENTA, args.colors))
            print(render_post(rec, args))
        return 0

    # Default: interactive
    return interactive_browse(records, args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
