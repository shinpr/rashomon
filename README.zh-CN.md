<p align="center">
  <img src="assets/rashomon-banner.jpg" width="600" alt="Rashomon">
</p>

<p align="center">
  <a href="https://claude.ai/code"><img src="https://img.shields.io/badge/Claude%20Code-Plugin-purple" alt="Claude Code"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="License"></a>
</p>

<p align="center"><a href="README.md">English</a> | 简体中文</p>

**发布 Skill 之前，先确认它是否真的改善了 Agent 的行为。**

能力越强的模型，越能把一条糟糕的指令执行得丝毫不差。不必要的关卡会变成无谓的停顿，僵化的流程会制造额外工作，围绕旧模型局限写下的规则也可能反过来束缚新模型。

有时候，不使用 Skill，Agent 反而表现得更好。

Rashomon 就是用来验证这种可能性的。它让基线版本和修改后的版本分别执行同一个任务，然后在不知道各项结果来自哪个版本的情况下进行比较。对于 Skill，最终会给出 `ship`、`revise` 或 `reject` 建议。

想直接试用？[跳到安装步骤](#安装)。

## 为什么现在更需要它

Skill 和提示词会直接改变 Agent 的实际执行方式。随着模型能力提升，为弥补旧模型局限而写下的指令，可能已经多余，甚至会产生反效果。

在一个实际工作流中，生成的任务带有一条硬性约束：`Do not improvise a workaround`。尽管最小的有效改动仍然完全在任务范围内，执行器还是停止了执行并上报。随后，编排器不得不为剩余 13 个任务逐一补上纠偏说明。

这条约束本身就是 LLM 在遵循 Rashomon 自带的提示词优化指南（`prompt-optimization`）时生成的。后续审查仍使用同一套指南，但这一次有了实际失败记录作为证据，因此能够确认问题就出在这条约束上。当时并未使用成对执行评估。

修复方式不是再加一条一刀切的规则。现在，自动生成的约束必须以明确的权威来源为依据，并为最小可行方案留出空间。参见[对应的修改](https://github.com/shinpr/claude-code-workflows/commit/4043a08)以及[对这一设计问题的完整讨论](https://www.norsica.jp/blog/when-better-models-make-old-agent-workflows-worse)。

指令审查可以发现文本中可见的问题，也能在失败发生后帮助定位原因。Rashomon 将指令审查和成对执行得到的证据结合起来，回答仅靠审查无法确定的问题：这条指令在发布前，是否真的改善了 Agent 的行为？

## Rashomon 评估什么

| 评估对象 | 对比方式 | 得到的结论 |
|----------|----------|------------|
| 新 Skill | 不使用 Skill vs. 使用 Skill | 是否应该发布这个 Skill |
| 更新后的 Skill | 旧版本 vs. 修改后的版本 | 这次修改是否带来改进 |
| 提示词 | 原提示词 vs. 优化后的提示词 | 优化是否真正改善了执行质量 |

Rashomon 也可能得出“原提示词已经足够”的结论。改写并不会被默认视为改进。

## 证据如何产生

比较只关注可观察的结果，包括正确性、完整性、约束处理，以及多次测试中反复出现的行为差异。

1. **分析改动。** 检查 Skill 或提示词中具体的指令问题。
2. **隔离执行。** 两个版本从同一个仓库状态出发，分别在独立的 Git worktree 中运行。
3. **进行成对测试。** 多轮比较可以避免一次偶然的好结果左右结论。
4. **盲评结果。** 评估器先判断输出质量，之后才会知道每个结果来自哪个版本。
5. **给出建议。** Skill 报告会返回 `ship`、`revise` 或 `reject`；提示词报告会返回 `Use optimized`、`Original sufficient`、`Needs refinement` 或 `Collect more evidence`。

### 成本与限制

如果分析认为原提示词已经足够，提示词评估会在成对执行前结束。否则，比较过程会运行真实的开发任务：

- 收集 3 组有效配对，需要执行 6 次任务。
- 遇到无效配对时会重试，最多尝试 5 组配对，也就是最多执行 10 次任务。

Skill 评估采用相同的配对上限，另外还会进行质量检查和触发检查。以上数字只计算成对比较中的任务执行；总 token 消耗和耗时还取决于任务本身及其他分析步骤。

多轮盲评有助于区分稳定出现的行为差异和一次性波动，但不代表统计显著性，也不能证明因果关系。少于 2 组有效配对时，结果会标记为 `inconclusive`。

### 报告格式示例

下例保留实际报告使用的英文字段和判定值。

```text
Skill Quality: Grade A
- Project-specific rules are encoded clearly with no critical issues

Trigger Check: pass

Execution Effectiveness:
- Winner: with-skill
- Assessment: repeatable structural improvement across valid pairs
- Key difference: retry constraints and three-stage catch ordering were applied
  consistently across trials

Recommendation: ship
```

Grade A 表示可以直接使用；Grade B 表示可以接受，但仍有改进项；Grade C 表示使用前必须修改。

## 安装

Rashomon 是一个 [Claude Code](https://claude.ai/code) 插件。

```bash
# 启动 Claude Code
claude

# 添加插件市场
/plugin marketplace add shinpr/rashomon

# 安装 Rashomon
/plugin install rashomon@rashomon
```

安装完成后，请重启 Claude Code。

## 使用方法

### 创建并评估 Skill

```text
/recipe-eval-skill create
```

Rashomon 会收集 Skill 的用途、领域知识、项目专属规则和触发语句，然后创建 Skill、审查内容质量，并比较使用和不使用该 Skill 时的 Agent 行为。

### 更新并评估 Skill

```text
/recipe-eval-skill <skill-name> <修改要求>
```

例如：

```text
/recipe-eval-skill api-error-handling 调整 Skill 的适用范围
```

Rashomon 会直接比较当前版本和修改后的版本。

### 评估提示词

```text
/recipe-eval-prompt 为 HTTP 429 和 503 响应添加重试处理，同时保持客户端的公共 API 不变
```

Rashomon 会分析提示词，在需要时生成优化版本，并比较原提示词和优化后提示词的执行结果。

也可以评估保存在文件中的提示词：

```text
/recipe-eval-prompt 请按照这个 Skill 生成代码：./prompts/my-skill.md
```

Rashomon 适合那些需要执行证据才能判断的场景。如果只是想一次性改写提示词而不做比较，这套评估流程通常没有必要。

## 结果如何分类

输出不同，不等于输出更好。Rashomon 会把变化分成四类：

| 分类 | 含义 | 通常如何处理 |
|------|------|--------------|
| **结构性改进（Structural）** | 正确性、完整性或执行质量有所提升 | 使用新版本 |
| **上下文补充（Context Addition）** | 某个版本包含有价值的项目专属知识 | 确认上下文准确后使用 |
| **表达变化（Expressive）** | 措辞发生变化，但结果没有实质提升 | 两个版本都可以接受 |
| **随机波动（Variance）** | 差异符合模型正常的随机变化 | 保留原版本，或继续收集证据 |

报告会检查已发现的问题是否得到解决、必要输出和约束是否得到处理，以及同样的差异是否在多组有效配对中重复出现。

<details>
<summary>评估流程详情</summary>

### Skill 评估

```text
/recipe-eval-skill
    ├── skill-creator: 创建或更新 Skill
    ├── skill-reviewer: 将内容质量评为 A、B 或 C
    ├── eval-executor: 进行成对测试
    └── skill-eval-reporter: 执行盲评
```

每组配对中，Skill 的两个版本会按顺序执行。

### 提示词评估

```text
/recipe-eval-prompt
    ├── prompt-analyzer: 分析并优化提示词
    ├── prompt-executor: 在隔离的 worktree 中成对执行
    └── report-generator: 比较结果并判断差异来源
```

每组配对中的两次提示词执行会并行进行。

### 隔离执行

每个版本都在独立的 Git worktree 中运行。一次测试产生的文件改动不会影响另一次测试，而且两个版本都从同一个仓库状态开始。

</details>

<details>
<summary>提示词和 Skill 的质量检查</summary>

Rashomon 会检查 9 类常见的指令质量问题。

| 优先级 | ID | 问题模式 | Rashomon 检查什么 |
|--------|----|----------|-------------------|
| 关键 | BP-001 | 负面指令 | 只说明不能做什么，却没有定义应该达到的状态 |
| 关键 | BP-002 | 模糊指令 | 影响结果的选择存在多种合理解释 |
| 关键 | BP-003 | 缺少输出格式 | 下游使用者需要稳定结构，但提示词没有定义 |
| 关键 | BP-009 | 不受约束地增加工作量 | 指令制造了结果并不需要的额外工作 |
| 高影响 | BP-004 | 缺少结构 | 重要指令淹没在背景信息中，难以辨认 |
| 高影响 | BP-005 | 上下文不足或过多 | 模型不得不猜测，或者相关事实被无关细节掩盖 |
| 高影响 | BP-006 | 流程控制不足或过多 | 缺少必要边界，或者对可逆选择规定得过细 |
| 增强项 | BP-007 | 不必要或带偏向的示例 | 示例占用上下文，或让模型过度依赖偶然细节 |
| 增强项 | BP-008 | 缺少不确定性处理 | 输入未知时，没有规定下一步如何处理 |

</details>

<details>
<summary>项目知识库</summary>

Rashomon 可以把项目专属的发现保存在：

```text
.claude/.rashomon/prompt-knowledge.yaml
```

知识库会：

- 在文件存在时自动启用；
- 只保存项目专属模式，而不是通用建议；
- 为后续分析提供参考，并可根据比较结果更新；
- 最多保留 20 条记录，超出后优先删除置信度最低的记录。

记录不会仅仅因为存在时间较长就被删除。经过反复验证的稳定模式可能一直有价值。

</details>

<details>
<summary>故障排查</summary>

### 残留的 worktree

如果 Rashomon 意外退出，可能会留下临时 worktree：

```bash
rm -rf ${TMPDIR:-/tmp}/worktree-rashomon-*
```

### 超时问题

提示词执行默认超时 5 分钟。如果任务需要更多时间，请在请求中明确说明，最长可放宽至 30 分钟：

```text
/recipe-eval-prompt 这是一个复杂任务，可能需要较长时间。
```

Skill 评估器为每个版本的单次执行设置 10 分钟超时。这些数字只是单次执行的上限，并不是完整评估所需时间的预估。

### “Not a git repository” 错误

Rashomon 必须在 Git 仓库中运行。可以用以下命令初始化仓库：

```bash
git init
```

</details>

## 运行要求

- Claude Code
- Git 2.5 或更高版本
- Python 3.9 或更高版本，供 Skill 评估器使用
- 一个 Git 仓库

## 许可证

[MIT](LICENSE)
