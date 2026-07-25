# 负责定义召回字段取值的节点

from typing import Dict, List
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt


async def recall_value(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List[ValueInfo]]:
    """
    基于关键词+LLM扩写关键词，从ES召回字段取值数据
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 召回字段取值列表
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段取值", "status": "running"})

    # 安全读取状态，避免键不存在
    query = state.get("query", "").strip()
    keywords = state.get("keywords", [])

    value_es_repo = runtime.context["value_es_repository"]

    try:
        # 构建提示词与调用链路
        prompt_template = PromptTemplate(
            template=load_prompt("extend_keywords_for_value_recall"),
            input_variables=["query"]
        )
        json_parser = JsonOutputParser()
        chain = prompt_template | llm | json_parser

        # LLM 扩展关键词
        extend_result = await chain.ainvoke({"query": query})
        all_keywords = list(set(keywords + extend_result))
        logger.info(f"字段取值召回 - 合并后关键词列表: {all_keywords}")

        # ES 检索并根据ID去重
        values_map: Dict[str, ValueInfo] = {}
        for keyword in all_keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            value_list = await value_es_repo.search(keyword)
            for item in value_list:
                values_map.setdefault(item.id, item)

        retrieved_values = list(values_map.values())
        writer({"type": "progress", "step": "召回字段取值", "status": "success"})
        logger.info(f"字段取值召回完成，命中数据ID列表: {list(values_map.keys())}")

        return {"retrieved_values": retrieved_values}

    except Exception:
        writer({"type": "progress", "step": "召回字段取值", "status": "error"})
        logger.exception("召回字段取值发生异常")
        raise