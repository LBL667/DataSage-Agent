"""在 datasage_db 建演示表并插入 100 条多维度数据。

幂等，可重复运行。orders 100 条，含渠道、地区、品类、金额、利润、数量、
状态、时间七个维度，够做柱状图、折线图、环形图。order_items 约 200 条。

写权限账号用环境变量覆盖，默认读 .env 的 DB 账号。
"""

from __future__ import annotations

import asyncio
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aiomysql  # noqa: E402

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
    channel VARCHAR(20) NOT NULL COMMENT '渠道',
    region VARCHAR(20) NOT NULL COMMENT '地区',
    category VARCHAR(20) NOT NULL COMMENT '品类',
    amount DECIMAL(12,2) NOT NULL COMMENT '金额',
    profit DECIMAL(12,2) NOT NULL COMMENT '利润',
    quantity INT NOT NULL COMMENT '数量',
    status VARCHAR(20) NOT NULL COMMENT '状态',
    created_at DATE NOT NULL COMMENT '下单时间'
) COMMENT='订单表';

CREATE TABLE order_items (
    item_id INT PRIMARY KEY COMMENT '明细 id',
    order_id INT NOT NULL COMMENT '所属订单',
    product_name VARCHAR(50) NOT NULL COMMENT '商品名',
    quantity INT NOT NULL COMMENT '数量',
    price DECIMAL(10,2) NOT NULL COMMENT '单价'
) COMMENT='订单明细';
"""

CHANNELS = [
    (1, "华东"),
    (2, "华南"),
    (3, "华北"),
    (4, "西南"),
    (5, "东北"),
]

CATEGORIES = ["数码", "家电", "服饰", "食品", "美妆"]

REGIONS = ["华东", "华南", "华北", "西南", "东北"]

STATUSES = [("已完成", 8), ("待发货", 1), ("已取消", 1)]

PRODUCTS = {
    "数码": ["手机", "耳机", "平板", "充电器", "键盘"],
    "家电": ["冰箱", "洗衣机", "空调", "微波炉", "电饭煲"],
    "服饰": ["T恤", "牛仔裤", "卫衣", "夹克", "运动鞋"],
    "食品": ["坚果", "咖啡", "茶叶", "饼干", "巧克力"],
    "美妆": ["口红", "面霜", "面膜", "精华", "眼影"],
}


def gen_orders(n: int = 100) -> list[tuple]:
    rng = random.Random(42)
    rows = []
    start = date(2026, 3, 1)
    end = date(2026, 9, 30)
    span = (end - start).days

    for i in range(1, n + 1):
        channel = rng.choice(REGIONS)
        region = rng.choice(REGIONS)
        category = rng.choice(CATEGORIES)
        base = rng.uniform(100, 3000)
        quantity = rng.randint(1, 6)
        amount = round(base * quantity, 2)
        margin = rng.uniform(0.10, 0.40)
        profit = round(amount * margin, 2)
        status = rng.choices([s for s, _ in STATUSES], weights=[w for _, w in STATUSES])[0]
        created_at = start + timedelta(days=rng.randint(0, span))
        rows.append(
            (i, rng.randint(1001, 1200), channel, region, category, amount, profit, quantity, status, created_at)
        )
    return rows


def gen_items(orders: list[tuple]) -> list[tuple]:
    rng = random.Random(7)
    rows = []
    item_id = 1
    for order in orders:
        order_id = order[0]
        category = order[4]
        products = PRODUCTS[category]
        n_items = rng.randint(1, 3)
        for _ in range(n_items):
            product = rng.choice(products)
            qty = rng.randint(1, 3)
            price = round(rng.uniform(20, 1500), 2)
            rows.append((item_id, order_id, product, qty, price))
            item_id += 1
    return rows


async def main() -> None:
    user = os.environ.get("SEED_DB_USER") or os.environ.get("DB_USER", "root")
    password = os.environ.get("SEED_DB_PASSWORD") or os.environ.get("DB_PASSWORD", "")
    host = os.environ.get("DB_HOST", "127.0.0.1")
    port = int(os.environ.get("DB_PORT", "3306"))
    db = os.environ.get("DB_NAME", "datasage_db")

    print(f"连接 {user}@{host}:{port}/{db}")

    conn = await aiomysql.connect(host=host, port=port, user=user, password=password, db=db, autocommit=False)
    try:
        cur = await conn.cursor()
        await cur.execute(DROP_SQL)
        await cur.execute(CREATE_SQL)

        orders = gen_orders(100)
        items = gen_items(orders)

        await cur.executemany("INSERT INTO channels (channel_id, channel_name) VALUES (%s, %s)", CHANNELS)
        await cur.executemany(
            "INSERT INTO orders (order_id, user_id, channel, region, category, amount, profit, quantity, status, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            orders,
        )
        await cur.executemany(
            "INSERT INTO order_items (item_id, order_id, product_name, quantity, price) VALUES (%s, %s, %s, %s, %s)",
            items,
        )
        await conn.commit()
        print(f"完成：channels {len(CHANNELS)} 条，orders {len(orders)} 条，order_items {len(items)} 条")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())
