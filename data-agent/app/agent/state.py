# 负责定义langgraph状态
from typing import TypedDict, List

from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.value_info import ValueInfo


class ColumnInfoState(TypedDict):
    """字段中间状态"""
    name: str
    type: str
    role: str
    examples: List[str]
    description: str
    alias: List[str]


class TableInfoState(TypedDict):
    """数据表中间状态"""
    name: str
    role: str
    description: str
    columns: List[ColumnInfoState]


class MetricInfoState(TypedDict):
    """指标中间状态"""
    name: str
    description: str
    relevant_columns: List[str]
    alias: List[str]


class DateInfoState(TypedDict):
    """日期解析状态"""
    date: str
    weekday: str
    quarter: str


class DBInfoState(TypedDict):
    """数据库信息状态"""
    dialect: str
    version: str


class DataAgentState(TypedDict):
    """DataAgent 全流程上下文状态"""
    # 用户输入与解析
    query: str
    keywords: List[str]

    # 向量/检索召回结果（原始实体）
    retrieved_columns: List[ColumnInfo]
    retrieved_values: List[ValueInfo]
    retrieved_metrics: List[MetricInfo]

    # 结构化元数据状态
    table_infos: List[TableInfoState]
    metric_infos: List[MetricInfoState]

    # 环境信息
    date_info: DateInfoState
    db_info: DBInfoState

    # 输出结果
    sql: str
    error: str

    sql_retry_count: int  # 新增：SQL校正重试次数