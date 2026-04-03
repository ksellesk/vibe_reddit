#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scrape the last N hours of submissions from a subreddit using Reddit's official API (PRAW),
expanding all comments ("MoreComments") and writing JSON Lines output.

Environment variables required:
- REDDIT_CLIENT_ID
- REDDIT_CLIENT_SECRET

Optional:
- REDDIT_USER_AGENT (if not provided, a default UA string is used)

Usage examples:
  python scrape_reddit.py --subreddit ClaudeCode --hours 10 --out claudecode_last10h.jsonl
"""
import os
import sys
import time
import json
import argparse
import datetime as dt
from typing import Any, Dict, List

import praw
import prawcore


def utc_iso(ts: float) -> str:
    return dt.datetime.utcfromtimestamp(ts).isoformat() + "Z"


def submission_to_dict(s) -> Dict[str, Any]:
    return {
        "id": s.id,
        "fullname": f"t3_{s.id}",
        "title": s.title,
        "author": getattr(s.author, "name", None),
        "created_utc": float(s.created_utc),
        "created_iso": utc_iso(float(s.created_utc)),
        "permalink": f"https://www.reddit.com{s.permalink}",
        "url": s.url,
        "selftext": getattr(s, "selftext", "") or "",
        "num_comments": int(getattr(s, "num_comments", 0) or 0),
        "score": int(getattr(s, "score", 0) or 0),
        "over_18": bool(getattr(s, "over_18", False)),
        "stickied": bool(getattr(s, "stickied", False)),
        "locked": bool(getattr(s, "locked", False)),
        "distinguished": getattr(s, "distinguished", None),
        "edited": getattr(s, "edited", False),
    }


def comment_to_dict(c) -> Dict[str, Any]:
    return {
        "id": c.id,
        "fullname": f"t1_{c.id}",
        "parent_id": c.parent_id,
        "link_id": c.link_id,
        "author": getattr(c.author, "name", None),
        "body": getattr(c, "body", "") or "",
        "score": int(getattr(c, "score", 0) or 0),
        "created_utc": float(c.created_utc),
        "created_iso": utc_iso(float(c.created_utc)),
        "depth": int(getattr(c, "depth", 0) or 0),
        "is_submitter": bool(getattr(c, "is_submitter", False)),
        "distinguished": getattr(c, "distinguished", None),
        "edited": getattr(c, "edited", False),
        "removed_by_category": getattr(c, "removed_by_category", None),
    }


def expand_all_comments(submission) -> None:
    """Expand all MoreComments with retries/backoff."""
    backoff = 5.0
    while True:
        try:
            submission.comments.replace_more(limit=None)
            return
        except prawcore.exceptions.TooManyRequests as e:
            # Respect the server's suggested sleep_time if present.
            sleep_for = getattr(e, "sleep_time", None)
            if not sleep_for:
                sleep_for = backoff
                backoff = min(backoff * 2, 300.0)
            print(f"[rate-limit] Sleeping {sleep_for:.1f}s...", file=sys.stderr)
            time.sleep(sleep_for)
        except (prawcore.exceptions.RequestException, prawcore.exceptions.ServerError) as e:
            print(f"[retryable] {e} -> backoff {backoff:.1f}s", file=sys.stderr)
            time.sleep(backoff)
            backoff = min(backoff * 2, 300.0)


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description="Fetch recent subreddit posts and all comments via PRAW")
    #ap.add_argument("--subreddit", default="ClaudeAI", help="Subreddit name (without r/)")
    ap.add_argument("--subreddit", default="ClaudeCode", help="Subreddit name (without r/)")
    ap.add_argument("--hours", type=float, default=10.0, help="Look back window in hours")
    ap.add_argument("--out", default="claudecode_last10h.jsonl", help="Output JSONL file path")
    ap.add_argument("--max-posts", type=int, default=1000, help="Safety cap when walking r/new")
    ap.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout per request (seconds)")
    args = ap.parse_args(argv)

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("Missing REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET in environment.", file=sys.stderr)
        return 2

    user_agent = os.environ.get("REDDIT_USER_AGENT") or "script:claudecode-scraper:0.1 (by u/your_username)"
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
        requestor_kwargs={"timeout": args.timeout},
    )
    reddit.read_only = True

    sr = reddit.subreddit(args.subreddit)
    cutoff = time.time() - args.hours * 3600.0
    collected = 0

    start_time = time.time()
    with open(args.out, "w", encoding="utf-8") as fout:
        for idx, s in enumerate(sr.new(limit=args.max_posts), start=1):
            # PRAW ensures created_utc; new() is newest-first, so we can break early.
            if float(s.created_utc) < cutoff:
                print(f"Reached posts older than {args.hours}h at index {idx}. Stopping.", file=sys.stderr)
                break

            print(f"[{idx}] {utc_iso(float(s.created_utc))} - {s.id} - {s.title[:80]}", file=sys.stderr)

            # Expand comments with robust retries
            expand_all_comments(s)
            comments_flat = [comment_to_dict(c) for c in s.comments.list()]

            record = {
                "post": submission_to_dict(s),
                "comments": comments_flat,
                "fetched_at": utc_iso(time.time()),
            }
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")
            collected += 1

    elapsed = time.time() - start_time
    print(f"Collected {collected} posts into {args.out} in {elapsed:.1f}s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

