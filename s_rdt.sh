set -e

#python3 scrape_reddit.py --subreddit ClaudeAI --hours 16 --out claudeai_last16h.jsonl


python3 scrape_reddit.py --subreddit codex --hours 24 --out codex_last24h.jsonl


python3 scrape_reddit.py --subreddit ClaudeCode --hours 24 --out claudecode_last24h.jsonl


#python3 scrape_reddit.py --subreddit browsers --hours 240 --out browsers_last240h.jsonl


#python3 scrape_reddit.py --subreddit ChatGPTAtlas --hours 96 --out  ChatGPTAtlas_last96.jsonl
