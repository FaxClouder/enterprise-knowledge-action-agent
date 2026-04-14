
# LangChain + LangGraph 企业知识库与自动化 Agent 项目说明文档
**用途**：本说明文档用于指导 Codex 直接完成项目开发，并为后续简历撰写、面试讲解与项目验收提供统一标准。  
**项目代号**：Enterprise Knowledge & Action Agent  
**默认语言**：代码与 README 使用英文；项目说明、注释和演示材料可使用中文。  
**实现原则**：优先交付一个可运行、可追踪、可评测、可演示的主项目，再逐步补强长期记忆、MCP 扩展和部署能力。

---

## 1. 项目目标

构建一个面向企业内部知识与轻量自动化任务的 Agent 系统，基于 **LangChain v1 + LangGraph** 实现，具备以下核心能力：

1. **Agentic RAG**：由 Agent 判断是否需要检索，而不是每次都机械检索。
2. **Skills**：按需加载领域技能，避免将全部规则一次性塞入上下文。
3. **Memory**：同时支持线程级短期记忆与跨会话长期记忆。
4. **MCP**：能够接入至少 1 个外部 MCP server，消费其 tools / resources。
5. **Tracing + Evals**：具备 LangSmith 追踪和小规模评测集，用于调试与回归验证。
6. **可讲解性**：代码结构清晰，README 完整，适合录制 2~3 分钟演示视频并写入简历。

---

## 2. 用户场景与任务范围

### 2.1 目标用户
- 希望查询内部知识的员工或实习生
- 需要快速总结文档、会议纪要或操作手册的用户
- 需要读取轻量外部资源（文档、数据库 schema、API 元信息）的开发者

### 2.2 必须支持的任务
1. 企业知识问答  
2. 多文档综合问答  
3. 文档总结 / 会议纪要摘要  
4. 简单 SQL / 数据查询辅助（只生成建议 SQL，不直接执行高风险写操作）  
5. 用户偏好记忆（例如：输出语言偏好、回答风格偏好）  
6. 通过 MCP 读取外部资源或调用安全工具

### 2.3 明确不做的内容
- 不做浏览器自动化代理
- 不做复杂多 Agent 协同
- 不做高风险写操作（删除、修改生产数据）
- 不做复杂前端；CLI 或最小 Web API 即可
- 不以“上传 PDF 聊天”作为最终形态，必须体现 Agent 编排能力

---

## 3. 设计原则

1. **先主链路，再增强模块**：先交付可运行骨架，再逐步补 RAG、Skills、Memory、MCP、Evals。
2. **Agent 负责决策，LangGraph 负责编排**：  
   - LangChain `create_agent` 负责模型 + 工具循环  
   - LangGraph 负责状态、节点、边、持久化、线程与恢复
3. **上下文最小化**：Skill 只在需要时加载；长期记忆只存有复用价值的信息。
4. **默认安全**：只开放只读工具和低风险操作；敏感信息放 `.env`。
5. **可观测**：任何关键节点都要能在 LangSmith trace 中看到。
6. **先本地跑通，再谈生产化**：本项目优先本地开发和作品展示，不以复杂部署为第一目标。

---

## 4. 技术选型（必须遵守）

### 4.1 语言与运行环境
- Python 3.11+
- 使用虚拟环境
- 使用 `pyproject.toml` 或 `requirements.txt` 均可，但优先 `pyproject.toml`

### 4.2 核心框架
- `langchain`（v1 风格接口）
- `langgraph`
- `langsmith`
- `langchain-openai` 或 `langchain-anthropic`（二选一，默认 OpenAI）
- `langchain-mcp-adapters`

### 4.3 检索与数据
- 开发态向量库：优先 Chroma（本地最省时间）
- 文档目录：`data/knowledge_base/`
- 默认支持：`.md`、`.txt`、`.pdf`
- 检索策略：基础向量检索 + 结果打分 + 查询改写

### 4.4 记忆与持久化
- 短期记忆：LangGraph checkpointer
- 长期记忆：先用可本地运行的 store 适配层，默认实现为 JSON / sqlite 持久层；代码结构需预留切换到正式 store 的能力

### 4.5 服务形态
- 必须支持 CLI 或本地 API 二选一
- 优先选择：LangGraph app + `langgraph.json`
- 可选增加：最小 FastAPI 包装层

---

## 5. 架构总览

### 5.1 系统流程
1. 用户输入问题  
2. 路由节点判断任务类型  
3. 决定是否触发 RAG  
4. 决定是否需要加载 Skill  
5. 决定是否需要调用本地工具或 MCP 工具  
6. 读取短期记忆与长期记忆  
7. 生成最终答案  
8. 记录 trace、评测输入输出与关键中间状态

