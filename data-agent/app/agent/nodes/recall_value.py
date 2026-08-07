# 负责定义召回字段取值的节点

from typing import Dict, List

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime


from app.agent.context import DataAgentContext
from app.agent.llm import get_llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.value_info import ValueInfo
from app.prompt.prompt_loader import load_prompt
from pydantic import BaseModel, Field
# 定义期望输出结构
class KeywordExpandResp(BaseModel):
    keywords: list[str] = Field(description="召回字段后关键词列表")

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



    str_parser = JsonOutputParser()
    try:
        # 结构化llm
        # llm = get_llm().with_structured_output(KeywordExpandResp)
        llm = get_llm()
        # 构建提示词与调用链路
        prompt_template = PromptTemplate(
            template=load_prompt("extend_keywords_for_value_recall"),
            input_variables=["query"]
        )
        prompt_input = {"query": query}
        full_prompt = prompt_template.format(**prompt_input)

        # ==========调试日志：打印输入给模型的完整Prompt==========
        log_text = f"""
========== LLM输入Prompt ==========
{full_prompt}
===================================
        """
        logger.info(log_text)

        # 临时打印模型原始返回（定位模型闲聊问题，确认后可注释）
        # 修改为
        ai_msg = await llm.ainvoke(full_prompt)
        # 这里可以正常取 .content
        logger.info(f"recall_value-LLM原始文本响应：{ai_msg.content}")
        # 再执行解析
        raw_resp = str_parser.parse(ai_msg.content)


        # ✅ 取出关键词数组
        extend_keywords = [*raw_resp]

    except OutputParserException as e:
        logger.warning(f"【字段取值-关键词扩写失败】模型未返回合法JSON，query={query}, err={str(e)}")
        extend_keywords = []
    except Exception as e:
        logger.exception(f"【字段取值-关键词扩写异常】query={query},err={str(e)}")
        extend_keywords = []

    # ✅ 合并关键词 + 清洗 + 去重
    raw_all = keywords + extend_keywords
    # 过滤空字符串，有序去重
    seen = set()
    all_keywords = []
    for word in raw_all:
        w = word.strip()
        if w and w not in seen:
            seen.add(w)
            all_keywords.append(w)
    logger.info(f"字段取值召回 - 合并后关键词列表: {all_keywords}")

    try:
        # ES 检索并根据ID去重
        values_map: Dict[str, ValueInfo] = {}
        for keyword in all_keywords:
            value_list = await value_es_repo.search(keyword)
            for item in value_list:
                values_map.setdefault(item.id, item)

        retrieved_values = list(values_map.values())
        writer({"type": "progress", "step": "召回字段取值", "status": "success"})
        logger.info(f"字段取值召回完成，命中数据ID列表: {list(values_map.keys())}")
        return {"retrieved_values": retrieved_values}

    except Exception:
        writer({"type": "progress", "step": "召回字段取值", "status": "error"})
        logger.exception("ES检索字段取值发生异常")
        raise