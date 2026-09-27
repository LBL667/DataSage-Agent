# DataSage Agent

连接本地 MySQL 的数据分析 Agent。用户用自然语言提出分析需求，Agent 完成取数、质检、清洗、分析、可视化，全过程可审批、可追溯、可审计。单用户，本机部署。

## 核心设计

- 分层架构，表现层、编排层、能力层、存储层四层分离
- LangGraph 图编排，18 个节点分四阶段
- 只读账号加只读事务构成安全边界，sqlglot AST 校验与独立审查 Agent 作效率优化
- 分级审批加表级授权 TTL，把打断次数降到接近零
- 清洗规则显式化，全程留痕可回滚
- 算子白名单替代沙箱，模型只输出结构化指令

完整技术规范见仓库外部的 `analysis-agent-spec.md`，此处只保留可运行代码。

## 目录结构

```
backend/
├── app/
│   ├── main.py            FastAPI 入口与生命周期
│   ├── config.py          配置加载，Pydantic 读 .env，yaml 读黑白名单与清洗规则
│   ├── errors.py          统一异常与错误码
│   ├── llm.py             模型客户端
│   ├── api/               五个面板的接口
│   ├── graph/             LangGraph 状态、组装与节点
│   ├── middleware/        凭据解析与横切中间件
│   ├── guard/             SQL 校验与出域控制
│   ├── operators/         算子白名单
│   ├── rag/               三集合检索
│   ├── tools/             MCP 形态工具封装
│   ├── storage/           结果集落盘
│   ├── prompts/           按节点的提示词
│   └── observability/     结构化日志与事件模型
├── config/                白名单、黑名单、清洗规则
├── scripts/               验证脚本
├── data/                  结果集与 checkpoint
└── api-contract.md        接口契约
```

## 快速开始

依赖 uv 与 Python 3.12。

```bash
cd backend
uv sync                          # 安装锁定版本依赖
cp .env.example .env             # 填写数据库只读账号与模型密钥
uv run uvicorn app.main:app --reload
```

`/health` 返回服务状态与图加载状态。

## 验证脚本

```bash
uv run python scripts/check_readonly.py          # 验证只读通道
uv run python scripts/run_graph.py "最近三个月各渠道 GMV"   # 跑通带审批的取数
```

## 开发进度

按《后端开发顺序》推进，当前完成第 0 到第 3 步。

- 第 0 步 接口契约盘点，产出 `api-contract.md`
- 第 1 步 工程骨架，FastAPI 入口、配置加载、五个面板桩端点
- 第 2 步 凭据与只读通道，resolve_credential、只读执行、结果落盘
- 第 3 步 状态契约与最小图，AnalysisState、三节点图、sqlite checkpointer、中断恢复
