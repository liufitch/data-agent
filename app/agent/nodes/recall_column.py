# 负责定义召回字段信息的节点
from typing import Dict, List
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from langgraph.runtime import Runtime

from app.agent.context import DataAgentContext
from app.agent.llm import llm
from app.agent.state import DataAgentState
from app.core.log import logger
from app.entities.column_info import ColumnInfo
from app.prompt.prompt_loader import load_prompt


async def recall_column(
    state: DataAgentState,
    runtime: Runtime[DataAgentContext]
) -> Dict[str, List[ColumnInfo]]:
    """
    基于关键词+LLM扩写关键词，从向量库召回关联字段
    :param state: Agent 流程状态
    :param runtime: 运行时上下文
    :return: 召回字段列表
    """
    writer = runtime.stream_writer
    writer({"type": "progress", "step": "召回字段", "status": "running"})

    # 安全取值，兼容字段缺失场景
    query = state.get("query", "").strip()
    keywords = state.get("keywords", [])

    embedding_client = runtime.context["embedding_client"]
    column_qdrant_repo = runtime.context["column_qdrant_repository"]

    try:
        # 加载提示词并构建链路
        prompt_template = PromptTemplate(
            template=load_prompt("extend_keywords_for_column_recall"),
            input_variables=["query"],
        )
        json_parser = JsonOutputParser()
        chain = prompt_template | llm | json_parser

        # LLM 扩展关键词
        extend_result = await chain.ainvoke({"query": query})
        # 合并关键词并去重
        all_keywords = list(set(keywords + extend_result))
        logger.info(f"字段召回 - 合并后关键词列表: {all_keywords}")

        # 向量召回，字典去重
        retrieved_cols_map: Dict[str, ColumnInfo] = {}
        for keyword in all_keywords:
            if not keyword.strip():
                continue
            # 生成向量并检索
            vec = await embedding_client.aembed_query(keyword)
            col_list = await column_qdrant_repo.search(vec)
            for col in col_list:
                if col.id not in retrieved_cols_map:
                    retrieved_cols_map[col.id] = col

        retrieved_columns = list(retrieved_cols_map.values())
        writer({"type": "progress", "step": "召回字段", "status": "success"})
        logger.info(f"字段召回完成，命中字段ID列表: {list(retrieved_cols_map.keys())}")

        return {"retrieved_columns": retrieved_columns}

    except Exception as exc:
        writer({"type": "progress", "step": "召回字段", "status": "error"})
        logger.exception("召回字段信息发生异常")
        raise