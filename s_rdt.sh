set -e

. .venv/bin/activate

python scrape_reddit.py --subreddit codex --hours 24 --out codex_last24h.jsonl
python scrape_reddit.py --subreddit ClaudeCode --hours 24 --out claudecode_last24h.jsonl
