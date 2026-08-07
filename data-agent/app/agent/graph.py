# 负责定义langgraph图

from langgraph.constants import START, END
from langgraph.graph import StateGraph

# 状态、上下文、节点
from app.agent.context import DataAgentContext
from app.agent.state import DataAgentState
from app.agent.nodes.add_extra_context import add_extra_context
from app.agent.nodes.correct_sql import correct_sql
from app.agent.nodes.execute_sql import execute_sql
from app.agent.nodes.extract_keywords import extract_keywords
from app.agent.nodes.filter_metric import filter_metric
from app.agent.nodes.filter_table import filter_table
from app.agent.nodes.generate_sql import generate_sql
from app.agent.nodes.merge_retrieved_info import merge_retrieved_info
from app.agent.nodes.recall_column import recall_column
from app.agent.nodes.recall_metric import recall_metric
from app.agent.nodes.recall_value import recall_value
from app.agent.nodes.validate_sql import validate_sql
from app.core.log import logger
# 客户端管理器
from app.clients.embedding_client_manager import embedding_client_manager
from app.clients.es_client_manager import es_client_manager
from app.clients.mysql_client_manager import meta_mysql_client_manager, dw_mysql_client_manager
from app.clients.qdrant_client_manager import qdrant_client_manager

# 数据仓库
from app.repositories.es.value_es_repository import ValueESRepository
from app.repositories.mysql.dw.dw_mysql_repository import DWMySQLRepository
from app.repositories.mysql.meta.meta_mysql_repository import MetaMySQLRepository
from app.repositories.qdrant.column_qdrant_repository import ColumnQdrantRepository
from app.repositories.qdrant.metric_qdrant_repository import MetricQdrantRepository


def build_agent_graph() -> StateGraph:
    """
    构建数据分析 Agent 流程图
    流程链路：
    1. 提取关键词 → 并行召回字段/取值/指标
    2. 合并召回数据 → 并行过滤表/指标
    3. 补充额外上下文 → 生成SQL → 校验SQL
    4. 校验通过则执行SQL；失败则校正SQL后再执行
    """
    # 初始化图构造器
    graph_builder = StateGraph(
        state_schema=DataAgentState,
        context_schema=DataAgentContext
    )

    # ========== 注册所有节点 ==========
    graph_builder.add_node("extract_keywords", extract_keywords)
    graph_builder.add_node("recall_column", recall_column)
    graph_builder.add_node("recall_value", recall_value)
    graph_builder.add_node("recall_metric", recall_metric)
    graph_builder.add_node("merge_retrieved_info", merge_retrieved_info)
    graph_builder.add_node("filter_table", filter_table)
    graph_builder.add_node("filter_metric", filter_metric)
    graph_builder.add_node("add_extra_context", add_extra_context)
    graph_builder.add_node("generate_sql", generate_sql)
    graph_builder.add_node("validate_sql", validate_sql)
    graph_builder.add_node("correct_sql", correct_sql)
    graph_builder.add_node("execute_sql", execute_sql)

    # ========== 配置固定边 ==========
    # 起始节点：提取关键词，之后并行三个召回节点
    graph_builder.add_edge(START, "extract_keywords")
    graph_builder.add_edge("extract_keywords", "recall_column")
    graph_builder.add_edge("extract_keywords", "recall_value")
    graph_builder.add_edge("extract_keywords", "recall_metric")

    # 三个召回节点全部完成后，进入合并信息节点
    graph_builder.add_edge("recall_column", "merge_retrieved_info")
    graph_builder.add_edge("recall_value", "merge_retrieved_info")
    graph_builder.add_edge("recall_metric", "merge_retrieved_info")

    # 合并完成后，并行执行表过滤、指标过滤
    graph_builder.add_edge("merge_retrieved_info", "filter_table")
    graph_builder.add_edge("merge_retrieved_info", "filter_metric")

    # 两个过滤节点完成后，添加上下文
    graph_builder.add_edge("filter_table", "add_extra_context")
    graph_builder.add_edge("filter_metric", "add_extra_context")

    graph_builder.add_edge("add_extra_context", "generate_sql")
    graph_builder.add_edge("generate_sql", "validate_sql")

    # ========== 条件分支：SQL校验分流 ==========

    MAX_SQL_CORRECT_RETRY = 3 # 防止 更正sql和生成sql 两个节点来回调，限制次数
    def route_after_validate(state: DataAgentState) -> str:
        """SQL校验路由：无错误→执行SQL，有错误→校正SQL"""
        error = state.get("error")
        if error is None: # 不存在错误
            return "execute_sql"

        # 存在错误，判断是否达到重试上限
        retry_cnt = state.get("sql_retry_count", 0)
        if retry_cnt >= MAX_SQL_CORRECT_RETRY:
            logger.warning("次数超过最大次数")
            return "__end__"
        return "correct_sql"

    graph_builder.add_conditional_edges(
        source="validate_sql",
        path=route_after_validate,
        path_map={ # 路由返回值 → 目标节点映射  路由函数返回 "execute_sql" → 流转到 execute_sql 节点
            "execute_sql": "execute_sql",
            "correct_sql": "correct_sql",
            "__end__": "__end__"
        }
    )

    # 校正SQL后统一进入执行节点
    graph_builder.add_edge("correct_sql", "execute_sql")
    # 执行完成结束流程
    graph_builder.add_edge("execute_sql", END)

    return graph_builder.compile()


# 全局单例流程图（项目统一入口）
agent_graph = build_agent_graph()