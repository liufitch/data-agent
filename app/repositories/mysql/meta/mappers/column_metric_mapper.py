# column_metric orm实体和业务实体的类型转换

from dataclasses import asdict
from typing import List

from app.entities.column_metric import ColumnMetric
from app.models.column_metric_mysql import ColumnMetricMySQL


class ColumnMetricMapper:
    @staticmethod
    def to_entity(model: ColumnMetricMySQL) -> ColumnMetric:
        """MySQL 数据库模型 → 业务实体"""
        return ColumnMetric(
            column_id=model.column_id,
            metric_id=model.metric_id
        )

    @staticmethod
    def to_model(entity: ColumnMetric) -> ColumnMetricMySQL:
        """业务实体 → MySQL 数据库模型"""
        return ColumnMetricMySQL(**asdict(entity))

    @staticmethod
    def to_entity_list(model_list: List[ColumnMetricMySQL]) -> List[ColumnMetric]:
        """批量转换：模型列表 → 实体列表"""
        return [ColumnMetricMapper.to_entity(item) for item in model_list]

    @staticmethod
    def to_model_list(entity_list: List[ColumnMetric]) -> List[ColumnMetricMySQL]:
        """批量转换：实体列表 → 模型列表"""
        return [ColumnMetricMapper.to_model(item) for item in entity_list]