# 负责定义召回指标信息的节点

from typing import Dict, List
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt


async def recall_metric(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List[MetricInfo]]:
    """
    基于关键词+LLM扩写关键词，从向量库召回关联指标
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 召回指标列表
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回指标", "status": "running"})

    # 安全取值，避免键不存在
    query = state.get("query", "").strip()
    keywords = state.get("keywords", [])

    embedding_client = runtime.context["embedding_client"]
    metric_qdrant_repo = runtime.context["metric_qdrant_repository"]

    try:
        # 加载提示词并构建调用链路
        prompt_template = PromptTemplate(
            template=load_prompt("extend_keywords_for_metric_recall"),
            input_variables=["query"]
        )
        json_parser = JsonOutputParser()
        chain = prompt_template | llm | json_parser

        # LLM 扩展关键词
        extend_result = await chain.ainvoke({"query": query})
        # 合并关键词并去重
        all_keywords = list(set(keywords + extend_result))
        logger.info(f"指标召回 - 合并后关键词列表: {all_keywords}")

        # 向量检索 + 字典去重
        retrieved_metrics_map: Dict[str, MetricInfo] = {}
        for keyword in all_keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            embedding = await embedding_client.aembed_query(keyword)
            metric_list = await metric_qdrant_repo.search(embedding)
            for metric in metric_list:
                retrieved_metrics_map.setdefault(metric.id, metric)

        retrieved_metrics = list(retrieved_metrics_map.values())
        writer({"type": "progress", "step": "召回指标", "status": "success"})
        logger.info(f"指标召回完成，命中指标ID列表: {list(retrieved_metrics_map.keys())}")

        return {"retrieved_metrics": retrieved_metrics}

    except Exception:
        writer({"type": "progress", "step": "召回指标", "status": "error"})
        logger.exception("召回指标信息发生异常")
        raise