# Repository Guidelines

- 任何事情都从最简洁开始。只做必要的事，不要过度发挥。
- 用优雅流畅的中文和我交流；如果不知道什么是优雅流畅，就用普鲁斯特式的；你的中文水平是诺贝尔文学奖水平。
- 对于读类型的操作，你可以直接进行，但对于写类型的，必须先询问。若用户明确要求迭代处理，则不用每次都询问。
- 如果收到了模糊不清的指令，必须先追问澄清，不要自行补全需求。
- 我会审核你写的所有代码，所以写得清楚很重要。意思是：
  1. 代码优雅，可读性是第一要求，不要写难看的代码。
  2. 高品位，区分‘高级’和‘自以为高级’。
  3. 不要随便加 try except，有时候运行出错可以让我知道输入有问题。随便加会隐藏问题。
  4. 杜绝不重要的参数判断（比如 if len(sys.argv) > 2 之类），这会增加我的审核负担。真的有必要，我会主动提出添加。
- 记住我的工作习惯，我不会直接接受你的代码，而是会审核，方便我审核有最高优先级。

# Coding Style & Naming Conventions

## 通用
- 尽量少注释，只留最必要的注释
- 函数大小适中，尤其避免太长

## Python
- Style: PEP 8, 4-space indent, `snake_case` for files/functions, `UpperCamelCase` for classes.
- import 按长短排序
- 能用 sys.argv 就不要 argparse
- 能 print 输出就不要写文件, 不要 sys.stdout.write
- 读文件单独成函数，推荐这样的写法：lines = [l.strip() for l in open(sys.argv[1]).readlines()]
- 不要使用 `fn_str(name: str) -> str` 这样的写法，太高级，我已经 old-fashion 了
- 简单场景不要用 yield。
- 我很讨厌这样的写法 result = data.get("result") or {}, 直接 result = data["result"] 或者 result = data.get("result")
