# 接口契约

前端五个面板与后端交互的全部端点。这份文档是前后端解耦的依据，也是批次 7 实现 API 层的规格说明。

后端先行，前端尚未开发。本契约自行设计，作为将来前端的规格说明书。每个端点固定记录七项，路径、方法、请求体、响应体、是否流式、错误结构、所属面板。

## 一、通用约定

### 1.1 错误结构

错误响应统一三类，横切全部端点。前端据此决定提示重试还是直接报错。

| 类型 | HTTP 状态 | code | retryable | 含义 |
|---|---|---|---|---|
| 参数错误 | 400 | `PARAM_ERROR` | false | 请求体缺字段或类型不符 |
| 业务错误 | 400 或 409 | `BUSINESS_ERROR` | 按场景 | 业务规则不满足，可重试与不可重试再区分 |
| 系统错误 | 500 | `SYSTEM_ERROR` | false | 服务内部异常，不含堆栈与凭据 |

错误响应体统一。

```json
{
  "code": "PARAM_ERROR",
  "message": "缺少必填字段 user_goal",
  "retryable": false,
  "trace_id": "tr_9f2c"
}
```

### 1.2 其他约定

- 所有响应带 `trace_id`，贯穿一次分析的完整链路
- 时间字段用带时区的 ISO 8601 字符串
- 金额字段返回原始值，格式化由前端负责
- 凭据明文、完整结果集、异常堆栈不出现在任何响应体里

---

## 二、端点总表

| 路径 | 方法 | 流式 | 所属面板 |
|---|---|---|---|
| `/health` | GET | 否 | 通用 |
| `/api/chat` | POST | 是 | 对话 |
| `/api/chat/threads` | GET | 否 | 对话 |
| `/api/chat/threads` | POST | 否 | 对话 |
| `/api/chat/threads/{thread_id}` | DELETE | 否 | 对话 |
| `/api/chat/{thread_id}/history` | GET | 否 | 对话 |
| `/api/chat/{thread_id}/resume` | POST | 否 | 对话 |
| `/api/config/db` | GET | 否 | 配置 |
| `/api/config/db/test` | POST | 否 | 配置 |
| `/api/config/whitelist` | GET | 否 | 配置 |
| `/api/config/whitelist` | PUT | 否 | 配置 |
| `/api/config/blacklist` | GET | 否 | 配置 |
| `/api/config/blacklist` | PUT | 否 | 配置 |
| `/api/config/clean-rules` | GET | 否 | 配置 |
| `/api/config/clean-rules` | POST | 否 | 配置 |
| `/api/config/clean-rules/{rule_id}` | PUT | 否 | 配置 |
| `/api/config/clean-rules/{rule_id}` | DELETE | 否 | 配置 |
| `/api/config/thresholds` | GET | 否 | 配置 |
| `/api/config/thresholds` | PUT | 否 | 配置 |
| `/api/dashboard/results` | GET | 否 | 仪表盘 |
| `/api/dashboard/results/{result_id}` | GET | 否 | 仪表盘 |
| `/api/dashboard/data/{result_ref}` | GET | 否 | 仪表盘 |
| `/api/rag/documents` | GET | 否 | 知识库 |
| `/api/rag/documents` | POST | 否 | 知识库 |
| `/api/rag/documents/{doc_id}` | DELETE | 否 | 知识库 |
| `/api/rag/search` | POST | 否 | 知识库 |
| `/api/rag/collections/{collection}/rebuild` | POST | 否 | 知识库 |
| `/api/logs/events` | GET | 否 | 日志 |
| `/api/logs/stream` | GET | 是 | 日志 |
| `/api/logs/approvals` | GET | 否 | 日志 |

---

## 三、分面板详表

### 3.1 对话面板

#### POST /api/chat

发起一次分析。返回 SSE 流，事件级推送节点状态与最终回复。

请求体

