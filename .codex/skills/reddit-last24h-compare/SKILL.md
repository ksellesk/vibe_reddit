---
name: reddit-last24h-compare
description: 自动查找并分析本地 Reddit 24 小时 `jsonl` 快照。触发后先检查当前目录是否有当天快照；若有，直接比较社区话题、热帖、评论气氛与互相提及；若无，报告已有文件时间范围并询问下一步。适用于比较 ClaudeCode、Codex 等 subreddit 最近 24 小时在讨论什么，以及继续做详细报告、热门帖精读或主题深挖。
---

# Reddit Last24h Compare

默认目标：用户输入 `$reddit-last24h-compare` 后，不要先问一堆问题。先找本地文件，确认新鲜度，满足条件就直接给一份清楚的初版报告，最后问下一步。

## 启动检查

先只读检查本地快照：

1. 用 `rg --files -g '*.jsonl'` 找候选文件。
2. 优先使用文件名包含 `last24h` 的快照。
3. 读取每个候选文件的 `fetched_at`；没有则读取帖子里的 `created_iso`。
4. 判断是否为当天快照，同时报告精确时间范围。
5. 如果当天存在 `claudecode_last24h.jsonl` 和 `codex_last24h.jsonl`，直接比较这两个文件，不要追问。
6. 如果只有一个当天快照，直接分析这个社区。
7. 如果有多个当天快照且文件名明显对应不同社区，直接比较。
8. 只有文件过旧、结构异常、或无法判断社区归属时，才向用户说明情况并询问。

常用检查：

```bash
rg --files -g '*.jsonl'
```

```bash
python3 - <<'PY'
import json
for path in ['file.jsonl']:
    created = []
    fetched = []
    for line in open(path):
        obj = json.loads(line)
        fetched.append(obj.get('fetched_at'))
        created.append(obj['post'].get('created_iso'))
    print(path)
    print('created', min(created), '->', max(created))
    print('fetched', min(fetched), '->', max(fetched))
PY
```

## 读取顺序

先广读，再深读：

1. 确认每行是否是 `post + comments + fetched_at`。
2. 统计帖子数、评论数、总分、时间范围。
3. 抽取全量标题，不要只看前几条。
4. 分别按 `num_comments` 和 `score` 排热帖。
5. 用标题归纳主题，再用正文和高分评论确认。
6. 需要互提时，分标题、正文、评论三层统计。

`num_comments` 更像“引发讨论”，`score` 更像“获得认同”。二者分叉时要说出来。

## 默认初版报告

如果当天快照可用，首轮直接输出一份报告。报告要清楚，不要太短，也不要进入极详细模式。

默认结构：

1. `快照概况`：文件、帖子数、评论数、时间范围。
2. `总览`：一句话比较两个社区。
3. `社区 A`：3-5 个主话题，每个话题用代表帖落锚。
4. `社区 B`：3-5 个主话题，每个话题用代表帖落锚。
5. `交叉比较`：两边特点、相同点、差异和互相提及情况。
6. `值得继续看的帖子`：每边列 3-5 个，给标题、评论数、分数、为什么值得看。
7. `下一步`：给用户三个常用选择。

下一步固定给这三类：

1. `详细分析`：做一份详细到极致的报告，包含主题分组、代表帖、评论倾向、互相提及和证据计数。
2. `热门帖精读`：选两边最热门或最代表性的帖子，给标题、正文、代表评论、中文翻译、链接和点评，格式要漂亮。
3. `主题深挖`：用户指定一个主题，只围绕该主题深入研究。

## 主题归并

宁可用少数几个厚实主题，不要切成一串单薄标签。

主题从当天数据里归纳出来。每个主题尽量至少用两个帖子标题支撑。关键词分组若只是近似推断，要明说。

## 互相提及

如果用户问“一个板块有没有提到另一个工具或社区”，分三层搜：

- post titles
- post bodies
- comment bodies

分开报告：

- 有多少标题或正文直接提到
- 有多少评论提到
- 分布在多少帖子里
- 这些提及分别扮演什么角色

## 后续模式

### 详细分析

用户选择详细分析时，扩大证据密度：

- 给更完整的主题表
- 列每个主题的代表帖
- 比较 `num_comments` 与 `score`
- 抽取高分评论确认社区态度
- 单独统计互相提及
- 明确哪些判断来自标题，哪些来自正文和评论

### 热门帖精读

用户选择“热门帖精读”，或说“两边各 N 帖”“热门帖”“精读”时，按帖子输出。

默认每帖取高分前 5 条评论；用户要求 10 条就取 10 条。若评论不足，明确说明。

默认结构：

- `**[社区] 帖子标题**`
- `链接：...`
- `热度：X 评论，Y 分`
- `标题翻译：...`
- `正文翻译：...`
- `评论 1：...`
- `评论 2：...`
- `评论 3：...`
- `评论 4：...`
- `评论 5：...`
- `点评：...`

翻译要求：

- 保留原帖语气：抱怨、讽刺、争论、建议、兴奋都不要洗平。
- 长正文可忠实压缩翻译，但不能漏掉价格、时间、模型名、工具名、quota、token、plan 等关键信息。
- 如果用户明确要求“原文+翻译”，每帖按 `标题原文`、`标题翻译`、`正文原文`、`正文翻译`、`评论原文`、`评论翻译` 输出。
- 如果用户说“继续”，沿用上一条的帖子范围、格式和评论数量。

### 主题深挖

用户指定主题时，只围绕该主题：

- 搜标题、正文、评论三层
- 给命中计数
- 列最高互动帖子
- 提炼主要立场
- 给代表评论翻译或解释
- 最后说明该主题在相关快照中的呈现；如果多个社区都有讨论，再比较差异

## 常用提取

按评论数和分数提取热帖：

```bash
python3 - <<'PY'
import json
rows = []
for line in open('file.jsonl'):
    obj = json.loads(line)
    p = obj['post']
    rows.append((p.get('num_comments', 0), p.get('score', 0), p.get('title', ''), p.get('permalink', '')))
for comments, score, title, link in sorted(rows, reverse=True)[:20]:
    print(comments, score, title, link)
PY
```

统计直接提及：

```bash
python3 - <<'PY'
import json
import re
term = re.compile(r'\bcodex\b', re.I)
post_hits = 0
comment_hits = 0
comment_posts = set()
for i, line in enumerate(open('file.jsonl'), 1):
    obj = json.loads(line)
    p = obj['post']
    if term.search((p.get('title', '') or '') + '\n' + (p.get('selftext', '') or '')):
        post_hits += 1
    for c in obj.get('comments', []):
        if term.search(c.get('body', '') or ''):
            comment_hits += 1
            comment_posts.add(i)
print(post_hits, comment_hits, len(comment_posts))
PY
```
