# 负责定义召回指标信息的节点

from typing import Dict, List
import openai
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from app.agent.context import DataAgentContext
from app.agent.llm import get_llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.metric_info import MetricInfo
from app.prompt.prompt_loader import load_prompt

# 定义期望输出结构
class KeywordExpandResp(BaseModel):
    keywords: list[str] = Field(description="扩展后的关键词列表")

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
        #LangChain 中的 Output Parser（输出解析器） 和 Prompt Template（提示模板）
        # 相当于在调用大模型的输入前和输出后添加了两个中间层，它们共同作用，确保大模型的输出符合预定义的格式规范
        # 结构化llm
        structured_llm = get_llm().with_structured_output(KeywordExpandResp)
        # 加载提示词并构建调用链路
        prompt_template = PromptTemplate(
            template=load_prompt("extend_keywords_for_metric_recall"),
            input_variables=["query"]
        )


        try:
            # 格式化完整prompt
            prompt_input = {"query": query}
            full_prompt = prompt_template.format(**prompt_input)
            log_text = f"""
                   ========== LLM 输入Prompt =========={full_prompt}
                   ====================================
                   """
            logger.info(log_text)
            chain = prompt_template | structured_llm
            # 调用
            extend_result = await chain.ainvoke(prompt_input)
            extend_keywords = extend_result.keywords
        except OutputParserException as e:
            logger.warning(f"【关键词扩写失败】模型未返回合法JSON，query={query}, llm输出不符合规范, err={str(e)}")
            # 解析失败 → 扩展关键词置空，继续使用原始keywords
            extend_keywords = []
        except Exception as e:
            logger.exception(f"【关键词扩写调用异常】query={query}, err={str(e)}")
            extend_keywords = []


        # 合并关键词 过滤空字符串、去重
        all_keywords = list(set(keywords + extend_keywords))
        logger.info(f"指标召回 - 合并后关键词列表: {all_keywords}")
        # 向量检索 + 字典去重
        retrieved_metrics_map: Dict[str, MetricInfo] = {}
        for keyword in all_keywords:
            keyword = keyword.strip()
            if not keyword:
                continue

            try:
                #关键词向量化
                embedding = await embedding_client.aembed_query(keyword)
                # qdrant检索逻辑
            except openai.APIError as e:
                logger.warning(f"向量接口异常，跳过关键词:{keyword}, err={str(e)}")
                continue
            except Exception as e:
                logger.error(f"向量化失败 keyword={keyword}")
                continue
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