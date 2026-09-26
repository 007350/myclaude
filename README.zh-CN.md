# MyClaude：本地终端 AI 编程智能体（纯 Python）

[English](README.md) | **简体中文**

[![Tests](https://github.com/007350/myclaude/actions/workflows/tests.yml/badge.svg)](https://github.com/007350/myclaude/actions/workflows/tests.yml)
[![GitHub stars](https://img.shields.io/github/stars/007350/myclaude?style=social)](https://github.com/007350/myclaude/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

一个深度受 **Claude Code** 启发、基于原生 **Python** 打造的高性能本地终端自主编程
Agent，代码体量小、依赖轻量、可端到端通读与魔改。它通过完整的 ReAct 循环
（思考 → 工具调用 → 执行 → 验证），自主完成代码检索、切片阅读、高容错精准替换、
终端测试执行以及多轮 Bug 自动自愈。

除编程能力外，项目还内置了**双级上下文压缩**、**影子快照原子回退 (`/undo`)**、
**`CLAUDE.md` 规范记忆**、**渐进式技能库 (Skills)**、**MCP 插件自进化**与
**双轨伴生协同终端 (Sidecar)** 等生产级架构特性。

---

## 🌟 核心特性全景

### 1. 核心工具集与工业级容错编辑
- **`edit_file`（五级容错代码替换引擎）**：不同于容易漏代码且极度消耗 Token 的全量
  重写，本引擎采用多级回退匹配（精确字符 → CRLF/LF 换行符归一 → 行尾空白容错 →
  缩进偏差自适应对齐 → **88% 模糊相似匹配**），改代码极度稳定。
- **`read_file`**：支持按起止行号切片查看，防止一次性读取超长文件造成 Token 爆炸。
- **`write_file`**：创建与全量覆写文件，写入前自动接入快照保护网。
- **`code_search` & `find_files`**：类似 ripgrep 的极速检索，内置过滤 `.git`、
  `node_modules`、`venv` 等几十种目录及二进制文件。
- **`run_command`**：跨平台（Windows PowerShell / Linux / macOS bash）执行，具备
  超时保护、超大输出首尾截断防爆以及实时流式日志捕获。

### 2. ⏪ 原子版本安全网与秒级回滚 (`/undo`)
- **写入前影子快照 (Shadow Snapshot)**：任何文件被写入或修改前，自动抓取磁盘原始
  状态，并将每一步工具操作提交为原子 Checkpoint。
- **秒级撤回与认知注入**：输入 `/undo` 即可瞬间恢复，并自动清理新增文件；同时将
  撤销事件注入 Agent 记忆，防止死循环。

### 3. 🗜️ 双级渐进式上下文压缩引擎
- **Tier 1 软裁剪**：触碰软阈值时自动折叠早期杂乱工具输出（长日志、超长读取），
  立省 50%+ 上下文。
- **Tier 2 硬压缩**：逼近窗口极限时调用大模型深度提取【已达成 / 进行中 / 未决目标】
  三要素微摘要，并保留 System Prompt 静态缓存前缀与最近活跃上下文。
- **KV Cache 优化**：工具 Schema 严格字典序排列，控制台实时展示 Prompt Caching
  命中百分比。

### 4. 🧠 项目长期规范与环境记忆 (`CLAUDE.md`)
- **层级化规则装配**：自动探测并合并全局规范 (`~/.claude/CLAUDE.md`) 与项目专属
  规范 (`./CLAUDE.md`)。
- **一键交互式初始化 (`/init`)**：自动识别技术栈（Python/Poetry/uv、Node.js/npm/
  pnpm/yarn/bun、Rust/Cargo、Go 等）与构建测试命令，生成规范草稿供微调。

### 5. 🤹 渐进式披露技能库 (Skills Engine)
- **按需加载**：系统提示词初始仅含极简技能目录（Catalog，耗费 < 50 Token）。
- **自主/显式激活**：Agent 可通过 `activate_skill` 自主载入，或由用户 `/skill <name>`
  强制注入详细执行指南与配套脚本（如 `skills/git-workflow/SKILL.md`）。

### 6. 🔌 官方 MCP 插件协议与能力自进化
- **标准 MCP 支持**：原生基于 stdio 协议挂载外部 MCP 服务（浏览器自动化、数据库、
  API 查询等）。
- **`create_python_mcp_server`**：Agent 发现缺少能力时，可自主编写 FastMCP 代码创建
  服务并**当前会话零重启热加载**。

### 7. 🛰️ 双轨伴生协同监控终端 (`sidecar.py`)
- **双轨并行副驾驶**：在主终端旁另起窗口运行 `python sidecar.py`。
- **实时解说与带外干预**：实时拉取主 Agent 执行黑板、展示最新日志流，支持侧边栏
  下发实时战略指令（`/steer`）纠偏，或紧急中断（`/interrupt`）卡死的子进程命令。

### 8. ⚡ YOLO 极速模式与权限守卫
- **安全模式（默认）**：拦截高危指令（破坏性删除、格式化命令），支持
  `[y] 单次允许 / [a] 始终允许 (YOLO) / [n] 拒绝`。
- **YOLO 模式**：`/yolo` 一键切换，极速全自动执行。

---

## 🚀 快速上手

```bash
git clone https://github.com/007350/myclaude.git
cd myclaude
pip install -r requirements.txt
python main.py
```

> **首次运行引导**：若未检测到 `.env`，程序会自动弹出交互式配置向导，支持一键配置
> **DeepSeek（推荐）**、**OpenRouter（Claude 3.5/3.7、GPT-4o）**、**本地 Ollama**
> 或其他兼容 OpenAI 协议的模型。

亦可复制 `.env.example` 为 `.env` 手动填入：

```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
MAX_STEPS=30
```

---

## 🎮 终端快捷交互命令清单

在 `👉 myclaude >` 提示符下可随时键入：

| 快捷命令 | 说明 |
| :--- | :--- |
| `/undo` | **秒级原子回退**：还原最近一步的所有修改/创建文件，并同步认知 |
| `/undo list` | 查看当前 Undo 栈内的可回滚检查点清单 |
| `/init` | **代码库指纹扫描**：探测技术栈并交互式生成/微调 `CLAUDE.md` |
| `/skills` | 查看已发现的所有全局与项目专业技能清单 |
| `/skill <name>` | 手动显式激活专业技能（如 `/skill git-workflow`） |
| `/compact` | 手动触发上下文深度压缩（保留 KV Cache 静态前缀） |
| `/yolo` 或 `/mode` | 在 YOLO 极速模式与安全拦截模式间切换 |
| `/mcp` 或 `/plugins` | 查看已连接的 MCP 服务及其挂载工具 |
| `/clear` 或 `/reset` | 清空上下文并重新装载 `CLAUDE.md` 与技能库 |
| `/model` 或 `/config` | 查看当前模型、Base URL 与工作区路径 |
| `/help` | 查看详细帮助 |
| `/exit` 或 `/quit` | 优雅关闭 MCP 进程池并退出 |

---

## 🛰️ 启动双轨伴生协同终端 (Sidecar)

```bash
python sidecar.py
```

- **实时监控**：观察主 Agent 状态跃迁、当前工具、耗时与最近日志。
- **带外干预**：`/steer <指导说明>` 将指令注入主 Agent 下一轮思考。
- **紧急打断**：`/interrupt` 立即终止卡死的终端命令。

---

## 📂 项目代码结构

```text
myclaude/
├── main.py                     # 程序启动入口
├── sidecar.py                  # 双轨伴生协同终端（副驾驶/干预/监控）
├── requirements.txt            # 项目依赖清单
├── myclaude/                   # 核心 Python 源码包
│   ├── core/                   # 状态机、上下文压缩、记忆、技能库、快照、解析器
│   ├── mcp/                    # MCP 协议客户端与异步会话管理
│   ├── security/               # 权限守卫与模式拦截 (Normal/Strict/YOLO)
│   ├── tools/                  # 容错编辑、命令行、文件操作、检索、MCP、技能
│   ├── ui/                     # Rich 终端渲染与 Prompt 缓存统计
│   ├── agent.py                # ReAct 推理大脑与主循环
│   ├── cli.py                  # REPL 与斜杠命令路由
│   └── config.py               # 环境配置解析与模型参数加载
├── skills/                     # 项目级扩展技能库
├── custom_mcp_servers/         # Agent 自进化生成的本地 MCP 服务
├── examples/                   # MCP 服务端示例 (FastMCP)
├── docs/                       # 交互式架构学习指南 (GitHub Pages)
└── tests/                      # 单元测试套件（33 个测试）
```

---

## 🧪 自动化测试

```bash
python -m unittest discover -s tests -v
```

CI 在 Python 3.10 / 3.11 / 3.12 / 3.13 上运行。

---

## 📚 Agent 进阶与 LangGraph 学习资源

交互式架构图谱与学习平台（涵盖 7 步 ReAct 闭环拆解、模块深度剖析、
5 大维度与 LangGraph 状态图代码对照、4 阶段学习路线打卡）：

- 🌐 **在线访问**：https://007350.github.io/myclaude/
- 📄 **源码**：[`docs/index.html`](docs/index.html)

---

## 🤝 参与贡献

欢迎提 Issue 和 PR — 详见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。如果 MyClaude
对你有帮助，点个 ⭐ 能让更多人发现它。

## 📄 许可证

[MIT](LICENSE) © 2026 zouxi
