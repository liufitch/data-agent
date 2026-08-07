# 负责实现meta数据库的读写操作

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from sqlalchemy import text  # 补上此行，解决 text 未引用
from dataclasses import fields
from app.entities.table_info import TableInfo
from app.entities.column_info import ColumnInfo
from app.entities.metric_info import MetricInfo
from app.entities.column_metric import ColumnMetric
from app.models.column_info_mysql import ColumnInfoMySQL
from app.models.table_info_mysql import TableInfoMySQL
from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper
from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
from app.repositories.mysql.meta.mappers.metric_info_mapper import MetricInfoMapper
from app.repositories.mysql.meta.mappers.column_metric_mapper import ColumnMetricMapper
from app.core.log import logger

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

    from typing import List, Optional
    from sqlalchemy import text

    from app.entities.column_info import ColumnInfo
    from app.entities.table_info import TableInfo
    from app.models.column_info_mysql import ColumnInfoMySQL
    from app.models.table_info_mysql import TableInfoMySQL
    from app.repositories.mysql.meta.mappers.column_info_mapper import ColumnInfoMapper
    from app.repositories.mysql.meta.mappers.table_info_mapper import TableInfoMapper
    from app.core.log import logger

    async def get_column_info_by_id(self, column_id: str) -> Optional[ColumnInfo]:
        """
        根据字段ID查询字段详情
        :param column_id: 字段唯一ID
        :return: 字段实体，无数据返回 None
        """
        try:
            db_model: Optional[ColumnInfoMySQL] = await self.session.get(ColumnInfoMySQL, column_id)
            if db_model:
                return ColumnInfoMapper.to_entity(db_model)
            return None
        except Exception:
            logger.exception(f"根据ID查询字段异常，column_id: {column_id}")
            return None

    async def get_table_info_by_id(self, table_id: str) -> Optional[TableInfo]:
        """
        根据表ID查询数据表详情
        :param table_id: 数据表唯一ID
        :return: 表实体，无数据返回 None
        """
        try:
            db_model: Optional[TableInfoMySQL] = await self.session.get(TableInfoMySQL, table_id)
            if db_model:
                return TableInfoMapper.to_entity(db_model)
            return None
        except Exception:
            logger.exception(f"根据ID查询数据表异常，table_id: {table_id}")
            return None

    async def get_key_columns_by_table_id(self, table_id: str) -> List[ColumnInfo]:
        """
        根据表ID查询该表下所有主键、外键字段
        :param table_id: 数据表唯一ID
        :return: 主键/外键字段实体列表
        """
        sql = """
              SELECT *
              FROM column_info
              WHERE table_id = :table_id
                AND role IN ('primary_key', 'foreign_key') \
              """
        try:
            result = await self.session.execute(text(sql), {"table_id": table_id})
            rows = result.mappings().fetchall()
            # 获取ColumnInfo所有合法字段名 --ColumnInfo 没有created_at 字段，sql 查出来了，但是不需要，过滤掉这些字段
            valid_fields = {f.name for f in fields(ColumnInfo)}
            return [ColumnInfo(**{k: v for k, v in row.items() if k in valid_fields}) for row in rows]
        except Exception:
            logger.exception(f"查询表主外键字段异常，table_id: {table_id}")
            return []