### 5.2 必须存在的图节点
- `route_intent`
- `load_user_context`
- `decide_retrieval`
- `retrieve_documents`
- `grade_documents`
- `rewrite_query`
- `load_skill`
- `invoke_tools_or_mcp`
- `generate_answer`
- `persist_memory`

### 5.3 节点关系要求
- 允许 `grade_documents -> rewrite_query -> retrieve_documents` 的回路，最多 2 次
- `load_skill` 必须发生在最终回答前
- `persist_memory` 必须是成功路径和失败路径的共同终点之一

---

## 6. 仓库结构（Codex 必须按此生成）

```text
project/
  app/
    __init__.py
    graph.py
    state.py
    config.py
    prompts.py
    tools.py
    main.py
    rag/
      __init__.py
      ingest.py
      retriever.py
      grading.py
      rewrite.py
      schemas.py
    skills/
      __init__.py
      registry.py
      loader.py
      policy_qa/
        SKILL.md
      sql_analysis/
        SKILL.md
      meeting_summary/
        SKILL.md
    memory/
      __init__.py
      short_term.py
      long_term.py
      schemas.py
    mcp/
      __init__.py
      clients.py
      resources.py
  data/
    knowledge_base/
    memory_store/
  evals/
    dataset.jsonl
    rubrics.md
    run_eval.py
  tests/
    test_graph.py
    test_rag.py
    test_skills.py
    test_memory.py
    test_mcp.py
  scripts/
    ingest_docs.py
    demo_cli.py
  .env.example
  README.md
  langgraph.json
  pyproject.toml
```

---

## 7. 模块开发要求

## 7.1 Agent 主骨架模块
**目标**：先构建一个能接收问题、调工具、返回答案、写 trace 的最小 Agent。

### 必做
- 使用 `langchain.agents.create_agent`
- 至少提供 2 个本地工具：
  - `summarize_text`
  - `search_kb_metadata`（可先返回占位数据）
- 统一结构化输出：`answer`, `used_tools`, `used_skill`, `used_memory`, `citations`, `confidence`

### 验收标准
- 能在本地执行 3 组不同输入
- LangSmith 中能看到完整 trace
- 出错时返回可读错误消息，而不是直接崩溃

## 7.2 RAG 模块
**目标**：让 Agent 对内部知识进行可解释检索。

### 必做
- 文档加载：支持 md / txt / pdf
- chunk 切分
- embedding 入库
- 基础相似度检索
- 返回引用来源
- 文档打分节点
- 查询改写节点

### 行为要求
- 不是所有问题都检索
- 当检索结果质量低时，允许改写查询并重试一次或两次
- 最终回答必须附引用文档名

### 验收标准
- 至少准备 20 份文档
- 至少 10 条知识问答测试数据
- 能演示一次“第一次检索失败，改写后命中”的例子

## 7.3 Skills 模块
**目标**：实现 progressive disclosure。

### 必做
- Skill 注册表
- Skill 加载工具
- 至少 3 个 Skill：
  - `policy_qa`
  - `sql_analysis`
  - `meeting_summary`

### 每个 Skill 必须包含
- 适用场景
- 不适用场景
- 执行步骤
- 输出格式
- few-shot 示例（至少 1 个）

### 行为要求
- Agent 初始上下文中只暴露 Skill 名称和摘要
- 只有当任务匹配时才读取完整 `SKILL.md`

### 验收标准
- 普通知识问答时不加载 Skill
- SQL 问题只加载 SQL Skill
- 会议纪要任务只加载 summary Skill

## 7.4 Memory 模块
**目标**：实现线程内连续对话和跨会话偏好记忆。

### 短期记忆必做
- 保留消息历史
- 保留最近一次检索摘要
- 支持同一 `thread_id` 续聊

### 长期记忆必做
- 存储用户语言偏好
- 存储用户输出风格偏好
- 存储组织术语映射（例如内部缩写）
- 提供读写接口

### 行为要求
- 长期记忆必须是结构化记录，不允许原样堆积聊天日志
- 短期记忆过长时，允许总结压缩

### 验收标准
- 第二轮追问能利用第一轮上下文
- 新会话中仍能记住用户偏好
- 当用户修改偏好后，长期记忆可被覆盖更新

## 7.5 MCP 模块
**目标**：让 Agent 使用标准协议扩展外部能力。

### 必做
- 接入至少 1 个可用的 MCP server
- 至少消费 1 个 resource 或 1 个 tool
- 将 MCP 工具包装进主 Agent 的工具集合

### 推荐示例
- 文档类 MCP server
- 文件系统类 MCP server
- 数据库 schema / 元信息类 MCP server

### 行为要求
- 所有 MCP 调用必须限制为安全只读能力
- 出现连接失败时，Agent 应降级回本地能力，而不是整体失败

### 验收标准
- 至少 1 条示例对话明确使用了 MCP 工具或资源
- Trace 中可见 MCP 调用路径

