"""验证第 10 步。工具调用走 MCP 通道。"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.tools.registrar import get_registry  # noqa: E402


async def main() -> None:
    reg = get_registry()
    await reg.init()
    print(f"MCP 工具已装配 {len(reg._tools)} 个\n")

    # 1. mysql_query 走 MCP 通道
    result = await reg.call("mysql_query", sql="SELECT channel, SUM(amount) AS total FROM orders GROUP BY channel")
    print(f"[通过] mysql_query: ref={result['result_ref']}, meta={result['meta']}")
    ref = result["result_ref"]

    # 2. quality_probe
    report = await reg.call("quality_probe", data_ref=ref)
    print(f"[通过] quality_probe: passed={report['passed']}, 检查 {len(report['checks'])} 项")

    # 3. clean_exec
    clean = await reg.call("clean_exec", data_ref=ref)
    print(f"[通过] clean_exec: applied={clean['clean_rules_applied']}")

    # 4. run_operator
    op = await reg.call(
        "run_operator",
        action="attribution",
        params={"metric": "total", "group_by": ["channel"]},
        data_ref=clean["cleaned_ref"] or ref,
    )
    print(f"[通过] run_operator: {op.get('note')}")

    # 5. chart_validate
    columns = result["meta"]["columns"]
    cv = await reg.call(
        "chart_validate",
        chart_spec={"chart_type": "bar", "x_field": "channel", "y_field": "total"},
        columns=columns,
    )
    print(f"[通过] chart_validate: ok={cv['ok']}")

    # 6. rag_search 占位
    rag = await reg.call("rag_search", query="订单", collection="schema")
    print(f"[通过] rag_search: chunks={rag['chunks']}")


if __name__ == "__main__":
    asyncio.run(main())
