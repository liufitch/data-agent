# 负责定义校验SQL的节点

from typing import Dict, Optional
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def validate_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, Optional[str]]:
    """
    执行 SQL 语法与执行计划校验
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 错误信息，校验通过则为 None
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "验证SQL", "status": "running"})

    dw_mysql_repo = runtime.context["dw_mysql_repository"]
    sql = state.get("sql", "").strip()

    # 前置拦截空 SQL
    if not sql:
        logger.warning("待验证 SQL 为空")
        writer({"type": "progress", "step": "验证SQL", "status": "error"})
        return {"error": "待验证 SQL 内容为空"}

    try:
        await dw_mysql_repo.validate_sql(sql)
        writer({"type": "progress", "step": "验证SQL", "status": "success"})
        logger.info(f"SQL 验证通过: {sql}")
        return {"error": None}

    except Exception:
        writer({"type": "progress", "step": "验证SQL", "status": "error"})
        logger.exception(f"SQL 验证失败，SQL: {sql}")
        return {"error": "SQL 语法或执行计划校验不通过"}