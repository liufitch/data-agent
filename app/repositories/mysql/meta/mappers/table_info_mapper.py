# table_info orm实体和业务实体的类型转换

from dataclasses import asdict
from typing import Optional

from app.entities.table_info import TableInfo
from app.models.table_info_mysql import TableInfoMySQL


class TableInfoMapper:
    @staticmethod
    def to_entity(model: TableInfoMySQL) -> TableInfo:
        """MySQL 模型 → 业务实体"""
        return TableInfo(
            id=model.id,
            name=model.name,
            role=model.role,
            description=model.description
        )

    @staticmethod
    def to_model(entity: TableInfo) -> TableInfoMySQL:
        """业务实体 → MySQL 模型"""
        return TableInfoMySQL(**asdict(entity))

    @staticmethod
    def to_entity_list(model_list: list[TableInfoMySQL]) -> list[TableInfo]:
        """批量：MySQL 模型列表 → 业务实体列表"""
        return [TableInfoMapper.to_entity(item) for item in model_list]

    @staticmethod
    def to_model_list(entity_list: list[TableInfo]) -> list[TableInfoMySQL]:
        """批量：业务实体列表 → MySQL 模型列表"""
        return [TableInfoMapper.to_model(item) for item in entity_list]