```json
{
  "thread_id": "ss_8813",
  "message": "帮我看下最近三个月各渠道的 GMV 走势"
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| thread_id | string | 否 | 不传则新建会话并返回新 id |
| message | string | 是 | 用户输入的自然语言诉求 |

响应体，SSE 事件流，每个事件一个 data 行。

```json
{
  "event": "node_start",
  "node": "sql_generate",
  "ts": "2026-09-27T18:12:03.221+08:00",
  "trace_id": "tr_9f2c"
}
```

事件类型枚举，node_start、node_end、tool_call、approval_request、error、final。最终回复单独一条 final 事件携带正文。

#### POST /api/chat/{thread_id}/resume

审批回传。三个动作，取消、修改并附意见、同意。

请求体

```json
{
  "decision": "approve",
  "comment": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| decision | string | 是 | approve、edit、cancel 三选一 |
| comment | string | 否 | edit 时携带修改意见 |

响应体为 `{ "ok": true, "trace_id": "tr_9f2c" }`。

#### GET /api/chat/{thread_id}/history

拉取会话历史消息，用于刷新页面后恢复。

响应体

```json
{
  "thread_id": "ss_8813",
  "messages": [
    { "role": "user", "content": "帮我看下 GMV", "ts": "2026-09-27T18:10:00+08:00" }
  ]
}
```

#### GET /api/chat/threads

会话列表，按更新时间倒序。

响应体

```json
{
  "threads": [
    { "thread_id": "ss_8813", "title": "各渠道 GMV 走势", "updated_at": "2026-09-27T18:12:03+08:00" }
  ]
}
```

#### POST /api/chat/threads

新建会话，返回新 thread_id。

响应体

```json
{ "thread_id": "ss_8813" }
```

#### DELETE /api/chat/threads/{thread_id}

删除会话及其 checkpoint。

响应体

```json
{ "ok": true }
```

### 3.2 配置面板

#### GET /api/config/db

返回当前数据库连接状态与目标库名。方案 A 下不返回也不接收密码。

响应体

```json
{
  "status": "connected",
  "host": "127.0.0.1",
  "database": "your_db",
  "user": "agent_ro"
}
```

#### POST /api/config/db/test

测试连接，请求体为空。响应体为 `{ "ok": true }` 或带错误信息。

#### GET /api/config/whitelist

返回允许 Agent 访问的表清单。

响应体

```json
{ "tables": ["orders", "order_items", "channels"] }
```

#### PUT /api/config/whitelist

整体替换白名单。请求体与 GET 响应同构。

#### GET /api/config/blacklist

返回敏感字段黑名单与语句黑名单。

响应体

```json
{
  "columns": ["phone", "id_card", "bank_account"],
  "column_patterns": ["*_secret"],
  "statements": ["INTO OUTFILE", "LOAD_FILE"]
}
```

#### PUT /api/config/blacklist

整体替换黑名单。请求体与 GET 响应同构。

#### GET /api/config/clean-rules

返回清洗规则列表。每条规则含 id、目标列、动作、参数、启用开关。

响应体

```json
{
  "rules": [
    { "id": "R1", "target": ["*"], "action": "drop_duplicate", "key": ["order_id"], "enabled": true }
  ]
}
```

#### POST /api/config/clean-rules

新增一条清洗规则，请求体为单条规则对象，响应体返回生成的规则 id。

#### PUT /api/config/clean-rules/{rule_id}

更新指定规则，请求体为完整规则对象。

#### DELETE /api/config/clean-rules/{rule_id}

删除指定规则。

#### GET /api/config/thresholds

返回审批阈值与超时配置。

响应体

```json
{
  "max_scan_rows": 100000,
  "sql_timeout_s": 10,
  "grant_ttl_s": 1800
}
```

#### PUT /api/config/thresholds

更新阈值。请求体与 GET 响应同构。

### 3.3 仪表盘面板

#### GET /api/dashboard/results

返回历史分析结果列表。

响应体

```json
{
  "results": [
    {
      "result_id": "r_001",
      "title": "各渠道 GMV 走势",
      "time_window": ["2026-06-27", "2026-09-27"],
      "created_at": "2026-09-27T18:12:03+08:00",
      "thread_id": "ss_8813"
    }
  ]
}
```

#### GET /api/dashboard/results/{result_id}

返回单个分析结果，含图表规格与数据来源说明。

响应体

```json
{
  "result_id": "r_001",
  "chart_spec": {
    "chart_type": "line",
    "x_field": "date",
    "y_field": "gmv",
    "series": "channel"
  },
  "source_tables": ["orders"],
  "clean_rules_applied": ["R4"],
  "thread_id": "ss_8813"
}
```

#### GET /api/dashboard/data/{result_ref}

按结果引用分页拉取渲染数据。图表数据量小时可一次性返回。

请求参数，offset、limit。

响应体

```json
{
  "columns": ["date", "channel", "gmv"],
  "rows": [["2026-09-01", "华东", 128000]],
  "total": 1
}
```

### 3.4 知识库面板

#### GET /api/rag/documents

返回文档列表。每个文档含文件名、所属集合、切分块数、入库时间。

响应体

```json
{
  "documents": [
    { "doc_id": "d_001", "name": "orders_schema.md", "collection": "schema", "chunks": 1, "created_at": "2026-09-27T18:00:00+08:00" }
  ]
}
```

#### POST /api/rag/documents

上传文档。multipart 表单，字段 file 与 collection。collection 取值 schema、metric、method。响应体返回文档 id 与切分块数。

#### DELETE /api/rag/documents/{doc_id}

删除文档并清理对应向量。响应体为 `{ "ok": true }`。

#### POST /api/rag/search

检索测试，预览召回结果与相似度得分。

请求体

```json
{ "query": "orders 表有哪些字段", "collection": "schema", "top_k": 10 }
```

响应体

```json
{
  "chunks": [
    { "content": "orders 表字段说明", "score": 0.87, "source": "orders_schema.md" }
  ]
}
```

#### POST /api/rag/collections/{collection}/rebuild

整集合重建。请求体为空，响应体为 `{ "ok": true }`。

### 3.5 日志面板

#### GET /api/logs/events

按条件查询历史事件。

请求参数，node、status、from、to、approval。

响应体

```json
{
  "events": [
    {
      "ts": "2026-09-27T18:12:03.221+08:00",
      "trace_id": "tr_9f2c",
      "node": "readonly_exec",
      "event": "tool_call",
      "duration_ms": 842,
      "status": "ok"
    }
  ]
}
```

#### GET /api/logs/stream

SSE 实时订阅。事件级推送，结构同事件查询。供日志面板实时亮灯。

#### GET /api/logs/approvals

审批记录单独视图。返回每次审批的动作、时间、决策。

响应体

```json
{
  "approvals": [
    { "ts": "2026-09-27T18:12:03+08:00", "table": "orders", "decision": "approve", "actor": "u_01" }
  ]
}
```

---

## 四、事件类型枚举

前端日志面板按此枚举做筛选，后端事件写入据此定死。

| event | 含义 |
|---|---|
| node_start | 节点开始执行 |
| node_end | 节点执行结束，带耗时 |
| tool_call | 工具调用，带目标对象与扫描行数 |
| approval_request | 发起审批请求 |
| error | 错误事件，带异常类型与摘要 |

事件结构与《analysis-agent-spec.md》第 12 节一致，字段一旦有下游消费就不再改动。
