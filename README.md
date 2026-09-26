# MyClaude: 本地终端 AI 编程智能体 (Claude Code Python 增强版)

这是一个深度受 **Claude Code** 启发、基于原生 **Python** 打造的高性能本地终端自主编程 Agent。它能够在本地终端通过完整的 ReAct 循环（思考 $\to$ 工具调用 $\to$ 执行 $\to$ 验证），自主完成代码检索、切片阅读、高容错精准替换、终端测试执行以及多轮 Bug 自动自愈。

除了完整的编程能力，本项目还内置了**双级上下文压缩**、**影子快照原子回退 (/undo)**、**CLAUDE.md 规范记忆**、**渐进式技能库 (Skills)**、**MCP 插件自进化**与**双轨伴生协同终端 (Sidecar)** 等生产级架构特性。

---

## 🌟 核心特性全景

### 1. 核心工具集与工业级容错编辑
- **`edit_file` (核心五级容错代码替换引擎)**：不同于容易漏代码且极度消耗 Token 的全量文件重写，本引擎采用多级回退匹配（精确字符 $\to$ CRLF/LF 换行符归一 $\to$ 行尾空白容错 $\to$ 缩进偏差自适应对齐 $\to$ 88% 模糊相似匹配），修改代码极度稳定。
- **`read_file`**：支持指定起止行号切片查看，防止一次性读取超长文件造成 Token 爆炸。
- **`write_file`**：创建与全量覆写文件，写入前自动接入快照保护网。
- **`code_search` & `find_files`**：类似 ripgrep 的极速代码检索，内置过滤 `.git`、`node_modules`、`venv` 等几十种目录及二进制文件。
- **`run_command`**：跨平台（Windows PowerShell / Linux / macOS bash）命令行执行，具备超时保护、超大输出首尾截断防爆以及实时流式日志捕获。

### 2. ⏪ 原子版本安全网与秒级回滚 (`/undo`)
- **写入前影子快照 (Shadow Snapshot)**：在任何文件被写入或修改前，系统自动抓取磁盘原始状态，并将每一步工具操作提交为原子 Checkpoint。
- **秒级撤回与认知注入**：输入 `/undo` 即可瞬间恢复修改前状态（并自动清理新增文件）；同时将撤销事件注入 Agent 记忆，防止智能体在错误思路上死循环。

### 3. 🗜️ 双级渐进式上下文压缩引擎 (Context Compactor)
- **Tier 1 软裁剪**：当对话历史触碰软阈值时，自动将早期杂乱的工具输出（如长日志、超长文件读取）折叠首尾，立省 50%+ 上下文。
- **Tier 2 硬压缩**：逼近窗口极限时，自动调用大模型深度提取【已达成事项 / 当前工作状态 / 遗留未决目标】三要素阶段微摘要，保留 System Prompt 静态缓存前缀与最近活跃上下文。
- **KV Cache 优化**：工具 Schema 严格做字典序确定性排列，控制台实时展示 Prompt Caching 命中百分比。

### 4. 🧠 项目长期规范与环境记忆 (`CLAUDE.md`)
- **层级化规则装配**：自动探测并合并全局规范 (`~/.claude/CLAUDE.md`) 与项目专属规范 (`./CLAUDE.md`)。
- **一键交互式初始化 (`/init`)**：自动识别当前仓库的技术栈（Python/Poetry/uv、Node.js/npm/pnpm/yarn/bun、Rust/Cargo、Go 等）和构建测试命令，生成规范草稿供交互微调。

