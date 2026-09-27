"""成本熔断。token 累计与超预算熔断。"""

from __future__ import annotations

from app.errors import BusinessError


class BudgetExceeded(BusinessError):
    """超预算熔断。"""

    code = "BUSINESS_ERROR"
    http_status = 400
    retryable = False


class Budget:
    """token 预算，累计用量，超限抛熔断。"""

    def __init__(self, max_tokens: int):
        self.max_tokens = max_tokens
        self.used = 0

    def add(self, tokens: int) -> None:
        self.used += tokens
        if self.used > self.max_tokens:
            raise BudgetExceeded(f"token 用量 {self.used} 超过预算 {self.max_tokens}")

    @property
    def remaining(self) -> int:
        return max(0, self.max_tokens - self.used)


def extract_tokens(message) -> int:
    """从模型返回消息里提取 token 用量。"""
    usage = getattr(message, "usage_metadata", None) or {}
    if not isinstance(usage, dict):
        return 0
    total = usage.get("total_tokens")
    if total is not None:
        return int(total)
    input_tokens = usage.get("input_tokens") or usage.get("prompt_tokens") or 0
    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or 0
    return int(input_tokens) + int(output_tokens)
