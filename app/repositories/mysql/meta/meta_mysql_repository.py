# 负责实现meta数据库的读写操作

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from app.entities.table_info import TableInfo
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.column_metric import ColumnMetric
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper


class MetaMySQLRepository:
    def __init__(self, session: AsyncSession):
        self.session: AsyncSession = session

    async def save_table_infos(self, table_infos: List[TableInfo]) -> None:
        """批量保存数据表元信息"""
        models = TableInfoMapper.to_model_list(table_infos)
        self.session.add_all(models)

    async def save_column_infos(self, column_infos: List[ColumnInfo]) -> None:
        """批量保存字段元信息"""
        models = ColumnInfoMapper.to_model_list(column_infos)
        self.session.add_all(models)

    async def save_metric_infos(self, metric_infos: List[MetricInfo]) -> None:
        """批量保存指标元信息"""
        models = MetricInfoMapper.to_model_list(metric_infos)
        self.session.add_all(models)

    async def save_column_metrics(self, column_metrics: List[ColumnMetric]) -> None:
        """批量保存字段-指标关联关系"""
        models = ColumnMetricMapper.to_model_list(column_metrics)
        self.session.add_all(models)