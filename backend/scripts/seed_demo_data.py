"""在 datasage_db 建演示表并插入数据。

幂等，可重复运行。orders 20 条，order_items 若干，channels 3 条。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiomysql  # noqa: E402

from app.middleware.credential import resolve_credential  # noqa: E402

DROP_SQL = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS channels;
"""

CREATE_SQL = """
CREATE TABLE channels (
    channel_id INT PRIMARY KEY COMMENT '渠道 id',
    channel_name VARCHAR(50) NOT NULL COMMENT '渠道名'
) COMMENT='渠道表';

CREATE TABLE orders (
    order_id INT PRIMARY KEY COMMENT '订单号',
    user_id INT NOT NULL COMMENT '用户 id',
    channel VARCHAR(50) NOT NULL COMMENT '渠道',
    amount DECIMAL(10,2) NOT NULL COMMENT '金额',
    created_at DATE NOT NULL COMMENT '下单时间'
) COMMENT='订单表';

CREATE TABLE order_items (
    item_id INT PRIMARY KEY COMMENT '明细 id',
    order_id INT NOT NULL COMMENT '所属订单',
    product_id INT NOT NULL COMMENT '商品 id',
    quantity INT NOT NULL COMMENT '数量',
    price DECIMAL(10,2) NOT NULL COMMENT '单价'
) COMMENT='订单明细';
"""

# channels 3 条
CHANNELS = [
    (1, "华东"),
    (2, "华南"),
    (3, "华北"),
]

# orders 20 条，覆盖三个渠道与最近三个月
ORDERS = [
    (101, 1001, "华东", 128.00, "2026-06-02"),
    (102, 1002, "华南", 256.50, "2026-06-11"),
    (103, 1003, "华北", 89.90, "2026-06-18"),
    (104, 1004, "华东", 399.00, "2026-06-25"),
    (105, 1005, "华南", 178.20, "2026-07-03"),
    (106, 1006, "华东", 45.00, "2026-07-09"),
    (107, 1007, "华北", 512.80, "2026-07-15"),
    (108, 1008, "华南", 66.60, "2026-07-22"),
    (109, 1009, "华东", 233.30, "2026-07-29"),
    (110, 1010, "华北", 98.00, "2026-08-04"),
    (111, 1011, "华东", 320.50, "2026-08-12"),
    (112, 1012, "华南", 150.00, "2026-08-19"),
    (113, 1013, "华北", 275.40, "2026-08-26"),
    (114, 1014, "华东", 410.20, "2026-09-02"),
    (115, 1015, "华南", 88.80, "2026-09-08"),
    (116, 1016, "华东", 190.00, "2026-09-14"),
    (117, 1017, "华北", 350.60, "2026-09-18"),
    (118, 1018, "华东", 120.90, "2026-09-22"),
    (119, 1019, "华南", 460.00, "2026-09-25"),
    (120, 1020, "华北", 205.30, "2026-09-27"),
]

# order_items 若干条，关联 orders
ORDER_ITEMS = [
    (1001, 101, 2001, 2, 64.00),
    (1002, 102, 2002, 1, 256.50),
    (1003, 103, 2003, 3, 29.97),
    (1004, 104, 2004, 1, 399.00),
    (1005, 105, 2005, 2, 89.10),
    (1006, 106, 2006, 1, 45.00),
    (1007, 107, 2007, 4, 128.20),
    (1008, 108, 2008, 2, 33.30),
    (1009, 109, 2009, 1, 233.30),
    (1010, 110, 2010, 2, 49.00),
    (1011, 111, 2011, 1, 320.50),
    (1012, 112, 2012, 3, 50.00),
]


async def main() -> None:
    cred = resolve_credential("single")
    print(f"连接 {cred.user}@{cred.host}:{cred.port}/{cred.database}")

    conn = await aiomysql.connect(
        host=cred.host, port=cred.port, user=cred.user,
        password=cred.password, db=cred.database, autocommit=True,
    )
    try:
        cur = await conn.cursor()
        for stmt in DROP_SQL.strip().split(";"):
            if stmt.strip():
                await cur.execute(stmt)
        for stmt in CREATE_SQL.strip().split(";"):
            if stmt.strip():
                await cur.execute(stmt)
        await cur.executemany("INSERT INTO channels VALUES (%s, %s)", CHANNELS)
        await cur.executemany(
            "INSERT INTO orders (order_id, user_id, channel, amount, created_at) VALUES (%s, %s, %s, %s, %s)",
            ORDERS,
        )
        await cur.executemany(
            "INSERT INTO order_items (item_id, order_id, product_id, quantity, price) VALUES (%s, %s, %s, %s, %s)",
            ORDER_ITEMS,
        )
        await cur.close()
    finally:
        conn.close()

    print(f"完成：channels {len(CHANNELS)} 条，orders {len(ORDERS)} 条，order_items {len(ORDER_ITEMS)} 条")


if __name__ == "__main__":
    asyncio.run(main())
