# column_info orm实体和业务实体的类型转换

from dataclasses import asdict
from typing import List

from app.entities.column_info import ColumnInfo
from app.models.column_info_mysql import ColumnInfoMySQL


class ColumnInfoMapper:
    @staticmethod
    def to_entity(model: ColumnInfoMySQL) -> ColumnInfo:
        """MySQL 数据库模型 → 业务实体"""
        return ColumnInfo(
            id=model.id,
            name=model.name,
            type=model.type,
            role=model.role,
            examples=model.examples,
            description=model.description,
            alias=model.alias,
            table_id=model.table_id
        )

    @staticmethod
    def to_model(entity: ColumnInfo) -> ColumnInfoMySQL:
        """业务实体 → MySQL 数据库模型
        注：entity.sync 为运行时临时字段，asdict 会自动携带，MySQL 模型忽略即可
        """
        return ColumnInfoMySQL(**asdict(entity))

    @staticmethod
    def to_entity_list(model_list: List[ColumnInfoMySQL]) -> List[ColumnInfo]:
        """批量转换：模型列表 → 实体列表"""
        return [ColumnInfoMapper.to_entity(item) for item in model_list]

    @staticmethod
    def to_model_list(entity_list: List[ColumnInfo]) -> List[ColumnInfoMySQL]:
        """批量转换：实体列表 → 模型列表"""
        return [ColumnInfoMapper.to_model(item) for item in entity_list]