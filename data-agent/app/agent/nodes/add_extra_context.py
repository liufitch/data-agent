# 负责定义添加额外上下文信息的节点

from typing import Dict
from datetime import datetime
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState, DateInfoState
from app.core.log import logger


async def add_extra_context(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, object]:
    """
    补充流程额外上下文：日期信息、数据仓库环境信息
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 日期信息、数据库信息
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "添加额外上下文信息", "status": "running"})

    dw_mysql_repo = runtime.context["dw_mysql_repository"]

    try:
        # 解析当前日期、星期、季度
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        weekday_str = now.strftime("%A")
        quarter_str = f"Q{(now.month - 1) // 3 + 1}"

        date_info = DateInfoState(
            date=date_str,
            weekday=weekday_str,
            quarter=quarter_str
        )

        # 获取数据库环境信息
        db_info = await dw_mysql_repo.get_db_info()

        writer({"type": "progress", "step": "添加额外上下文信息", "status": "success"})
        logger.info(f"额外上下文 | 日期信息: {date_info} | 数据库信息: {db_info}")

        return {
            "date_info": date_info,
            "db_info": db_info
        }

    except Exception:
        writer({"type": "progress", "step": "添加额外上下文信息", "status": "error"})
        logger.exception("添加上下文信息异常")
        raise