## 7.6 Evaluation 模块
**目标**：证明该项目可调试、可回归。

### 必做
- `evals/dataset.jsonl` 至少 20 条数据
- 按任务类型覆盖：
  - RAG 问答
  - Skill 调用
  - MCP 调用
  - 多轮记忆
- 提供一个 `run_eval.py`
- 输出至少以下指标：
  - answer_correct
  - citation_present
  - expected_skill_selected
  - expected_tool_path

### 验收标准
- 能对评测集执行完整评估
- 能输出简单汇总报告
- README 中展示一张评测结果摘要表

---

## 8. 编码规范

1. 所有核心函数必须写 docstring  
2. 所有配置走 `config.py` 和环境变量  
3. 所有提示词集中在 `prompts.py` 或 `skills/*/SKILL.md`  
4. 工具函数和图节点函数分离  
5. 所有外部调用必须带异常处理  
6. 关键数据结构使用 `pydantic` 模型或 dataclass  
7. 单元测试覆盖核心链路  
8. 不允许把 API key 写入代码

---

## 9. 实施顺序（Codex 严格遵循）

### 阶段 1：最小可运行骨架
- 初始化仓库
- 接入模型
- 创建最小 agent
- 写 2 个本地工具
- 打通 trace

### 阶段 2：补 RAG
- 文档导入脚本
- 检索器
- 文档打分
- 查询改写
- 引用输出

### 阶段 3：补 Skills
- 建 Skill 注册表
- 实现加载工具
- 补 3 个 `SKILL.md`
- 让 Agent 根据任务触发 Skill

### 阶段 4：补 Memory
- 短期记忆 + thread
- 长期记忆存储与读写
- 记忆压缩 / 更新逻辑

### 阶段 5：补 MCP
- 配置 MCP client
- 导入至少 1 组 tools / resources
- 加失败降级逻辑

### 阶段 6：补 Evals 与 README
- 准备评测集
- 跑评测
- 生成 README、架构图说明、demo 指令

---

## 10. README 必须包含的内容

1. 项目简介  
2. 核心能力（RAG / Skills / Memory / MCP / Evals）  
3. 系统架构图（可用 Mermaid）  
4. 目录结构  
5. 环境变量说明  
6. 本地启动方式  
7. 文档导入方式  
8. 示例对话  
9. 评测方法  
10. 已知限制  
11. 后续优化方向

---

## 11. 演示要求

Codex 完成项目后，仓库应支持以下最小演示：

### 演示 1：知识问答
用户问某项企业政策，Agent 决定检索文档并给出引用。

### 演示 2：Skill 调用
用户要求“根据销售表结构生成查询某月 GMV 的 SQL”，Agent 加载 SQL Skill 并输出建议 SQL。

### 演示 3：记忆
用户先声明“以后尽量用中文，回答简洁”，下一轮新会话仍保持该偏好。

### 演示 4：MCP
用户请求读取某外部资源或调用某只读工具，Agent 完成调用并整合答案。

---

## 12. 验收清单

### 功能验收
- [ ] Agent 主链路可运行  
- [ ] RAG 可用且有引用  
- [ ] Skills 可按需加载  
- [ ] Memory 支持短期和长期  
- [ ] MCP 至少接入 1 个外部能力  
- [ ] Evals 可运行  

### 工程验收
- [ ] 仓库结构清晰  
- [ ] `.env.example` 完整  
- [ ] README 可独立指导运行  
- [ ] 有最小测试集  
- [ ] trace 可视化正常  

### 求职验收
- [ ] 能录 2~3 分钟 demo  
- [ ] 能用 3~5 句话讲清架构  
- [ ] 能展示至少 1 张评测结果图或表  
- [ ] 能解释 Skills 与 Memory 的区别  
- [ ] 能解释 MCP 与普通工具封装的区别  

---

## 13. 已知风险与处理策略

### 风险 1：RAG 效果差
处理：
- 优先检查 chunk 大小与 overlap
- 增加查询改写
- 增加文档打分
- 不要把纯聊天问题硬送检索

### 风险 2：Skill 加载过多
处理：
- 只把 skill 名称和摘要放入初始上下文
- 将长说明保存在 `SKILL.md`
- 使用显式 `load_skill` 工具

### 风险 3：Memory 污染上下文
处理：
- 长期记忆只存结构化偏好与术语
- 对历史消息做裁剪或总结
- 禁止无差别注入所有历史聊天

### 风险 4：MCP 不稳定
处理：
- 做超时控制
- 做失败回退
- 默认只接只读工具
- 使用本地替代工具保持主流程可运行

---

## 14. 面试时如何讲这个项目

推荐讲法：

