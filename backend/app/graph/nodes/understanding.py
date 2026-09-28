"""理解节点。intent_router 判定意图与信息充分度，clarify 澄清反问。

clarify 是中断节点，interrupt 在第一行，只问一次。
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.types import interrupt
from pydantic import BaseModel

from app.graph.state import AnalysisState
from app.llm import get_structured_llm
from app.middleware.node_wrapper import node
from app.prompts.intent import INTENT_SYSTEM_PROMPT


class IntentOutput(BaseModel):
    """意图识别的结构化输出。"""

    intent: Literal["chat", "simple_query", "deep_analysis"]
    info_sufficient: bool
    clarify_questions: list[str] = []
    route_reason: str = ""


class ClarifyAnswer(BaseModel):
    """澄清回答。"""

    answer: str


@node("intent_router")
async def intent_router(state: AnalysisState) -> dict:
    """判定意图三类并评估信息充分度。"""
    structured = get_structured_llm(IntentOutput)
    messages = [
        SystemMessage(content=INTENT_SYSTEM_PROMPT),
        HumanMessage(content=state["user_goal"]),
    ]
    result: IntentOutput = await structured.ainvoke(messages)
    return {
        "intent": result.intent,
        "route_reason": result.route_reason,
        "info_sufficient": result.info_sufficient,
        "clarify_questions": result.clarify_questions,
    }


async def clarify(state: AnalysisState) -> dict:
    """信息不足时反问一次，interrupt 在第一行。"""
    questions = state.get("clarify_questions", [])
    answer: ClarifyAnswer = interrupt({"questions": questions}, response_schema=ClarifyAnswer)
    return {"clarify_answer": answer.answer}