### 5. 🤹 渐进式披露技能库 (Skills Engine)
- **按需加载机制**：系统提示词初始仅包含极简技能目录（Catalog，耗费 < 50 Token）。
- **自主/显式激活**：当任务涉及专门规范时，Agent 可通过 `activate_skill` 工具自主载入，或由用户通过 `/skill <name>` 强注入详细执行指南与配套脚本（如 [skills/git-workflow/SKILL.md](file:///D:/myclaude/skills/git-workflow/SKILL.md)）。

### 6. 🔌 官方 MCP 插件协议与能力自进化 (Self-Evolution)
- **标准 MCP 支持**：原生基于 stdio 协议挂载外部 MCP 服务的工具（如浏览器自动化、数据库、API 查询等）。
- **`create_python_mcp_server`**：当 Agent 发现自身缺少某种能力时，能够自主编写 FastMCP Python 代码创建服务并**当前会话零重启热加载**！

### 7. 🛰️ 双轨伴生协同监控终端 (`sidecar.py`)
- **双轨并行副驾驶**：可在主终端旁边另起窗口运行 `python sidecar.py`。
- **实时解说与带外干预**：实时拉取主 Agent 执行黑板、展示最新日志流，支持在侧边栏下发实时战略指令（`/steer`）纠偏，或紧急中断（`/interrupt`）卡死的子进程命令。

### 8. ⚡ YOLO 极速模式与权限守卫
- **安全模式 (默认)**：智能拦截高危指令（如破坏性删除、格式化命令），支持 `[y] 单次允许 / [a] 始终允许(YOLO) / [n] 拒绝`。
- **YOLO 模式**：通过 `/yolo` 一键切换，极速全自动执行所有文件与终端操作。

---

## 📂 项目代码结构

```
D:/myclaude/
├── main.py                     # 程序启动入口
├── sidecar.py                  # 双轨伴生协同终端（副驾驶/干预/监控）
├── mcp.json                    # MCP (Model Context Protocol) 插件服务配置
├── agent_learning_guide.html   # 交互式智能体架构剖析与 LangGraph 学习平台
├── requirements.txt            # 项目依赖清单
│
├── myclaude/                   # 核心 Python 源码包
│   ├── core/                   # 🧠 Agent 核心底座
│   │   ├── state.py            # 全局共享黑板状态机与 HTTP IPC 服务
│   │   ├── context.py          # 双级上下文窗口压缩与 Token 优化管理
│   │   ├── memory.py           # CLAUDE.md 规范加载与项目生态自动探测器
│   │   ├── skills.py           # 渐进式技能库引擎 (Skills Engine)
│   │   ├── snapshot.py         # 影子快照与秒级原子回退安全网 (/undo)
│   │   └── parser.py           # 4 级容错 JSON 解析与参数别名自愈对齐
│   ├── mcp/                    # 🔌 MCP 协议集成客户端与异步会话管理
│   │   └── manager.py          # 独立事件循环与 stdio 服务进程调度
│   ├── security/               # 🛡️ 权限守卫与模式拦截 (Normal/Strict/YOLO)
│   │   └── permissions.py      # 高危命令特征检测与交互确认逻辑
│   ├── tools/                  # 🛠️ 生产级工具生态
│   │   ├── editor.py           # 五级容错代码段精准替换引擎 (edit_file)
│   │   ├── bash.py             # 命令行执行、流式截断与外部中断
│   │   ├── file_ops.py         # 切片读取 read_file、快照写入 write_file
│   │   ├── search.py           # 跨文件 code_search 与文件定位 find_files
│   │   ├── mcp_ops.py          # MCP 挂载与 FastMCP 自进化创建工具
│   │   ├── skill_ops.py        # 技能动态激活工具 (activate_skill)
│   │   └── registry.py         # 函数签名动态反射注册与 Schema 排序
│   ├── ui/                     # 🖥️ 终端渲染与 Rich 卡片流美化
│   │   └── console.py          # 控制台交互、状态面板与 Prompt 缓存统计展示
│   ├── agent.py                # ⚙️ ReAct 推理大脑与主循环驱动中枢
│   ├── cli.py                  # 🎮 REPL 交互命令行与斜杠命令路由系统
│   └── config.py               # ⚙️ 环境配置解析与模型参数加载
│
├── skills/                     # 🤹 项目级扩展技能库
│   └── git-workflow/           # Git 规范提交与分支管理技能范例
├── custom_mcp_servers/         # 🧬 Agent 自进化生成的本地 MCP 服务存储目录
├── examples/                   # 💡 MCP 服务端示例 (FastMCP)
└── tests/                      # 🧪 单元测试套件 (包含 31 个自动化测试)
```

---

## 🚀 快速上手

### 1. 安装依赖
本项目依赖轻量、运行快速：
```bash
pip install -r requirements.txt
```

### 2. 配置与启动
进入项目根目录并运行：
```bash
python main.py
```
> **首次运行引导**：若未检测到 `.env`，程序会自动弹出交互式配置向导，支持一键配置 **DeepSeek (推荐)**、**OpenRouter (Claude 3.5/3.7, GPT-4o)**、**本地 Ollama** 或其他兼容 OpenAI 协议的模型。

亦可直接复制 `.env.example` 为 `.env` 手动填入配置：
```ini
OPENAI_API_KEY=sk-xxxx
OPENAI_BASE_URL=https://api.deepseek.com/v1
MODEL_NAME=deepseek-chat
MAX_STEPS=30
```

---

## 🎮 终端快捷交互命令清单

在 `👉 myclaude >` 提示符下可随时键入以下斜杠指令：

| 快捷命令 | 说明 |
| :--- | :--- |
| `/undo` | **秒级原子回退**：将最近一次步骤中所有修改/创建的文件还原至最初状态，并同步认知 |
| `/undo list` | 查看当前 Undo 栈内所有可回滚的历史检查点清单 |
| `/init` | **代码库指纹扫描**：自动探测技术栈并交互式生成/微调项目的 `CLAUDE.md` 规范 |
| `/skills` | 查看当前已发现的所有全局与项目专业技能（Skills）清单 |
| `/skill <name>` | 手动显式激活指定专业技能（例如 `/skill git-workflow`） |
| `/compact` | 手动触发上下文智能微摘要深度压缩（释放 80%+ 空间并保留 KV Cache 静态前缀） |
| `/yolo` 或 `/mode` | **切换执行模式**：在 YOLO 极速自动放行模式与安全拦截确认模式之间一键切换 |
| `/mcp` 或 `/plugins` | 查看当前已连接的所有 MCP 外部服务及其挂载的工具列表 |
| `/clear` 或 `/reset` | 清空当前对话上下文记忆，重新装载 `CLAUDE.md` 与技能库 |
| `/model` 或 `/config` | 查看当前正在生效的大模型、Base URL 与工作区路径 |
| `/help` | 查看详细帮助说明 |
| `/exit` 或 `/quit` | 优雅关闭 MCP 进程池并退出程序 |

---

## 🛰️ 启动双轨伴生协同终端 (Sidecar)

建议在主 Agent 运行的同时，在侧边打开第二个终端运行伴生窗口：
```bash
python sidecar.py
```
- **实时监控**：无缝观察主 Agent 的状态跃迁、当前执行工具、耗时与最近日志。
- **带外干预**：输入 `/steer <指导说明>`（如 `/steer 先别写代码，先查看现有测试`），指令将直接注入主 Agent 下一轮思考。
- **紧急打断**：输入 `/interrupt` 可立即强制终止主 Agent 正在运行的卡死终端命令。

---

## 🧪 自动化测试验证

项目内置了完整的单元测试，涵盖核心上下文压缩、容错替换算法、快照回滚与参数解析：
```bash
python -m unittest discover -s tests
```

---

## 📚 Agent 进阶与 LangGraph 学习资源

本项目已生成开箱即用的交互式架构图谱与学习平台：
- 本地文件：[agent_learning_guide.html](file:///D:/myclaude/agent_learning_guide.html)
- 在浏览器直接打开：`file:///D:/myclaude/agent_learning_guide.html`
- 涵盖 **7 步 ReAct 闭环管道步进拆解**、**模块文件深度剖析**、**5 大维度与 LangGraph 状态图代码对照** 以及 **4 阶段实战学习路线进度打卡器**。
