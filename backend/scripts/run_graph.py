"""CLI 验证脚本，跑通带人工审批的取数，验证中断与恢复。

用法：
  python scripts/run_graph.py "最近三个月各渠道 GMV"                首次，跑到审批中断
  python scripts/run_graph.py --resume <thread_id> --decision approve   恢复到中断点
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.types import Command  # noqa: E402

from app.graph.build import build_graph, close_graph  # noqa: E402


async def run_first(question: str, thread_id: str) -> None:
    graph = await build_graph()
    try:
        config = {"configurable": {"thread_id": thread_id}}
        initial = {"user_goal": question, "session_id": thread_id}

        print(f"thread_id={thread_id}")
        async for chunk in graph.astream(initial, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "sql_generate":
                    print(f"[sql_generate] SQL: {update.get('sql_draft')}")
                    print(f"[sql_generate] 说明: {update.get('sql_explain')}")
                elif node == "readonly_exec":
                    print(f"[readonly_exec] result_ref={update.get('result_ref')}")
                    print(f"[readonly_exec] meta={update.get('result_meta')}")

        snapshot = graph.get_state(config)
        if snapshot.next:
            print("\n图中断，等待审批。恢复命令：")
            print(f"  python scripts/run_graph.py --resume {thread_id} --decision approve")
        else:
            print("\n流程结束")
    finally:
        await close_graph()


async def run_resume(thread_id: str, decision: str, comment: str | None) -> None:
    graph = await build_graph()
    try:
        config = {"configurable": {"thread_id": thread_id}}

        async for chunk in graph.astream(
            Command(resume={"decision": decision, "comment": comment}),
            config,
            stream_mode="updates",
        ):
            for node, update in chunk.items():
                if node == "readonly_exec":
                    print(f"[readonly_exec] result_ref={update.get('result_ref')}")
                    print(f"[readonly_exec] meta={update.get('result_meta')}")
        print("恢复完成")
    finally:
        await close_graph()


def main() -> None:
    parser = argparse.ArgumentParser(description="跑通带审批的取数")
    parser.add_argument("question", nargs="?", help="用户问题")
    parser.add_argument("--resume", help="恢复的 thread_id")
    parser.add_argument("--decision", default="approve", choices=["approve", "edit", "cancel"])
    parser.add_argument("--comment", default=None)
    args = parser.parse_args()

    if args.resume:
        asyncio.run(run_resume(args.resume, args.decision, args.comment))
        return

    question = args.question or "最近三个月各渠道的 GMV 走势"
    thread_id = f"ss_{uuid.uuid4().hex[:8]}"
    asyncio.run(run_first(question, thread_id))


if __name__ == "__main__":
    main()
