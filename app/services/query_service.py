# 负责定义查询接口核心业务逻辑

import json
from typing import AsyncGenerator
from langchain_huggingface import HuggingFaceEndpointEmbeddings

from app.agent.context import DataAgentContext
from app.agent.graph import agent_graph
from app.agent.state import DataAgentState
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


class QueryService:
    """数据分析查询服务，封装流程图调用与SSE流式输出"""

    def __init__(
        self,
        embedding_client: HuggingFaceEndpointEmbeddings,
        column_qdrant_repository: ColumnQdrantRepository,
        value_es_repository: ValueESRepository,
        metric_qdrant_repository: MetricQdrantRepository,
        meta_mysql_repository: MetaMySQLRepository,
        dw_mysql_repository: DWMySQLRepository
    ):
        self.embedding_client = embedding_client
        self.column_qdrant_repository = column_qdrant_repository
        self.value_es_repository = value_es_repository
        self.metric_qdrant_repository = metric_qdrant_repository
        self.meta_mysql_repository = meta_mysql_repository
        self.dw_mysql_repository = dw_mysql_repository

    async def query(self, user_query: str) -> AsyncGenerator[str, None]:
        """
        执行查询流程并以SSE格式流式返回结果
        :param user_query: 用户自然语言查询
        :return: SSE标准格式异步数据流
        """
        # 初始化上下文与流程状态
        context = DataAgentContext(
            embedding_client=self.embedding_client,
            column_qdrant_repository=self.column_qdrant_repository,
            value_es_repository=self.value_es_repository,
            metric_qdrant_repository=self.metric_qdrant_repository,
            meta_mysql_repository=self.meta_mysql_repository,
            dw_mysql_repository=self.dw_mysql_repository
        )
        state = DataAgentState(query=user_query)

        try:
            # 执行流程图并流式推送数据
            async for chunk in agent_graph.astream(
                input=state,
                context=context,
                stream_mode="custom"
            ):
                payload = json.dumps(chunk, ensure_ascii=False, default=str)
                # SSE 格式统一由 query_router.sse_event_generator 负责封装。
                yield payload

        except Exception as e:
            # 统一封装异常信息，向前端推送错误流
            error_data = {
                "type": "error",
                "message": f"流程执行异常: {str(e)}"
            }
            payload = json.dumps(error_data, ensure_ascii=False, default=str)
            yield payload
