---
name: git-workflow
description: 规范化 Git 分支管理、Conventional Commits 提交格式以及安全检查流程
triggers: ["git", "commit", "push", "branch", "pr"]
---

### Git 专业工作流与规范指南

#### 1. 提交前必检原则 (Pre-commit Checklist):
- 必须首先通过 `run_command(command="git status")` 检查工作区脏文件状态。
- 如果涉及代码修改，使用 `run_command(command="git diff")` 仔细审查变更点，杜绝误提无关文件或测试残余。
- 执行项目单元测试（如 `pytest` 或 `npm test`），确保所有单测 100% 通过方可提交。

#### 2. Conventional Commits 格式规范:
提交信息必须遵循如下标准化结构：
`<type>(<scope>): <subject>`

常用 Type 类型：
- `feat`: 新增特性或功能
- `fix`: 修复 Bug 或异常
- `refactor`: 重构代码（不改变对外行为，提升结构设计）
- `perf`: 性能优化提升
- `test`: 增加或修改单元/集成测试
- `docs`: 文档或规范更新
- `chore`: 构建配置、依赖升级等杂项

示例：
- `feat(memory): support hierarchical CLAUDE.md instruction loading`
- `fix(editor): handle CRLF newlines on Windows platform`

#### 3. 禁止事项:
- 严禁提交包含真实 API Key、`.env` 密钥的文件。
- 严禁未经用户允许执行 `git push --force`。