> 我做的是一个基于 LangChain v1 和 LangGraph 的企业知识库与自动化 Agent。  
> 它不是简单的问答机器人，而是一个带决策能力的 Agent：会先判断要不要检索，再按需加载 Skill，并结合短期和长期记忆来完成任务。  
> 我还通过 MCP 接入了外部工具 / 资源，并用 LangSmith 做 trace 和 trajectory eval，确保项目不仅能跑，还能调试和回归验证。

---

## 15. 简历表达方式

## 15.1 中文版项目名称
**企业知识库与自动化 Agent（LangChain + LangGraph）**

## 15.2 中文版简历描述（适合校招 / 实习）
- 基于 LangChain `create_agent` 与 LangGraph 构建企业知识库 Agent，实现任务路由、工具调用、状态化执行与可追踪工作流。  
- 设计 Agentic RAG 流程，支持检索决策、查询改写、文档相关性打分和带引用问答，提升复杂知识问答的可解释性。  
- 实现基于 `SKILL.md` 的按需技能加载机制，并结合短期 / 长期记忆维护用户偏好与会话上下文，降低上下文冗余。  
- 通过 MCP 接入外部只读工具 / 资源，使用 LangSmith 进行 trace 与评测，构建可调试、可回归的 Agent 工程项目。

## 15.3 中文版强化描述（适合简历项目亮点）
- 将 Skills、Memory、MCP 与 Agentic RAG 统一到 LangGraph 编排图中，形成可扩展的企业级 Agent 原型。  
- 构建 20+ 条评测集，覆盖知识问答、技能选择、记忆调用和工具路径，支持 prompt / tool / graph 变更后的回归验证。  
- 设计结构化长期记忆存储方案，保存用户偏好与组织术语，提升跨会话一致性与回答个性化。

## 15.4 英文版项目名称
**Enterprise Knowledge & Action Agent (LangChain + LangGraph)**

## 15.5 英文版简历描述
- Built a stateful enterprise knowledge and automation agent with LangChain `create_agent` and LangGraph, covering task routing, tool use, graph orchestration, and traceable execution.  
- Implemented agentic RAG with retrieval gating, query rewriting, document relevance grading, and citation-backed answers for internal knowledge tasks.  
- Added on-demand skills via `SKILL.md`-based progressive disclosure and combined short-term / long-term memory to preserve user preferences and conversational context.  
- Integrated external read-only capabilities through MCP and used LangSmith tracing/evaluations to support debugging, observability, and regression testing.

---

## 16. 面试追问准备

### Q1：为什么不用纯 RAG？
答：因为目标不是“每次都检索”，而是让 Agent 先判断当前问题是否需要知识库、技能或外部工具；这比固定 RAG 链更贴近真实 Agent 场景。

### Q2：Skills 和 Memory 的区别是什么？
答：Skills 是按需加载的专门能力，解决上下文过重问题；Memory 是持续注入或可检索的历史信息，解决跨轮与跨会话连续性问题。

### Q3：为什么要加 MCP？
答：MCP 让工具和上下文接入采用标准协议，而不是每接一个系统就手写一套封装；这样项目更容易扩展到文件、文档、数据库和其他系统。

### Q4：为什么要做评测？
答：Agent 系统不是写完 prompt 就结束。加入 trace 和 trajectory eval 后，才能知道模型是否走了预期路径，以及改 prompt / tool 后是否退化。

---

## 17. Codex 最终交付物清单

Codex 完成后，仓库必须至少包含：
1. 完整代码
2. `.env.example`
3. `README.md`
4. `langgraph.json`
5. 最小样例数据
6. 评测脚本与评测集
7. 至少 3 个 `SKILL.md`
8. 一个可直接运行的 demo 入口
9. 基本测试文件
10. 一份 `PROJECT_SUMMARY.md`，概述架构、能力和演示方式

---

## 18. 官方能力约束（用于实现时参考）

- 单 Agent 推荐使用 LangChain v1 的 `create_agent`。  
- LangGraph 负责状态图、持久化、线程与恢复。  
- 短期记忆为 thread-scoped，长期记忆应跨会话组织。  
- Skills 采用 progressive disclosure，只在需要时加载。  
- MCP 用于标准化接入 tools / resources。  
- 评测至少覆盖最终回答与工具路径两层。

---

## 19. 对 Codex 的执行指令（可直接复制）

1. 严格按照本说明文档创建仓库与目录结构。  
2. 不要先做前端，先保证主链路运行、trace 正常、README 可复现。  
3. 先完成最小 Agent，再逐步加入 RAG、Skills、Memory、MCP、Evals。  
4. 所有环境变量写入 `.env.example`。  
5. 所有关键路径加日志和错误处理。  
6. 所有对外能力默认只读。  
7. 任何能力做不到时，先提供降级版本，不要阻塞整个项目。  
8. 完成后补全 README 与演示说明，确保项目可直接用于简历和面试展示。

---
