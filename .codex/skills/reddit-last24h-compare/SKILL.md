---
name: reddit-last24h-compare
description: 分析并比较一个或多个 Reddit 24 小时 `jsonl` 快照。每一行通常包含一个 `post` 对象和一个 `comments` 数组。适用于这类问题：两个 Reddit 板块的人在讨论什么、各自的主话题是什么、哪些帖子最活跃、一个板块有没有提到另一个工具或社区、两份数据在语气、关注点与 cross-mentions 上有什么差异。
---

# Reddit Last24h Compare

先看全量标题，再用正文与评论确认模式。尽量给出有计数支撑的判断，不要凭零散样本下结论。

## 预期结构

默认每一行都是一个 JSON 对象，至少包含：

- `post`: title, selftext, score, num_comments, permalink, timestamps
- `comments`: array of comment objects with `body`, `score`, timestamps

如果结构不同，先抽样确认字段，再调整读取方式。

## 工作流

### 1. 先确认文件与记录形态

先用只读命令。

- Locate candidate files with `rg --files`
- Inspect a few lines with `python3` or `sed`
- Confirm whether each line is a packed `post + comments` record

### 2. 先广读，再深读

先看全量帖子标题，不要只看前几条样本。

- Count posts with `wc -l`
- Extract all titles
- Sort by `num_comments` and `score`
- Scan for repeated terms or repeated problem types

先用标题识别主话题；遇到含混之处，再回到 `selftext` 与评论核实。

### 3. 归并主题

宁可用少数几个厚实主题，也不要切成一串单薄标签。

常见主题包括：

- 模型表现、退化、回归
- 定价、限额、quota、plan
- workflow、agents、subagents、MCP、hooks
- 宕机、bug、性能问题
- 与另一工具的比较
- showcase 帖、工具发布、经验贴

每个主题尽量用至少两个帖子标题落锚。

### 4. 单独检查互相提及

如果用户问“一个板块有没有提到另一个工具或社区”，分三层搜：

- post titles
- post bodies
- comment bodies

分开报告：

- 有多少帖子直接提到
- 有多少评论提到
- 这些提及分别扮演什么角色

常见角色有：

- 比较对象
- 宕机时的备胎
- 混合工作流的一环
- bridge、integration、MCP handoff

### 5. 分清“热闹”和“认同”

同时看 `num_comments` 与 `score`。

- `num_comments` 更像“引发讨论”
- `score` 更像“获得认同”

二者若明显分叉，要直接说出来。

### 6. 分层作答

默认回答结构：

1. 一段总括
2. 每个文件或社区各一段
3. 一段交叉比较
4. 如有需要，再补一段带计数的互相提及说明

如果用户问得很窄，例如“板块 A 有没有提到工具 B”，先直接答“有”或“没有”，再补计数和语境。

## 工作规则

- 优先用 `python3` 做轻量结构化提取
- 能便宜算出来的地方，优先给精确计数
- 不要只看头几条就下判断
- 不要大段引用原帖原文
- 关键词分组若只是近似推断，要明说
- 除非用户要求去重，否则重复标题或重复帖也算作数据的一部分

## 常用模式

按评论数和分数提取高热帖子：

```bash
python3 - <<'PY'
import json
rows = []
for line in open('file.jsonl'):
    obj = json.loads(line)
    p = obj['post']
    rows.append((p.get('num_comments', 0), p.get('score', 0), p.get('title', '')))
for comments, score, title in sorted(rows, reverse=True)[:20]:
    print(comments, score, title)
PY
```

统计标题、正文、评论里的直接提及：

```bash
python3 - <<'PY'
import json, re
term = re.compile(r'\\bcodex\\b', re.I)
post_hits = 0
comment_hits = 0
for line in open('file.jsonl'):
    obj = json.loads(line)
    p = obj['post']
    if term.search((p.get('title', '') or '') + '\n' + (p.get('selftext', '') or '')):
        post_hits += 1
    for c in obj.get('comments', []):
        if term.search(c.get('body', '') or ''):
            comment_hits += 1
print(post_hits, comment_hits)
PY
```

## 输出风格

回答要短、准、带比较感。优先用这种句式：

- “A 板块主要在讨论 X、Y、Z。”
- “B 板块在宕机和工具发布上更嘈杂。”
- “工具 B 更多是作为备胎出现，而不是主角。”
- “这是根据全量标题加高互动帖子作出的推断。”
