#用于定义meta_config.yaml的参数结构
from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class ColumnConfig:
    name: str
    role: str
    description: str
    alias: List[str]
    sync: bool


@dataclass
class TableConfig:
    name: str
    role: str
    description: str
    columns: List[ColumnConfig]


@dataclass
class MetricConfig:
    name: str
    description: str
    relevant_columns: List[str]
    alias: List[str]


@dataclass
class MetaConfig:
    # 给列表设置空列表默认值，避免 Optional + 列表混用的坑
    tables: Optional[List[TableConfig]] = field(default_factory=list)
    metrics: Optional[List[MetricConfig]] = field(default_factory=list)