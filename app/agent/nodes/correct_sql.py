# 负责定义校正SQL的节点
from typing import Dict
import yaml
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def correct_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, str]:
    """
    根据报错信息与上下文，校正出错的 SQL 语句
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 校正后的 SQL
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "校正SQL", "status": "running"})

    # 安全读取状态字段
    sql = state.get("sql", "").strip()
    error = state.get("error", "")
    query = state.get("query", "").strip()
    table_infos = state.get("table_infos", [])
    metric_infos = state.get("metric_infos", [])
    date_info = state.get("date_info", {})
    db_info = state.get("db_info", {})

    # 前置校验：无原始SQL或无错误信息则直接终止
    if not sql:
        logger.warning("待校正 SQL 为空，跳过校正流程")
        writer({"type": "progress", "step": "校正SQL", "status": "error"})
        return {"sql": sql}
    if not error:
        logger.warning("未获取到 SQL 错误信息，跳过校正流程")
        writer({"type": "progress", "step": "校正SQL", "status": "success"})
        return {"sql": sql}

    try:
        # 统一 YAML 序列化配置
        yaml_config = {"allow_unicode": True, "sort_keys": False, "default_flow_style": False}
        prompt_template = PromptTemplate(
            template=load_prompt("correct_sql"),
            input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info", "sql", "error"]
        )
        str_parser = StrOutputParser()
        chain = prompt_template | llm | str_parser

        invoke_params = {
            "query": query,
            "table_infos": yaml.dump(table_infos, **yaml_config),
            "metric_infos": yaml.dump(metric_infos, **yaml_config),
            "date_info": yaml.dump(date_info, **yaml_config),
            "db_info": yaml.dump(db_info, **yaml_config),
            "sql": sql,
            "error": error
        }

        corrected_sql = await chain.ainvoke(invoke_params)
        corrected_sql = corrected_sql.strip()

        writer({"type": "progress", "step": "校正SQL", "status": "success"})
        logger.info(f"校正后 SQL: {corrected_sql}")
        return {"sql": corrected_sql}

    except Exception:
        writer({"type": "progress", "step": "校正SQL", "status": "error"})
        logger.exception("SQL 校正流程异常")
        raise