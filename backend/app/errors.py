"""统一异常类型与错误码。

错误分三类，参数错误、业务错误、系统错误。业务错误里再区分可重试与不可重试，
前端据此决定提示重试还是直接报错。对应 api-contract.md 第 1.1 节。
"""

from __future__ import annotations


class AppError(Exception):
    """应用错误基类。"""

    code: str = "SYSTEM_ERROR"
    http_status: int = 500
    retryable: bool = False

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ParamError(AppError):
    """参数错误，请求体缺字段或类型不符。"""

    code = "PARAM_ERROR"
    http_status = 400
    retryable = False


class BusinessError(AppError):
    """业务错误，业务规则不满足。"""

    code = "BUSINESS_ERROR"
    http_status = 400
    retryable = False


class RetryableBusinessError(BusinessError):
    """可重试的业务错误。"""

    retryable = True


class ConfigError(AppError):
    """配置错误，启动时必填项缺失或格式错误。"""

    code = "SYSTEM_ERROR"
    http_status = 500
    retryable = False
