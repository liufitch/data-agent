# 用于定义字段信息的业务实体类

from dataclasses import dataclass, field
from typing import Any, List, Optional

@dataclass
class ColumnInfo:
    # 全局唯一ID（UUID）
    id: str
    # 数据库字段名
    name: str
    # 字段数据类型
    type: str
    # 字段角色：primary_key / foreign_key / dimension / measure
    role: str
    # 所属表ID，关联 TableInfo.id
    table_id: str
    # 运行时临时标记：是否同步字段值到ES（不落地数据库）
    sync: bool = field(default=False)
    # 字段示例数据
    examples: List[Any] = field(default_factory=list)
    # 字段业务描述
    description: Optional[str] = field(default="")
    # 字段别名/同义词
    alias: List[str] = field(default_factory=list)