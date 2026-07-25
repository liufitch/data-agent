# 负责定义执行SQL的节点

from typing import Dict, Any
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.core.log import logger


async def execute_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, Any]:
    """
    执行最终SQL并返回查询结果
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: SQL执行结果
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "执行SQL", "status": "running"})

    dw_mysql_repo = runtime.context["dw_mysql_repository"]
    sql = state.get("sql", "").strip()

    # 前置校验空SQL
    if not sql:
        logger.warning("待执行 SQL 为空")
        writer({"type": "progress", "step": "执行SQL", "status": "error"})
        raise ValueError("SQL 内容不能为空")

    try:
        exec_result = await dw_mysql_repo.execute_sql(sql)

        writer({"type": "progress", "step": "执行SQL", "status": "success"})
        writer({"type": "result", "data": exec_result})
        logger.info(f"SQL执行结果: {exec_result}")

        return {"result": exec_result}

    except Exception:
        writer({"type": "progress", "step": "执行SQL", "status": "error"})
        logger.exception("SQL执行异常")
        raise