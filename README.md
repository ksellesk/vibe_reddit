# reddit-exp2

这个仓库保留两部分：

- Reddit 抓取脚本
- repo 内置 Codex skill：`.codex/skills/reddit-last24h-compare`

主要文件：

- `scrape_reddit.py`：抓取 subreddit 最近若干小时的帖子和评论，输出 `jsonl`
- `pretty_read.py`：把抓到的 `jsonl` 读成更好看的终端视图
- `deepseek_client.py`：`pretty_read.py` 里用到的翻译客户端
- `requirements.txt`：当前依赖 `praw` 和 `requests`
- `.codex/skills/reddit-last24h-compare/`：用于比较两个 Reddit 24h 快照的 skill

准备：

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
export REDDIT_CLIENT_ID=...
export REDDIT_CLIENT_SECRET=...
export REDDIT_USER_AGENT=...
```

如果要用 `pretty_read.py` 的翻译功能，再设置：

```bash
export DEEPSEEK_API_KEY=...
```

抓取示例：

```bash
python scrape_reddit.py --subreddit ClaudeCode --hours 24 --out claudecode_last24h.jsonl
python scrape_reddit.py --subreddit codex --hours 24 --out codex_last24h.jsonl
sh s_rdt.sh
```

在 Codex 里使用这个 skill：

1. 在这个仓库目录里启动 Codex
2. 重启一次 Codex，让 repo 里的 `.codex/skills` 被重新加载
3. 直接输入 `$reddit-last24h-compare`

如果你想装成用户全局 skill：

```bash
mkdir -p ~/.codex/skills
cp -R .codex/skills/reddit-last24h-compare ~/.codex/skills/
```

当前 `.gitignore` 默认不跟踪生成出来的 `jsonl`、`jsons/` 和 `codex_src4/`。
