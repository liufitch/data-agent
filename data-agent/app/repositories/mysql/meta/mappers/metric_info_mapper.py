# metric_info orm实体和业务实体的类型转换
from dataclasses import asdict
from typing import List

from app.entities.metric_info import MetricInfo
from app.models.metric_info_mysql import MetricInfoMySQL


class MetricInfoMapper:
    @staticmethod
    def to_entity(model: MetricInfoMySQL) -> MetricInfo:
        """MySQL 数据库模型 → 业务实体"""
        return MetricInfo(
            id=model.id,
            name=model.name,
            description=model.description,
            relevant_columns=model.relevant_columns,
            alias=model.alias
        )

    @staticmethod
    def to_model(entity: MetricInfo) -> MetricInfoMySQL:
        """业务实体 → MySQL 数据库模型"""
        return MetricInfoMySQL(**asdict(entity))

    @staticmethod
    def to_entity_list(model_list: List[MetricInfoMySQL]) -> List[MetricInfo]:
        """批量转换：模型列表 → 实体列表"""
        return [MetricInfoMapper.to_entity(item) for item in model_list]

    @staticmethod
    def to_model_list(entity_list: List[MetricInfo]) -> List[MetricInfoMySQL]:
        """批量转换：实体列表 → 模型列表"""
        return [MetricInfoMapper.to_model(item) for item in entity_list]