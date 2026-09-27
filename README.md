# DataSage Agent

连接本地 MySQL 的数据分析 Agent。用户用自然语言提出分析需求，Agent 完成取数、质检、清洗、分析、可视化，全过程可审批、可追溯、可审计。单用户，本机部署。

## 目录

- `backend/` FastAPI 加 LangGraph 后端，uv 管理，Python 3.12。开发进度与快速开始见 `backend/README.md`
- `frontend/` 五面板工作台前端，暂未开始开发

## 后端开发进度

按《后端开发顺序》推进，已完成第 0 到第 5 步。

| 步 | 内容 | 状态 |
|---|---|---|
| 0 | 接口契约盘点，产出 `backend/api-contract.md` | 完成 |
| 1 | 工程骨架，FastAPI 入口、配置加载、五个面板桩端点 | 完成 |
| 2 | 凭据与只读通道，resolve_credential、只读执行、结果落盘 | 完成 |
| 3 | 状态契约与最小图，AnalysisState、三节点图、checkpoint 中断恢复 | 完成 |
| 4 | SSE 事件流，EventStore 持久化、chat/logs 真实现、审批回传 | 完成 |
| 5 | 中间件层，节点埋点装饰器、成本熔断、超时重试 | 完成 |

## 许可证

MIT，见 `LICENSE`。
