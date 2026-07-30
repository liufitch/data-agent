# 负责定义过滤指标信息的节点

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


async def filter_metric(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List]:
    """
    基于用户查询 + LLM 过滤无关指标
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 过滤后的指标列表
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "过滤指标", "status": "running"})

    # 安全取值，避免键不存在
    query = state.get("query", "").strip()
    metric_infos = state.get("metric_infos", [])

    # 无指标直接跳过
    if not metric_infos:
        logger.warning("当前无待过滤指标，直接跳过")
        writer({"type": "progress", "step": "过滤指标", "status": "success"})
        return {"metric_infos": metric_infos}

    try:
        prompt_template = PromptTemplate(
            template=load_prompt("filter_metric_info"),
            input_variables=["query", "metric_infos"]
        )
        json_parser = JsonOutputParser()
        chain = prompt_template | get_llm() | json_parser

        # YAML 序列化，保留中文与原有顺序
        metric_yaml = yaml.dump(
            metric_infos,
            allow_unicode=True,
            sort_keys=False,
            default_flow_style=False
        )
        llm_result = await chain.ainvoke({
            "query": query,
            "metric_infos": metric_yaml
        })

        # 结果类型兜底
        if not isinstance(llm_result, dict):
            logger.warning("LLM 返回格式异常，保留全部指标")
            writer({"type": "progress", "step": "过滤指标", "status": "success"})
            return {"metric_infos": metric_infos}

        # 新建列表收集结果，避免遍历过程中删除元素
        filtered_metrics = []
        keep_names = set(llm_result.keys())
        for metric in metric_infos:
            metric_name = metric.get("name", "")
            if metric_name in keep_names:
                filtered_metrics.append(metric)

        writer({"type": "progress", "step": "过滤指标", "status": "success"})
        logger.info(f"过滤后指标: {[m['name'] for m in filtered_metrics]}")
        return {"metric_infos": filtered_metrics}

    except Exception:
        writer({"type": "progress", "step": "过滤指标", "status": "error"})
        logger.exception("过滤指标发生异常")
        raise