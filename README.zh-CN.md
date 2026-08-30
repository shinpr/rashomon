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

## 快速开始

Rashomon 是一个 [Claude Code](https://claude.ai/code) 插件。Skill 评估需要 Python 3.9 或更高版本，以及 Git 2.5 或更高版本。

启动 Claude Code：

```bash
claude
```

添加插件市场并安装 Rashomon：

```text
/plugin marketplace add shinpr/rashomon
/plugin install rashomon@rashomon
```

在要创建 Skill 的 Git 仓库中重启 Claude Code，然后运行：

```text
/recipe-eval-skill create
```

Rashomon 会先询问几个问题，再创建 Skill，并比较 Agent 在使用和不使用该 Skill 时的表现。最终报告会给出 `ship`、`revise` 或 `reject` 建议。

## Rashomon 评估什么

| 评估对象 | 对比方式 | 结果 |
|----------|----------|------------|
| 新 Skill | 不使用 Skill vs. 使用 Skill | 是否应该发布这个 Skill |
| 更新后的 Skill | 旧版本 vs. 修改后的版本 | 这次修改是否带来改进 |
| 提示词 | 原提示词 vs. 优化后的提示词 | 优化是否真正改善了执行质量 |

Rashomon 也可能得出“原提示词已经足够”的结论。改写并不会被默认视为改进。

## 你会得到什么

报告会说明哪个版本胜出、主要差异是什么，以及这些差异是否在多轮测试中稳定出现。

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

Grade A 表示 Skill 可以直接使用；Grade B 表示可以使用，但仍有改进项；Grade C 表示需要修改。

## 工作原理

比较只关注可观察的结果，包括正确性、完整性、约束处理，以及多次测试中反复出现的行为差异。

1. **分析改动。** 检查 Skill 或提示词中具体的指令问题。
2. **隔离执行。** 两个版本从同一个仓库状态出发，分别在独立的 Git worktree 中运行。
3. **进行配对测试。** 多轮比较可以避免一次偶然的好结果左右结论。
4. **进行盲评。** 先判断输出质量，之后才揭晓每个结果来自哪个版本。
5. **给出建议。** Skill 报告会返回 `ship`、`revise` 或 `reject`；提示词报告会返回 `Use optimized`、`Original sufficient`、`Needs refinement` 或 `Collect more evidence`。

## 使用方法

### 创建并评估 Skill

```text
/recipe-eval-skill create
```

Rashomon 会收集 Skill 的用途、领域知识、项目特有的规则和触发短语，然后创建 Skill、审查内容质量，并比较使用和不使用该 Skill 时的 Agent 行为。

### 更新并评估 Skill

```text
/recipe-eval-skill <skill-name> <修改要求>
```

例如：

```text
/recipe-eval-skill api-error-handling 调整 Skill 的适用范围
```

Rashomon 会比较当前版本和修改后的版本。

### 评估提示词

```text
/recipe-eval-prompt 为 HTTP 429 和 503 响应添加重试处理，同时保持客户端的公共 API 不变
```

Rashomon 会分析提示词，在需要时生成优化版本，并比较原提示词和优化后提示词的执行结果。经过验证、适用于当前项目的结论还可以为后续的提示词评估提供参考。

也可以评估保存在文件中的提示词：

```text
/recipe-eval-prompt 请按照这个 Skill 生成代码：./prompts/my-skill.md
```

Rashomon 适合那些需要通过实际执行来验证效果的场景。如果只是想一次性改写提示词而不做比较，这套评估流程通常没有必要。

## 结果如何分类

输出不同，不等于输出更好。Rashomon 会把变化分成四类：

| 分类 | 含义 | 通常如何处理 |
|------|------|--------------|
| **结构性改进（Structural）** | 正确性、完整性或执行质量有所提升 | 使用新版本 |
| **上下文补充（Context Addition）** | 某个版本包含当前项目特有的知识 | 确认上下文准确后使用 |
| **表达变化（Expressive）** | 措辞发生变化，但结果没有实质提升 | 两个版本都可以接受 |
| **随机波动（Variance）** | 差异符合模型正常的随机变化 | 保留原版本，或继续收集证据 |

报告会检查已发现的问题是否得到解决、必要输出和约束是否得到处理，以及同样的差异是否在多组有效配对中重复出现。

文章 [When Better Models Make Old Agent Workflows Worse](https://www.norsica.jp/blog/when-better-models-make-old-agent-workflows-worse) 分析了一个真实案例：为旧模型设计的防护措施，后来反而成了问题本身。

## 运行要求

- Claude Code
- Git 2.5 或更高版本
- Python 3.9 或更高版本，供 Skill 评估器使用
- 一个 Git 仓库

## 许可证

[MIT](LICENSE)
