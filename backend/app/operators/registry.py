"""算子注册表。算子名到实现与参数 schema 的映射。"""

from __future__ import annotations

from app.operators.impl.attribution import op_attribution
from app.operators.impl.correlation import op_correlation
from app.operators.impl.distribution import op_distribution
from app.operators.impl.enumerate import op_enumerate
from app.operators.impl.period_compare import op_period_compare
from app.operators.impl.top_n import op_top_n
from app.operators.schema import (
    AttributionParams,
    CorrelationParams,
    DistributionParams,
    EnumerateParams,
    PeriodCompareParams,
    TopNParams,
)

OPERATORS = {
    "period_compare": op_period_compare,
    "top_n": op_top_n,
    "attribution": op_attribution,
    "distribution": op_distribution,
    "correlation": op_correlation,
    "enumerate": op_enumerate,
}

# 算子名到参数 schema 的映射，模型输出据此校验
PARAM_SCHEMAS = {
    "period_compare": PeriodCompareParams,
    "top_n": TopNParams,
    "attribution": AttributionParams,
    "distribution": DistributionParams,
    "correlation": CorrelationParams,
    "enumerate": EnumerateParams,
}
