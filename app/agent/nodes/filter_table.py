# 负责定义过滤表格信息的节点

from typing import Dict, List
import yaml
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import get_llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.prompt.prompt_loader import load_prompt


async def filter_table(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List]:
    """
    基于用户查询 + LLM 过滤无关数据表与字段
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 过滤后的表信息列表
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "过滤表格", "status": "running"})

    # 安全取值，避免 KeyError
    query = state.get("query", "").strip()
    table_infos = state.get("table_infos", [])

    if not table_infos:
        logger.warning("当前无待过滤表信息，直接跳过")
        writer({"type": "progress", "step": "过滤表格", "status": "success"})
        return {"table_infos": table_infos}

    try:
        # 构建调用链路
        prompt_template = PromptTemplate(
            template=load_prompt("filter_table_info"),
            input_variables=["query", "table_infos"]
        )
        json_parser = JsonOutputParser()
        chain = prompt_template | get_llm() | json_parser

        # YAML 序列化表结构，保留中文、原有顺序
        table_yaml = yaml.dump(
            table_infos,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False
        )
        llm_result = await chain.ainvoke({
            "query": query,
            "table_infos": table_yaml
        })

        # 类型兜底，确保为字典
        if not isinstance(llm_result, dict):
            logger.warning("LLM 返回格式异常，保留全部表与字段")
            writer({"type": "progress", "step": "过滤表格", "status": "success"})
            return {"table_infos": table_infos}

        # 筛选表：只保留 LLM 选中的表
        filtered_tables = []
        for table in table_infos:
            table_name = table.get("name", "")
            if table_name not in llm_result:
                continue

            # 筛选当前表下的字段
            keep_col_names = llm_result[table_name]
            if not isinstance(keep_col_names, list):
                keep_col_names = []

            filtered_cols = [
                col for col in table["columns"]
                if col.get("name", "") in keep_col_names
            ]
            table["columns"] = filtered_cols
            filtered_tables.append(table)

        writer({"type": "progress", "step": "过滤表格", "status": "success"})
        logger.info(f"过滤后数据表: {[t['name'] for t in filtered_tables]}")
        return {"table_infos": filtered_tables}

    except Exception:
        writer({"type": "progress", "step": "过滤表格", "status": "error"})
        logger.exception("过滤数据表发生异常")
        raise