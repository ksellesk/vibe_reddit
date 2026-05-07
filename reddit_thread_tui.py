#!/usr/bin/env python3
import re
import sys
import json
import shutil
import unicodedata


def read_records(path):
    lines = [l.strip() for l in open(path).readlines()]
    return [json.loads(l) for l in lines if l]


def text_width(text):
    total = 0
    for ch in text:
        if unicodedata.combining(ch):
            continue
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            total += 2
        else:
            total += 1
    return total


def terminal_width():
    columns = shutil.get_terminal_size((92, 24)).columns
    return min(108, max(72, columns - 2))


def clean_text(text):
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def marker_indent(line):
    found = re.match(r"^([-*]|\d+[.)])\s+", line)
    if found:
        return text_width(found.group(0))
    return 0


def split_long_token(token, width):
    parts = []
    line = ""
    for ch in token:
        if line and text_width(line) + text_width(ch) > width:
            parts.append(line)
            line = ch
        else:
            line += ch
    if line:
        parts.append(line)
    return parts


def wrap_line(line, width):
    tokens = re.findall(r"\S+|\s+", line)
    wrapped = []
    current = ""
    gap = ""

    for token in tokens:
        if token.isspace():
            if current:
                gap = " "
            continue

        piece = gap + token if current else token
        if text_width(current) + text_width(piece) <= width:
            current += piece
            gap = ""
            continue

        if current:
            wrapped.append(current)

        if text_width(token) <= width:
            current = token
        else:
            pieces = split_long_token(token, width)
            wrapped.extend(pieces[:-1])
            current = pieces[-1]
        gap = ""

    if current:
        wrapped.append(current)
    return wrapped


def append_wrapped(lines, text, first_prefix, rest_prefix, width):
    first = True
    for raw in clean_text(text).split("\n"):
        line = raw.strip()
        if not line:
            lines.append(rest_prefix.rstrip())
            first = True
            continue

        prefix = first_prefix if first else rest_prefix
        body_width = max(28, width - text_width(prefix))
        wrapped = wrap_line(line, body_width)
        hang = marker_indent(line)

        for i, part in enumerate(wrapped):
            if first and i == 0:
                lines.append(first_prefix + part)
            elif i == 0:
                lines.append(rest_prefix + part)
            else:
                lines.append(rest_prefix + " " * hang + part)
        first = False


def append_field(lines, name, value, width):
    append_wrapped(lines, value, name.ljust(10), " " * 10, width)


def build_tree(record):
    nodes = {}
    children = {}
    post = record["post"]

    for comment in record.get("comments", []):
        fid = comment.get("fullname") or "t1_" + comment["id"]
        nodes[fid] = comment
        parent = comment.get("parent_id")
        children.setdefault(parent, []).append(fid)

    return nodes, children, children.get(post["fullname"], [])


def score_text(score):
    if score > 0:
        return "+" + str(score)
    return str(score)


def render_comment(lines, nodes, children, fid, prefix, last, width):
    node = nodes[fid]
    branch = "`-- " if last else "|-- "
    next_prefix = prefix + ("    " if last else "|   ")
    author = node.get("author") or "[deleted]"
    score = score_text(node.get("score", 0))
    created = node.get("created_iso", "")
    op = " OP" if node.get("is_submitter") else ""
    head = f"{author}{op} | {score} | {created}"

    append_wrapped(lines, head, prefix + branch, next_prefix, width)

    body = clean_text(node.get("body"))
    if body:
        append_wrapped(lines, body, next_prefix, next_prefix, width)

    kids = children.get(fid, [])
    for i, child in enumerate(kids):
        render_comment(lines, nodes, children, child, next_prefix, i == len(kids) - 1, width)


def render_record(record, width):
    post = record["post"]
    lines = []
    rule = "=" * width
    thin = "-" * width

    lines.append(rule)
    append_field(lines, "TITLE", post.get("title", ""), width)
    lines.append(thin)
    lines.append("LINK".ljust(10) + post.get("permalink", ""))
    append_field(lines, "SCORE", str(post.get("score", 0)), width)
    append_field(lines, "COMMENTS", str(post.get("num_comments", 0)), width)
    append_field(lines, "CREATED", post.get("created_iso", ""), width)

    body = clean_text(post.get("selftext"))
    lines.append("")
    lines.append("BODY")
    lines.append(thin)
    if body:
        append_wrapped(lines, body, "", "", width)
    else:
        lines.append("(empty)")

    nodes, children, roots = build_tree(record)
    lines.append("")
    lines.append("COMMENTS")
    lines.append(thin)
    for i, fid in enumerate(roots):
        if i:
            lines.append("")
        render_comment(lines, nodes, children, fid, "", i == len(roots) - 1, width)

    return "\n".join(lines)


def find_record(records, query):
    query = query.lower()
    for record in records:
        title = record["post"].get("title", "").lower()
        if query in title:
            return record
    raise SystemExit("not found: " + query)


def main():
    records = read_records(sys.argv[1])
    record = find_record(records, sys.argv[2])
    print(render_record(record, terminal_width()))


if __name__ == "__main__":
    main()
