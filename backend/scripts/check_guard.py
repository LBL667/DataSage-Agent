"""验证安全护栏。

用攻击用例测，不用正常用例。四类：union 非白名单、写操作语句、select 星号、
低风险查询与授权记忆。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import load_blacklist, load_whitelist  # noqa: E402
from app.guard import grant_store, risk  # noqa: E402

WHITELIST = load_whitelist()
BLACKLIST = load_blacklist()


def _check(name: str, sql: str, expect_level: str) -> None:
    r = risk.assess(sql, WHITELIST, BLACKLIST)
    ok = r["level"] == expect_level
    mark = "通过" if ok else "未通过"
    print(f"[{mark}] {name}: 判定 {r['level']}, 期望 {expect_level}")
    if r["reasons"]:
        print(f"       理由: {r['reasons']}")


def main() -> None:
    print(f"白名单: {WHITELIST}")
    print(f"黑名单列: {BLACKLIST.get('columns')}\n")

    # 1. union 拼接到非白名单表
    _check("union 非白名单表", "SELECT * FROM orders UNION SELECT * FROM secret_table", "high")

    # 2. 写操作语句
    _check("UPDATE 写操作", "UPDATE orders SET amount = 0 WHERE 1 = 1", "high")
    _check("DELETE 写操作", "DELETE FROM orders WHERE 1 = 1", "high")

    # 3. select 星号
    _check("select 星号", "SELECT * FROM orders", "high")

    # 4. 命中敏感列
    _check("命中敏感列 phone", "SELECT order_id, phone FROM orders LIMIT 10", "high")

    # 5. 正常低风险查询
    _check("正常低风险查询", "SELECT order_id, amount FROM orders LIMIT 10", "low")

    # 6. 授权记忆
    print("\n=== 授权记忆 ===")
    session = "s_test"
    tables = ["secret_table"]
    print(f"首次查询 secret_table 是否已授权: {grant_store.is_granted(session, tables)}")
    grant_store.grant(session, tables)
    print(f"授权后是否已授权: {grant_store.is_granted(session, tables)}")


if __name__ == "__main__":
    main()
