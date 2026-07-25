# 负责定义生成SQL的节点
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


async def generate_sql(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, str]:
    """
    结合上下文信息，调用 LLM 生成业务 SQL
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 生成的 SQL 语句
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "生成SQL", "status": "running"})

    # 安全读取状态数据
    query = state.get("query", "").strip()
    table_infos = state.get("table_infos", [])
    metric_infos = state.get("metric_infos", [])
    date_info = state.get("date_info", {})
    db_info = state.get("db_info", {})

    try:
        prompt_template = PromptTemplate(
            template=load_prompt("generate_sql"),
            input_variables=["query", "table_infos", "metric_infos", "date_info", "db_info"]
        )
        str_parser = StrOutputParser()
        chain = prompt_template | llm | str_parser

        # 统一 YAML 序列化配置，保证格式一致
        yaml_opts = {"allow_unicode": True, "sort_keys": False, "default_flow_style": False}
        invoke_params = {
            "query": query,
            "table_infos": yaml.dump(table_infos, **yaml_opts),
            "metric_infos": yaml.dump(metric_infos, **yaml_opts),
            "date_info": yaml.dump(date_info, **yaml_opts),
            "db_info": yaml.dump(db_info, **yaml_opts)
        }

        sql_result = await chain.ainvoke(invoke_params)
        # 简单清洗首尾空白字符
        sql_result = sql_result.strip()

        writer({"type": "progress", "step": "生成SQL", "status": "success"})
        logger.info(f"生成SQL语句: {sql_result}")

        return {"sql": sql_result}

    except Exception:
        writer({"type": "progress", "step": "生成SQL", "status": "error"})
        logger.exception("生成SQL发生异常")
        raise