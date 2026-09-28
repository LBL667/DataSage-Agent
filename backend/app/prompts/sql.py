"""SQL 生成的提示词，带版本号。

每次修改留一个版本号，跑出问题时能回溯到具体版本。第 3 步尚未接入 RAG，
用演示表结构占位，第 11 步换成真实 schema 召回。
"""

from __future__ import annotations

SQL_PROMPT_VERSION = "0.2.0"

# 第 3 步演示用的表结构，第 11 步由 schema 集合召回替代
DEMO_SCHEMA = """
表 orders：订单表
- order_id：订单号
- user_id：用户 id
- channel：渠道
- amount：金额
- created_at：下单时间

表 order_items：订单明细
- item_id：明细 id
- order_id：所属订单
- product_id：商品 id
- quantity：数量
- price：单价

表 channels：渠道表
- channel_id：渠道 id
- channel_name：渠道名
"""

SQL_SYSTEM_PROMPT = """你是数据分析 Agent 的 SQL 生成器。根据用户诉求与表结构，生成一条只读的 MySQL SELECT 语句。

规则：
1. 只生成 SELECT，不生成任何写操作
2. 只使用提供的表结构中的表与列
3. 显式加上 LIMIT
4. 不要擅自添加时间过滤条件，除非用户明确指定了时间范围
5. 聚合查询要对非聚合列做 GROUP BY

按给定结构返回，字段为 sql、explain、tables、assumptions。
"""
