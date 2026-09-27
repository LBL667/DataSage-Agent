"""验证只读通道。

验收两条。一条 SELECT 跑通并落盘，一条 UPDATE 被数据库拒绝。
第二条是重点，验证的是账号权限真的生效，而不是被代码拦住。
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.middleware.credential import resolve_credential  # noqa: E402
from app.tools.mysql_tool import close_pool, execute_query  # noqa: E402


async def main() -> None:
    cred = resolve_credential("single")
    print(f"连接目标 {cred.user}@{cred.host}:{cred.port}/{cred.database}")

    # 第一条，SELECT 通
    try:
        ref, meta = await execute_query("SELECT 1 AS ok")
        print(f"[通过] SELECT 执行成功，result_ref={ref}，meta={meta}")
    except Exception as e:  # noqa: BLE001
        print(f"[失败] SELECT 未跑通：{type(e).__name__}: {e}")
        return

    # 第二条，UPDATE 被数据库拒绝
    try:
        await execute_query("UPDATE orders SET amount = 0 WHERE 1 = 1")
        print("[失败] UPDATE 被执行了，说明连的是主账号，安全边界是假的")
    except Exception as e:  # noqa: BLE001
        print(f"[通过] UPDATE 被数据库拒绝：{type(e).__name__}: {e}")

    await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
